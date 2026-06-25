import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.rag.registry import RAG_RULE_REGISTRY, resolve_category


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
SCORING_CONFIG_FILE = CONFIG_DIR / "scoring_config.json"


def _load_scoring_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or SCORING_CONFIG_FILE
    if config_path.is_file():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


_SCORING_CONFIG_DATA = _load_scoring_config()


def get_scoring_config_data() -> dict[str, Any]:
    return _SCORING_CONFIG_DATA


def reload_scoring_config(path: Path | None = None) -> dict[str, Any]:
    global _SCORING_CONFIG_DATA
    _SCORING_CONFIG_DATA = _load_scoring_config(path)
    return _SCORING_CONFIG_DATA


def _resolve_client_maturity(
    config: dict[str, Any],
    client_id: str | None,
) -> str:
    overrides = config.get("client_overrides", {})
    if client_id and client_id in overrides:
        return overrides[client_id].get("maturity_level", "standard")
    return "standard"


def _resolve_deductions(
    config: dict[str, Any],
    category_key: str,
    maturity: str,
    client_id: str | None,
) -> dict[str, int]:
    defaults = config.get("defaults", {})
    base = defaults.get("severity_deductions", {})

    overrides = config.get("client_overrides", {})
    client_cfg = overrides.get(client_id, {}) if client_id else {}

    if client_cfg.get("category_weights") and category_key in client_cfg["category_weights"]:
        merged = dict(base)
        merged.update(client_cfg["category_weights"][category_key])
        return merged

    if client_cfg.get("severity_deductions"):
        merged = dict(base)
        merged.update(client_cfg["severity_deductions"])
        base = merged

    category_weights = config.get("category_weights", {})
    if category_key in category_weights:
        merged = dict(base)
        merged.update(category_weights[category_key])
        base = merged

    for level in config.get("maturity_levels", []):
        if level["name"] == maturity:
            if level.get("category_weights") and category_key in level["category_weights"]:
                merged = dict(base)
                merged.update(level["category_weights"][category_key])
                return merged
            if level.get("severity_deductions"):
                merged = dict(base)
                merged.update(level["severity_deductions"])
                base = merged
            break

    return base


def _resolve_grade_thresholds(
    config: dict[str, Any],
    maturity: str,
    client_id: str | None,
) -> list[tuple[int, str]]:
    defaults = config.get("defaults", {})
    raw = defaults.get("grade_thresholds", [])

    overrides = config.get("client_overrides", {})
    client_cfg = overrides.get(client_id, {}) if client_id else {}

    if client_cfg.get("grade_thresholds"):
        raw = client_cfg["grade_thresholds"]

    for level in config.get("maturity_levels", []):
        if level["name"] == maturity:
            if level.get("grade_thresholds"):
                raw = level["grade_thresholds"]
            break

    return [(t["min_score"], t["grade"]) for t in raw]


def _resolve_starting_score(
    config: dict[str, Any],
    client_id: str | None,
) -> int:
    defaults = config.get("defaults", {})
    base = defaults.get("starting_score", 100)
    overrides = config.get("client_overrides", {})
    client_cfg = overrides.get(client_id, {}) if client_id else {}
    return client_cfg.get("starting_score", base)


def _resolve_minimum_score(
    config: dict[str, Any],
    client_id: str | None,
) -> int:
    defaults = config.get("defaults", {})
    base = defaults.get("minimum_score", 0)
    overrides = config.get("client_overrides", {})
    client_cfg = overrides.get(client_id, {}) if client_id else {}
    return client_cfg.get("minimum_score", base)


def _resolve_maximum_score(
    config: dict[str, Any],
    client_id: str | None,
) -> int:
    defaults = config.get("defaults", {})
    base = defaults.get("maximum_score", 100)
    overrides = config.get("client_overrides", {})
    client_cfg = overrides.get(client_id, {}) if client_id else {}
    return client_cfg.get("maximum_score", base)


@dataclass(frozen=True)
class ScoringCategory:
    key: str
    label: str
    domain_aliases: tuple[str, ...] = field(default_factory=tuple)
    category_aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ScoringConfig:
    starting_score: int
    minimum_score: int
    maximum_score: int
    severity_deductions: dict[str, int]
    categories: tuple[ScoringCategory, ...]
    grade_thresholds: tuple[tuple[int, str], ...]
    maturity: str = "standard"
    client_id: str | None = None


def build_scoring_config(
    client_id: str | None = None,
    maturity: str | None = None,
    scoring_data: dict[str, Any] | None = None,
) -> ScoringConfig:
    data = scoring_data if scoring_data is not None else _SCORING_CONFIG_DATA
    resolved_maturity = maturity or _resolve_client_maturity(data, client_id)
    raw_categories = data.get("defaults", {}).get("categories", [])

    return ScoringConfig(
        starting_score=_resolve_starting_score(data, client_id),
        minimum_score=_resolve_minimum_score(data, client_id),
        maximum_score=_resolve_maximum_score(data, client_id),
        severity_deductions=_resolve_deductions(data, "__all__", resolved_maturity, client_id),
        grade_thresholds=_resolve_grade_thresholds(data, resolved_maturity, client_id),
        categories=tuple(
            ScoringCategory(
                key=cat["key"],
                label=cat["label"],
                domain_aliases=tuple(cat.get("domain_aliases", [])),
                category_aliases=tuple(cat.get("category_aliases", [])),
            )
            for cat in raw_categories
        ),
        maturity=resolved_maturity,
        client_id=client_id,
    )


DEFAULT_SCORING_CONFIG = build_scoring_config()


class HealthScoringEngine:
    def __init__(
        self,
        config: ScoringConfig | None = None,
        client_id: str | None = None,
        maturity: str | None = None,
    ) -> None:
        if config is not None:
            self.config = config
        else:
            self.config = build_scoring_config(client_id=client_id, maturity=maturity)

    def calculate(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        category_scores = [
            self._category_score(category, findings)
            for category in self.config.categories
        ]
        overall_score = round(
            sum(category["score"] for category in category_scores)
            / max(1, len(category_scores))
        )
        return {
            "overall_score": overall_score,
            "grade": self.grade_for_score(overall_score),
            "category_scores": category_scores,
            "scoring_policy": {
                "starting_score": self.config.starting_score,
                "minimum_score": self.config.minimum_score,
                "maximum_score": self.config.maximum_score,
                "severity_deductions": self.config.severity_deductions,
                "maturity": self.config.maturity,
                "client_id": self.config.client_id,
            },
        }

    def grade_for_score(self, score: int) -> str:
        for threshold, grade in self.config.grade_thresholds:
            if score >= threshold:
                return grade
        return self.config.grade_thresholds[-1][1]

    def _category_score(
        self,
        category: ScoringCategory,
        findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        matched_findings = [
            finding
            for finding in findings
            if self._matches_category(finding, category)
        ]
        deductions = [
            self._deduction_for_finding(finding, category.key)
            for finding in matched_findings
        ]
        total_deduction = sum(deduction["points"] for deduction in deductions)
        score = max(
            self.config.minimum_score,
            min(self.config.maximum_score, self.config.starting_score - total_deduction),
        )
        return {
            "key": category.key,
            "label": category.label,
            "score": score,
            "grade": self.grade_for_score(score),
            "deduction_total": total_deduction,
            "deductions": deductions,
        }

    def _resolve_category_deductions(self, category_key: str) -> dict[str, int]:
        data = _SCORING_CONFIG_DATA
        maturity = self.config.maturity
        client_id = self.config.client_id
        return _resolve_deductions(data, category_key, maturity, client_id)

    def _deduction_for_finding(
        self,
        finding: dict[str, Any],
        category_key: str | None = None,
    ) -> dict[str, Any]:
        evidence = finding.get("evidence") if isinstance(finding.get("evidence"), dict) else {}
        severity = str(finding.get("severity") or evidence.get("severity") or "informational").lower()
        deductions_map = self._resolve_category_deductions(category_key or "__all__")
        points = deductions_map.get(severity, 0)
        return {
            "finding_id": str(finding.get("id") or evidence.get("rule_id") or "finding"),
            "finding_name": str(finding.get("title") or finding.get("name") or "Finding"),
            "severity": severity,
            "points": points,
            "rule_triggered": str(
                finding.get("rule_triggered")
                or evidence.get("rule_triggered")
                or evidence.get("rule_id")
                or "unknown"
            ),
            "job_name": str(finding.get("job_name") or evidence.get("job_name") or evidence.get("job") or "unknown"),
            "component_name": str(
                finding.get("component_name")
                or evidence.get("component")
                or evidence.get("component_name")
                or evidence.get("target")
                or "unknown"
            ),
            "component_type": str(
                finding.get("component_type")
                or evidence.get("component_type")
                or evidence.get("component_name")
                or "unknown"
            ),
        }

    def _matches_category(
        self,
        finding: dict[str, Any],
        category: ScoringCategory,
    ) -> bool:
        evidence = finding.get("evidence") if isinstance(finding.get("evidence"), dict) else {}
        domain = str(evidence.get("domain") or "").lower()
        finding_category = str(finding.get("category") or "").lower()
        source_agent = str(evidence.get("source_agent") or "").lower()
        values = {domain, finding_category, source_agent}

        if any(alias in values for alias in category.domain_aliases):
            return True
        return any(alias in finding_category for alias in category.category_aliases)


def _resolve_compliance_rule_prefixes(
    config: dict[str, Any],
    client_id: str | None,
) -> dict[str, list[str]]:
    compliance = config.get("compliance", {})
    base = dict(compliance.get("rule_prefixes", {}))
    overrides = compliance.get("client_overrides", {})
    client_cfg = overrides.get(client_id, {}) if client_id else {}
    client_cats = client_cfg.get("category_rules", {})
    for cat, rules in client_cats.items():
        if cat in base:
            base[cat] = list(set(base[cat] + rules))
    return base


def _resolve_compliance_maturity(
    config: dict[str, Any],
    client_id: str | None,
) -> str:
    compliance = config.get("compliance", {})
    base = compliance.get("default_maturity", "standard")
    overrides = compliance.get("client_overrides", {})
    client_cfg = overrides.get(client_id, {}) if client_id else {}
    return client_cfg.get("maturity", base)


def _resolve_compliance_grade_thresholds(
    config: dict[str, Any],
    client_id: str | None,
) -> list[tuple[int, str]]:
    compliance = config.get("compliance", {})
    maturity = _resolve_compliance_maturity(config, client_id)
    levels = compliance.get("maturity_levels", {})
    level = levels.get(maturity, levels.get("standard", {}))
    thresholds = level.get("grade_thresholds", [])

    overrides = compliance.get("client_overrides", {})
    client_cfg = overrides.get(client_id, {}) if client_id else {}
    if client_cfg.get("grade_thresholds"):
        thresholds = client_cfg["grade_thresholds"]

    return [(t["min_score"], t["grade"]) for t in thresholds]


class ComplianceScoringEngine:
    """Computes compliance score based on (Passed Objective Rules / Total Objective Applicable Rules) * 100 per category.
    Advisory rules are excluded from scoring and reported separately."""

    def __init__(self, client_id: str | None = None) -> None:
        self.client_id = client_id
        config = _SCORING_CONFIG_DATA
        self.rule_prefixes = _resolve_compliance_rule_prefixes(config, client_id)
        self.grade_thresholds = _resolve_compliance_grade_thresholds(config, client_id)
        self.advisory_rule_ids: set[str] = set(
            config.get("compliance", {}).get("advisory_rule_ids", [])
        )

    def grade_for_score(self, score: int) -> str:
        for threshold, grade in self.grade_thresholds:
            if score >= threshold:
                return grade
        return self.grade_thresholds[-1][1]

    def _rules_for_category(self, category_key: str) -> list[str]:
        prefixes = self.rule_prefixes.get(category_key, [])
        matched: list[str] = []
        for rule_id in RAG_RULE_REGISTRY:
            for prefix in prefixes:
                if rule_id.startswith(prefix):
                    matched.append(rule_id)
                    break
        return sorted(matched)

    def calculate(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        config = _SCORING_CONFIG_DATA
        raw_categories = config.get("defaults", {}).get("categories", [])

        failed_rule_ids: set[str] = set()
        for finding in findings:
            rid = str(finding.get("rule_triggered") or "")
            if rid:
                failed_rule_ids.add(rid)

        category_scores: list[dict[str, Any]] = []
        total_passed = 0
        total_applicable = 0
        all_advisory_failed: list[str] = []

        for raw_cat in raw_categories:
            key = raw_cat["key"]
            label = raw_cat["label"]
            all_rules = self._rules_for_category(key)

            objective_rules = [
                rid for rid in all_rules if rid not in self.advisory_rule_ids
            ]
            advisory_rules_in_cat = [
                rid for rid in all_rules if rid in self.advisory_rule_ids
            ]

            total_objective = len(objective_rules)

            failed_objective = [
                rid for rid in objective_rules if rid in failed_rule_ids
            ]
            failed_advisory = [
                rid for rid in advisory_rules_in_cat if rid in failed_rule_ids
            ]
            failed_count = len(failed_objective)
            passed_count = total_objective - failed_count

            if total_objective > 0:
                score = round((passed_count / total_objective) * 100)
            else:
                score = 100

            total_passed += passed_count
            total_applicable += total_objective
            all_advisory_failed.extend(failed_advisory)

            category_scores.append({
                "key": key,
                "label": label,
                "score": score,
                "grade": self.grade_for_score(score),
                "total_rules": total_objective,
                "passed_rules": passed_count,
                "failed_rules": failed_count,
                "failed_rule_ids": sorted(failed_objective),
                "advisory_failed_rule_ids": sorted(failed_advisory),
                "advisory_total": len(advisory_rules_in_cat),
            })

        overall = round(
            sum(cs["score"] for cs in category_scores)
            / max(1, len(category_scores))
        ) if category_scores else 100

        return {
            "overall_score": overall,
            "grade": self.grade_for_score(overall),
            "maturity": _resolve_compliance_maturity(config, self.client_id),
            "category_scores": category_scores,
            "total_rules_evaluated": total_applicable,
            "total_passed": total_passed,
            "total_failed": total_applicable - total_passed,
            "advisory_failed_ids": sorted(all_advisory_failed),
            "advisory_total": len(all_advisory_failed),
        }

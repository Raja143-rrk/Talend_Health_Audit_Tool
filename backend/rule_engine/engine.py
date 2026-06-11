from typing import Any

from backend.rag.registry import get_registered_rule_ids, lookup_rule, resolve_rag_fields, resolve_severity, resolve_category
from backend.rule_engine.models import Rule, RuleCategory, RuleScope
from backend.rule_engine.rules import DEFAULT_RULES
from backend.shared.models import AgentFinding, FindingSeverity

SEVERITY_ORDER = {
    FindingSeverity.INFORMATIONAL: 0,
    FindingSeverity.ADVISORY: 1,
    FindingSeverity.WARNING: 2,
    FindingSeverity.RISK: 3,
    FindingSeverity.CRITICAL_RISK: 4,
}


class RuleEngine:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules = rules or list(DEFAULT_RULES)

    def register(self, rule: Rule) -> None:
        self.rules.append(rule)

    def evaluate(
        self,
        payload: dict[str, Any],
        categories: set[RuleCategory] | None = None,
    ) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            if categories is not None and rule.category not in categories:
                continue
            findings.extend(self._evaluate_rule(rule, payload))
        return self.standardize_findings(findings)

    def standardize_findings(
        self,
        findings: list[AgentFinding],
        source_agent: str | None = None,
        domain: RuleCategory | str | None = None,
    ) -> list[AgentFinding]:
        return self._dedupe_findings(
            [
                self._standardize_finding(
                    finding=finding,
                    source_agent=source_agent,
                    domain=domain,
                )
                for finding in findings
            ]
        )

    def validate_findings(
        self,
        findings: list[AgentFinding],
        source_agent: str,
        domain: RuleCategory | str,
    ) -> list[AgentFinding]:
        registered_ids = get_registered_rule_ids()
        compliant = [
            f for f in findings
            if f.rule_triggered in registered_ids
            or str(f.evidence.get("rule_id")) in registered_ids
        ]
        return self.standardize_findings(
            findings=compliant,
            source_agent=source_agent,
            domain=domain,
        )

    def configure(self, rule_overrides: dict[str, dict[str, Any]]) -> None:
        for rule in self.rules:
            override = rule_overrides.get(rule.id)
            if not override:
                continue
            if "enabled" in override:
                rule.enabled = bool(override["enabled"])
            if "severity" in override:
                rule.severity = override["severity"]

    def _evaluate_rule(self, rule: Rule, payload: dict[str, Any]) -> list[AgentFinding]:
        targets = self._targets_for_scope(rule.scope, payload)
        findings: list[AgentFinding] = []
        for target in targets:
            if rule.predicate(target, payload):
                findings.append(
                    rule.to_finding(
                        target,
                        evidence=self._evidence_for_target(rule.scope, target),
                    )
                )
        return findings

    def _targets_for_scope(self, scope: RuleScope, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if scope == RuleScope.INVENTORY:
            return [payload]
        if scope == RuleScope.JOB:
            return list(payload.get("jobs", []))
        if scope == RuleScope.COMPONENT:
            components: list[dict[str, Any]] = []
            for job in payload.get("jobs", []):
                for component in job.get("components", []):
                    component_with_job = {**component, "job": job.get("name"), "job_path": job.get("path")}
                    components.append(component_with_job)
            components.extend(payload.get("components", []))
            return components
        return []

    def _evidence_for_target(self, scope: RuleScope, target: dict[str, Any]) -> dict[str, Any]:
        if scope == RuleScope.JOB:
            return {
                "job": target.get("name"),
                "path": target.get("path"),
                "component_count": len(target.get("components", [])),
            }
        if scope == RuleScope.COMPONENT:
            return {
                "job": target.get("job"),
                "job_path": target.get("job_path"),
                "component": target.get("name"),
                "component_name": target.get("component_name"),
                "component_type": target.get("component_type") or target.get("component_name"),
            }
        return {
            "jobs": len(target.get("jobs", [])),
            "components": len(target.get("components", [])),
        }

    def _standardize_finding(
        self,
        finding: AgentFinding,
        source_agent: str | None,
        domain: RuleCategory | str | None,
    ) -> AgentFinding:
        rule_id = str(finding.evidence.get("rule_id") or finding.rule_triggered or finding.id)
        rag_fields = resolve_rag_fields(rule_id)
        remediation = self._remediation_for(rule_id, finding)
        normalized_domain = domain.value if isinstance(domain, RuleCategory) else domain
        severity = self._resolve_severity(rule_id, finding.severity)
        category = rag_fields["category"] if rag_fields["category"] != "unknown" else str(finding.category)
        job_name = str(
            finding.evidence.get("job_name")
            or finding.evidence.get("job")
            or (finding.job_name if finding.job_name != "unknown" else None)
            or "unknown"
        )
        component_name = str(
            finding.evidence.get("component")
            or (finding.component_name if finding.component_name != "unknown" else None)
            or finding.evidence.get("component_name")
            or finding.evidence.get("target")
            or "unknown"
        )
        component_type = str(
            finding.evidence.get("component_type")
            or (finding.component_type if finding.component_type != "unknown" else None)
            or finding.evidence.get("component_name")
            or "unknown"
        )
        rule_triggered = str(
            finding.rule_triggered
            or finding.evidence.get("rule_triggered")
            or rule_id
        )

        impact = (
            finding.impact
            or rag_fields["impact"]
            or ""
        )
        source = (
            finding.source
            or rag_fields["source"]
            or ""
        )

        evidence = {
            **finding.evidence,
            "rule_id": rule_id,
            "rule_triggered": rule_triggered,
            "job_name": job_name,
            "component_name": component_name,
            "component_type": component_type,
            "source_agent": source_agent or finding.evidence.get("source_agent"),
            "domain": normalized_domain or finding.evidence.get("domain") or category,
            "severity": severity.value,
            "remediation": remediation,
            "recommendation": finding.recommendation or finding.evidence.get("recommendation") or remediation,
            "impact": impact,
            "source": source,
            "rag_classification": rag_fields,
            "validated_by_rule_engine": True,
        }

        return AgentFinding(
            id=finding.id,
            title=finding.title,
            job_name=job_name,
            component_name=component_name,
            component_type=component_type,
            category=category,
            severity=severity,
            rule_triggered=rule_triggered,
            description=finding.description,
            impact=impact,
            recommendation=str(evidence["recommendation"]),
            source=source,
            evidence=evidence,
        )

    def _resolve_severity(
        self,
        rule_id: str,
        fallback: FindingSeverity,
    ) -> FindingSeverity:
        rag_sev = resolve_severity(rule_id)
        try:
            return FindingSeverity(rag_sev)
        except ValueError:
            rule = self._rule_by_id(rule_id)
            if rule is not None:
                return rule.severity
            return fallback

    def _remediation_for(self, rule_id: str, finding: AgentFinding) -> str:
        rule = self._rule_by_id(rule_id)
        if rule is not None:
            return rule.remediation

        for key in ("remediation", "recommendation", "optimization_suggestion"):
            value = finding.evidence.get(key)
            if value:
                return str(value)
        return "Review the finding evidence and apply the relevant Talend remediation pattern."

    def _rule_by_id(self, rule_id: str) -> Rule | None:
        return next((rule for rule in self.rules if rule.id == rule_id), None)

    def _max_severity(
        self,
        left: FindingSeverity,
        right: FindingSeverity,
    ) -> FindingSeverity:
        return left if SEVERITY_ORDER[left] >= SEVERITY_ORDER[right] else right

    def _dedupe_findings(self, findings: list[AgentFinding]) -> list[AgentFinding]:
        deduped: list[AgentFinding] = []
        seen: set[tuple[str, ...]] = set()
        for finding in findings:
            evidence = finding.evidence
            key = (
                str(evidence.get("rule_id") or finding.id),
                str(evidence.get("job_name") or evidence.get("job") or finding.job_name or ""),
                str(evidence.get("component_name") or evidence.get("component") or finding.component_name or ""),
                str(evidence.get("component_type") or finding.component_type or ""),
                str(evidence.get("xml_path") or evidence.get("location") or ""),
                str(evidence.get("parameter_name") or ""),
                str(evidence.get("target") or ""),
                str(evidence.get("snippet") or evidence.get("matched_value") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(finding)
        return deduped

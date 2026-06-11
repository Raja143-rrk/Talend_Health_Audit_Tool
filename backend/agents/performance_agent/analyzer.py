from backend.agents.performance_agent.rules import (
    DEFAULT_PERFORMANCE_RULES,
    PerformanceRule,
    commit_size,
    component_name,
)
from backend.rag.registry import resolve_rag_fields
from backend.shared.models import AgentFinding, AgentRecommendation, FindingSeverity

ANALYZER_TO_RAG_RULE_MAP: dict[str, str] = {
    "PERF-TJAVA-001": "RULE-PERF-001",
    "PERF-TMAP-001": "RULE-PERF-002",
    "PERF-COMMIT-001": "RULE-PERF-003",
    "PERF-LOOP-001": "RULE-PERF-006",
    "PERF-ROW-001": "RULE-PERF-004",
    "PERF-PARALLEL-001": "RULE-PERF-006",
}


class PerformanceAnalyzer:
    def __init__(self, rules: list[PerformanceRule] | None = None) -> None:
        self.rules = rules or DEFAULT_PERFORMANCE_RULES

    def analyze(self, inventory: dict | None) -> tuple[list[AgentFinding], list[AgentRecommendation], dict]:
        if not inventory:
            return [], [], {
                "performance_findings": 0,
                "performance_findings_by_severity": {},
                "performance_findings_by_category": {},
                "jobs_analyzed": 0,
            }

        findings: list[AgentFinding] = []
        for job in inventory.get("jobs", []):
            findings.extend(self._evaluate_job(job))

        recommendations = self._build_recommendations(findings)
        metrics = self._build_metrics(findings, len(inventory.get("jobs", [])))
        return findings, recommendations, metrics

    def _evaluate_job(self, job: dict) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for rule in self.rules:
            if not rule.predicate(job):
                continue
            rag_rule_id = ANALYZER_TO_RAG_RULE_MAP.get(rule.id, rule.id)
            rag_fields = resolve_rag_fields(rag_rule_id)
            try:
                severity = FindingSeverity(rag_fields["severity"])
            except ValueError:
                severity = FindingSeverity.INFORMATIONAL
            category = rag_fields["category"]

            for component in self._affected_components(job, rule):
                component_name = str(component.get("name") or "component")
                component_type = str(component.get("component_name") or "unknown")
                job_name = str(job.get("name") or "unknown")
                findings.append(
                    AgentFinding(
                        id=f"{rule.id}-{self._safe_job_id(job)}-{self._safe_component_id(component)}",
                        title=rule.title,
                        job_name=job_name,
                        component_name=component_name,
                        component_type=component_type,
                        category=category,
                        severity=severity,
                        rule_triggered=rag_rule_id,
                        description=(
                            f"{rule.title} in job '{job_name}' component "
                            f"'{component_name}'."
                        ),
                        impact=rag_fields["impact"],
                        recommendation=rag_fields["remediation"] or rule.recommendation,
                        source=rag_fields["source"],
                        evidence={
                            "rule_id": rag_rule_id,
                            "rule_triggered": rag_rule_id,
                            "analyzer_rule_id": rule.id,
                            "rule_title": rule.title,
                            "job_name": job_name,
                            "component_name": component_name,
                            "component_type": component_type,
                            "xml_file": job.get("path"),
                            "xml_path": (
                                f"/job[@name='{job_name}']"
                                f"/component[@name='{component_name}']"
                            ),
                            "matched_value": self._matched_value(component, rule),
                            "component_count": len(job.get("components", [])),
                            "recommendation": rag_fields["remediation"] or rule.recommendation,
                            "optimization_suggestion": rule.optimization_suggestion,
                            "remediation": rag_fields["remediation"] or rule.recommendation,
                        },
                    )
                )
        return findings

    def _build_recommendations(self, findings: list[AgentFinding]) -> list[AgentRecommendation]:
        recommendations: list[AgentRecommendation] = []
        seen_categories: set[str] = set()

        for finding in findings:
            if finding.category in seen_categories:
                continue
            seen_categories.add(finding.category)
            priority = "P1" if finding.severity.value == "critical_risk" else "P2"
            if finding.severity.value in ("warning", "advisory", "informational"):
                priority = "P3"

            recommendations.append(
                AgentRecommendation(
                    id=f"PERF-REC-{len(recommendations) + 1:03d}",
                    title=f"Optimize {finding.category.replace('_', ' ')}",
                    category=finding.category,
                    severity=finding.severity.value,
                    priority=priority,
                    job_name=finding.job_name,
                    component_name=finding.component_name,
                    component_type=finding.component_type,
                    rule_triggered=finding.rule_triggered,
                    finding_id=finding.id,
                    rationale=finding.description,
                    action=str(finding.evidence.get("recommendation")),
                    expected_impact=str(finding.evidence.get("optimization_suggestion")),
                )
            )

        return recommendations

    def _build_metrics(self, findings: list[AgentFinding], jobs_analyzed: int) -> dict:
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for finding in findings:
            by_severity[finding.severity.value] = by_severity.get(finding.severity.value, 0) + 1
            by_category[finding.category] = by_category.get(finding.category, 0) + 1

        return {
            "performance_findings": len(findings),
            "performance_findings_by_severity": by_severity,
            "performance_findings_by_category": by_category,
            "jobs_analyzed": jobs_analyzed,
        }

    def _component_summary(self, job: dict) -> list[dict[str, str | bool]]:
        return [
            {
                "name": str(component.get("name")),
                "component_name": str(component.get("component_name")),
                "disabled": bool(component.get("disabled")),
            }
            for component in job.get("components", [])
        ]

    def _affected_components(self, job: dict, rule: PerformanceRule) -> list[dict]:
        components = [
            component
            for component in job.get("components", [])
            if not component.get("disabled")
        ]
        if rule.category == "excessive_tjava":
            return [component for component in components if component_name(component) in {"tjava", "tjavarow", "tjavaflex"}]
        if rule.category == "nested_loops":
            return [component for component in components if "loop" in component_name(component) or component_name(component) in {"tforeach", "tfilelist", "tloop"}]
        if rule.category == "row_processing":
            return [component for component in components if component_name(component) in {"tjavarow", "tflowtoiterate", "titeratetoflow"} or "row" in component_name(component)]
        if rule.category == "missing_parallelization":
            return [component for component in components if "input" in component_name(component) or "output" in component_name(component)]
        if rule.category == "commit_size_issues":
            return [
                component
                for component in components
                if "output" in component_name(component)
                and commit_size(component) is not None
                and commit_size(component) <= 100
            ]
        if rule.category == "heavy_tmap_usage":
            return [component for component in components if component_name(component) == "tmap"]
        return components

    def _matched_value(self, component: dict, rule: PerformanceRule) -> str:
        if rule.category == "commit_size_issues":
            value = commit_size(component)
            return f"commit_size={value}" if value is not None else "commit_size"
        return str(component.get("component_name") or rule.category)

    def _safe_job_id(self, job: dict) -> str:
        value = str(job.get("name") or "unknown")
        return "".join(character if character.isalnum() else "-" for character in value).strip("-")

    def _safe_component_id(self, component: dict) -> str:
        value = str(component.get("name") or component.get("component_name") or "component")
        return "".join(character if character.isalnum() else "-" for character in value).strip("-")

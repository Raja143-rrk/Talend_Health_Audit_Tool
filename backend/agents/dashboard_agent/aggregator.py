from collections import Counter
from typing import Any

from backend.agents.dashboard_agent.models import (
    DashboardChartData,
    DashboardKpi,
    DashboardResponse,
)
from backend.agents.dashboard_agent.scoring import (
    ComplianceScoringEngine,
)
from backend.core.logging import get_logger


logger = get_logger(__name__)


class DashboardAggregator:
    def __init__(
        self,
        compliance_engine: ComplianceScoringEngine | None = None,
        client_id: str | None = None,
    ) -> None:
        self.compliance_engine = compliance_engine or ComplianceScoringEngine(client_id=client_id)
        self.client_id = client_id

    def aggregate(self, context_payload: dict[str, Any]) -> DashboardResponse:
        inventory = context_payload.get("talend_inventory") or {}
        security_findings = context_payload.get("security_findings") or []
        performance_findings = context_payload.get("performance_findings") or []
        recommendations = context_payload.get("recommendations") or []
        all_findings = [*security_findings, *performance_findings]

        active_components, disabled_components = self._split_components(inventory)
        job_names = self._job_names(inventory)
        total_jobs = len(job_names)
        total_components = len(active_components)
        total_disabled_components = len(disabled_components)
        self._log_count_debug(inventory, job_names, total_jobs, total_components)
        active_findings = self._filter_findings_for_active(all_findings, active_components)
        severity_summary = self._severity_summary(active_findings)
        critical_issues = severity_summary.get("critical_risk", 0)
        compliance_breakdown = self.compliance_engine.calculate(active_findings)
        compliance_score = int(compliance_breakdown["overall_score"])
        compliance_grade = str(compliance_breakdown["grade"])
        compliance_maturity = str(compliance_breakdown.get("maturity", "standard"))

        return DashboardResponse(
            analysis_id=str(context_payload.get("analysis_id")),
            project_name=str(
                inventory.get("project_name")
                or context_payload.get("project_name")
                or "Talend Health Analyzer"
            ),
            total_jobs=total_jobs,
            job_names=job_names,
            total_components=total_components,
            total_disabled_components=total_disabled_components,
            critical_issues=critical_issues,
            compliance_score=compliance_score,
            compliance_grade=compliance_grade,
            compliance_maturity=compliance_maturity,
            compliance_breakdown=compliance_breakdown,
            kpis=[
                DashboardKpi(label="Compliance Score", value=compliance_score, suffix="%", severity=compliance_grade),
                DashboardKpi(label="Total Jobs", value=total_jobs, severity="informational"),
                DashboardKpi(label="Total Components", value=total_components, severity="informational"),
                DashboardKpi(label="Disabled Components", value=total_disabled_components, severity="warning"),
                DashboardKpi(label="Critical Issues", value=critical_issues, severity="critical_risk"),
                DashboardKpi(label="Security Findings", value=len(security_findings), severity="warning"),
                DashboardKpi(label="Performance Findings", value=len(performance_findings), severity="warning"),
            ],
            severity_summary=severity_summary,
            score_breakdown=compliance_breakdown,
            charts=self._chart_data(
                inventory,
                active_components,
                disabled_components,
                security_findings,
                performance_findings,
                severity_summary,
                compliance_breakdown,
            ),
            recommendations=recommendations,
            findings=all_findings,
            component_traceability=self._component_traceability(all_findings, recommendations),
            remediation_mapping=self._remediation_mapping(all_findings),
        )

    def _split_components(
        self,
        inventory: dict,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        all_components = inventory.get("components", [])
        active: list[dict[str, Any]] = []
        disabled: list[dict[str, Any]] = []
        for component in all_components:
            if component.get("disabled"):
                disabled.append(component)
            else:
                active.append(component)
        return active, disabled

    def _filter_findings_for_active(
        self,
        findings: list[dict],
        active_components: list[dict],
    ) -> list[dict]:
        active_names: set[str] = {
            str(comp.get("name") or "")
            for comp in active_components
            if comp.get("name")
        }
        if not active_names:
            return findings
        filtered: list[dict] = []
        for finding in findings:
            evidence = finding.get("evidence") or {}
            fc = str(finding.get("component_name") or evidence.get("component_name") or "")
            if fc in active_names:
                filtered.append(finding)
        return filtered

    def _job_names(self, inventory: dict) -> list[str]:
        raw_job_names = inventory.get("job_names")
        if isinstance(raw_job_names, list):
            return sorted(
                {
                    str(job_name)
                    for job_name in raw_job_names
                    if str(job_name).strip()
                }
            )

        jobs = inventory.get("jobs", [])
        if not isinstance(jobs, list):
            return []

        return sorted(
            {
                str(job.get("name"))
                for job in jobs
                if isinstance(job, dict)
                and job.get("item_type") == "job_design"
                and str(job.get("name") or "").strip()
            }
        )

    def _log_count_debug(
        self,
        inventory: dict,
        job_names: list[str],
        total_jobs: int,
        total_components: int,
    ) -> None:
        raw_jobs = inventory.get("jobs", [])
        if isinstance(raw_jobs, list):
            for job in raw_jobs:
                if not isinstance(job, dict):
                    logger.info(
                        "[COUNT-DEBUG] Dashboard ignored job object: value=%s reason=invalid_job_payload",
                        job,
                    )
                    continue
                logger.info(
                    "[COUNT-DEBUG] Dashboard job input: name=%s item_type=%s components=%s counted=%s",
                    job.get("name") or "unknown",
                    job.get("item_type") or "unknown",
                    len(job.get("components", [])) if isinstance(job.get("components"), list) else 0,
                    job.get("item_type") == "job_design",
                )
        else:
            logger.info(
                "[COUNT-DEBUG] Dashboard ignored jobs payload: value_type=%s reason=jobs_not_list",
                type(raw_jobs).__name__,
            )

        raw_components = inventory.get("components", [])
        if isinstance(raw_components, list):
            for component in raw_components:
                if not isinstance(component, dict):
                    logger.info(
                        "[COUNT-DEBUG] Dashboard ignored component object: value=%s reason=invalid_component_payload",
                        component,
                    )
                    continue
                logger.info(
                    "[COUNT-DEBUG] Dashboard component input: name=%s type=%s counted=True",
                    component.get("name") or "unknown",
                    component.get("component_name") or "unknown",
                )
        else:
            logger.info(
                "[COUNT-DEBUG] Dashboard ignored components payload: value_type=%s reason=components_not_list",
                type(raw_components).__name__,
            )

        logger.info(
            "[COUNT-DEBUG] Final dashboard counts: total_jobs=%s job_names=%s total_components=%s",
            total_jobs,
            job_names,
            total_components,
        )

    def _severity_summary(self, findings: list[dict]) -> dict[str, int]:
        summary = {"critical_risk": 0, "risk": 0, "warning": 0, "advisory": 0, "informational": 0}
        for finding in findings:
            severity = str(finding.get("severity", "informational")).lower()
            if severity in summary:
                summary[severity] += 1
        return summary

    def _chart_data(
        self,
        inventory: dict,
        active_components: list[dict],
        disabled_components: list[dict],
        security_findings: list[dict],
        performance_findings: list[dict],
        severity_summary: dict[str, int],
        compliance_breakdown: dict[str, Any],
    ) -> DashboardChartData:
        def _distribution(components: list[dict]) -> list[dict]:
            counts = Counter(
                str(c.get("component_name") or "unknown")
                for c in components
            )
            return [
                {"name": name, "value": value}
                for name, value in counts.most_common()
            ]

        source_systems = set(inventory.get("source_systems", []))
        target_systems = set(inventory.get("target_systems", []))

        return DashboardChartData(
            component_distribution=_distribution([*active_components, *disabled_components]),
            active_component_distribution=_distribution(active_components),
            disabled_component_distribution=_distribution(disabled_components),
            severity_summary=[
                {"name": severity, "value": count}
                for severity, count in severity_summary.items()
            ],
            issue_categories=self._issue_categories(security_findings, performance_findings),
            source_target_systems=[
                {
                    "name": system,
                    "source": 1 if system in source_systems else 0,
                    "target": 1 if system in target_systems else 0,
                }
                for system in sorted(source_systems | target_systems)
            ],
            score_breakdown=[
                {"name": category_score["label"], "value": category_score["score"]}
                for category_score in compliance_breakdown.get("category_scores", [])
            ],
        )

    def _issue_categories(
        self,
        security_findings: list[dict],
        performance_findings: list[dict],
    ) -> list[dict]:
        counts = Counter()
        for finding in security_findings:
            counts[f"security:{finding.get('category', 'unknown')}"] += 1
        for finding in performance_findings:
            counts[f"performance:{finding.get('category', 'unknown')}"] += 1
        return [{"name": name, "value": value} for name, value in counts.items()]

    def _remediation_mapping(self, findings: list[dict]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for finding in findings:
            evidence = finding.get("evidence") or {}
            remediation = evidence.get("remediation")
            if remediation:
                mapping[str(finding.get("id"))] = str(remediation)
        return mapping

    def _component_traceability(
        self,
        findings: list[dict],
        recommendations: list[dict],
    ) -> list[dict]:
        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
        for finding in findings:
            evidence = finding.get("evidence") or {}
            key = self._component_key(finding, evidence)
            grouped.setdefault(
                key,
                {
                    "job_name": key[0],
                    "component_name": key[1],
                    "component_type": key[2],
                    "finding_ids": [],
                    "recommendation_ids": [],
                },
            )["finding_ids"].append(str(finding.get("id") or "finding"))

        for recommendation in recommendations:
            key = (
                str(recommendation.get("job_name") or "unknown"),
                str(recommendation.get("component_name") or "unknown"),
                str(recommendation.get("component_type") or "unknown"),
            )
            if key == ("unknown", "unknown", "unknown"):
                continue
            grouped.setdefault(
                key,
                {
                    "job_name": key[0],
                    "component_name": key[1],
                    "component_type": key[2],
                    "finding_ids": [],
                    "recommendation_ids": [],
                },
            )["recommendation_ids"].append(str(recommendation.get("id") or "recommendation"))

        return sorted(
            grouped.values(),
            key=lambda item: (item["job_name"], item["component_name"], item["component_type"]),
        )

    def _component_key(
        self,
        finding: dict,
        evidence: dict,
    ) -> tuple[str, str, str]:
        return (
            str(finding.get("job_name") or evidence.get("job_name") or evidence.get("job") or "unknown"),
            str(
                finding.get("component_name")
                or evidence.get("component")
                or evidence.get("component_name")
                or evidence.get("target")
                or "unknown"
            ),
            str(
                finding.get("component_type")
                or evidence.get("component_type")
                or evidence.get("component_name")
                or "unknown"
            ),
        )

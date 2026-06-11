from datetime import datetime, timezone
from typing import Any

from backend.core.exceptions import AppError
from backend.schemas.dashboard import (
    AgentStatusInfo,
    AnalysisLog,
    AnalysisStatusResponse,
    ChartDataResponse,
    ChartPoint,
    DashboardMetric,
    DashboardOverviewResponse,
    ComponentDrillDown,
    DashboardSummaryResponse,
    Finding,
    FindingsResponse,
    Recommendation,
    RecommendationsResponse,
)
from backend.services.analysis_service import AnalysisRecord, analysis_service


class DashboardService:
    def get_analysis_status(self, analysis_id: str | None = None) -> AnalysisStatusResponse:
        record = self._record_or_latest(analysis_id)
        workflow_state = record.workflow_state or {}
        execution_order = workflow_state.get("execution_order", [])
        current_step = record.current_agent or self._current_step(record.status.value)

        return AnalysisStatusResponse(
            analysis_id=record.analysis_id,
            status=record.status.value,
            progress=record.progress,
            current_step=current_step,
            logs=[
                AnalysisLog(
                    timestamp=self._format_time(record.created_at),
                    level="info",
                    message="Analysis queued",
                ),
                *[
                    AnalysisLog(
                        timestamp=self._format_time(record.updated_at),
                        level="info",
                        message=f"{agent_name} completed",
                    )
                    for agent_name in execution_order
                ],
                *[
                    AnalysisLog(
                        timestamp=self._format_time(record.updated_at),
                        level="error",
                        message=str(error),
                    )
                    for error in [*record.errors, *workflow_state.get("errors", [])]
                ],
            ],
        )

    def get_dashboard_overview(
        self,
        analysis_id: str | None = None,
    ) -> DashboardOverviewResponse:
        record = self._record_or_latest(analysis_id)
        return DashboardOverviewResponse(
            analysis_id=record.analysis_id,
            status=record.status.value,
            summary=self.get_dashboard_summary(record.analysis_id),
            charts=self.get_chart_data(record.analysis_id),
            recommendations=self.get_recommendations(record.analysis_id),
            security_findings=self.get_security_findings(record.analysis_id),
            performance_findings=self.get_performance_findings(record.analysis_id),
            component_drilldown=self.get_component_drilldown(record.analysis_id),
            agents=self._get_agent_statuses(record),
        )

    def get_dashboard_summary(
        self,
        analysis_id: str | None = None,
    ) -> DashboardSummaryResponse:
        record = self._record_or_latest(analysis_id)
        dashboard = self._dashboard(record)
        kpis = dashboard.get("kpis") or []

        return DashboardSummaryResponse(
            project_name=str(dashboard.get("project_name") or "Talend Health Analyzer"),
            environment="analysis",
            total_jobs=int(dashboard.get("total_jobs") or 0),
            job_names=[
                str(job_name)
                for job_name in dashboard.get("job_names", [])
                if str(job_name).strip()
            ],
            compliance_score=int(dashboard.get("compliance_score") or 100),
            compliance_grade=str(dashboard.get("compliance_grade") or "Optimized"),
            compliance_maturity=str(dashboard.get("compliance_maturity") or "standard"),
            compliance_breakdown=dashboard.get("compliance_breakdown"),
            last_analyzed_at=self._last_analyzed_at(record),
            metrics=[self._dashboard_metric(kpi) for kpi in kpis],
            score_breakdown=dashboard.get("score_breakdown") or self._empty_score_breakdown(),
        )

    def get_chart_data(self, analysis_id: str | None = None) -> ChartDataResponse:
        record = self._record_or_latest(analysis_id)
        dashboard = self._dashboard(record)
        charts = dashboard.get("charts") or {}
        security_findings = self._security_finding_payloads(record)
        performance_findings = self._performance_finding_payloads(record)

        return ChartDataResponse(
            component_distribution=self._chart_points(charts.get("component_distribution", [])),
            active_component_distribution=self._chart_points(charts.get("active_component_distribution", [])),
            disabled_component_distribution=self._chart_points(charts.get("disabled_component_distribution", [])),
            performance_issues=self._issue_chart_points(performance_findings),
            security_issues=self._issue_chart_points(security_findings),
            source_target_systems=self._chart_points(
                charts.get("source_target_systems")
                or [{"name": "MS SQL Server", "source": 1, "target": 1}]
            ),
            score_breakdown=self._chart_points(charts.get("score_breakdown", [])),
            risk_timeline=self._risk_timeline(record, dashboard),
        )

    def get_security_findings(self, analysis_id: str | None = None) -> FindingsResponse:
        record = self._record_or_latest(analysis_id)
        findings = [
            self._finding(finding, owner="Security")
            for finding in self._security_finding_payloads(record)
        ]
        return FindingsResponse(total=len(findings), items=findings)

    def get_performance_findings(self, analysis_id: str | None = None) -> FindingsResponse:
        record = self._record_or_latest(analysis_id)
        findings = [
            self._finding(finding, owner="Performance")
            for finding in self._performance_finding_payloads(record)
        ]
        return FindingsResponse(total=len(findings), items=findings)

    def get_recommendations(self, analysis_id: str | None = None) -> RecommendationsResponse:
        record = self._record_or_latest(analysis_id)
        component_recs = self._component_recommendations(record)
        agent_recs = [
            self._recommendation(rec)
            for rec in self._agent_recommendations(record)
            if rec.get("category") == "cleanup"
        ]
        all_recs = [*component_recs, *agent_recs]
        return RecommendationsResponse(total=len(all_recs), items=all_recs)

    def get_component_drilldown(self, analysis_id: str | None = None) -> list[ComponentDrillDown]:
        record = self._record_or_latest(analysis_id)
        findings = [
            *self.get_security_findings(record.analysis_id).items,
            *self.get_performance_findings(record.analysis_id).items,
        ]
        recommendations = self.get_recommendations(record.analysis_id).items
        grouped: dict[tuple[str, str, str], ComponentDrillDown] = {}

        for finding in findings:
            key = (finding.job_name, finding.component_name, finding.component_type)
            drilldown = grouped.setdefault(
                key,
                ComponentDrillDown(
                    job_name=finding.job_name,
                    component_name=finding.component_name,
                    component_type=finding.component_type,
                ),
            )
            drilldown.findings.append(finding)

        for recommendation in recommendations:
            if not recommendation.job_name or not recommendation.component_name:
                continue
            key = (
                recommendation.job_name,
                recommendation.component_name,
                recommendation.component_type or "unknown",
            )
            drilldown = grouped.setdefault(
                key,
                ComponentDrillDown(
                    job_name=key[0],
                    component_name=key[1],
                    component_type=key[2],
                ),
            )
            drilldown.recommendations.append(recommendation)

        return sorted(
            grouped.values(),
            key=lambda item: (item.job_name, item.component_name, item.component_type),
        )

    def _record_or_latest(self, analysis_id: str | None) -> AnalysisRecord:
        if analysis_id:
            return analysis_service.get_record(analysis_id)

        record = analysis_service.get_latest_record()
        if record is None:
            raise AppError(message="No analysis is available for dashboard data.", status_code=404)
        return record

    def _dashboard(self, record: AnalysisRecord) -> dict[str, Any]:
        if record.dashboard is None:
            raise AppError(
                message="Dashboard is not available until dashboard-agent completes.",
                status_code=202,
            )
        return record.dashboard

    def _metadata(self, record: AnalysisRecord) -> dict[str, Any]:
        workflow_state = record.workflow_state or {}
        context = workflow_state.get("context") or {}
        metadata = context.get("metadata") or {}
        return metadata if isinstance(metadata, dict) else {}

    def _security_finding_payloads(self, record: AnalysisRecord) -> list[dict[str, Any]]:
        metadata = self._metadata(record)
        findings = metadata.get("security_findings")
        if isinstance(findings, list):
            return [finding for finding in findings if isinstance(finding, dict)]
        agent_findings = self._agent_findings(record, "security-agent")
        if agent_findings:
            return agent_findings
        return self._findings_by_domain(record, "security")

    def _performance_finding_payloads(self, record: AnalysisRecord) -> list[dict[str, Any]]:
        metadata = self._metadata(record)
        findings = metadata.get("performance_findings")
        if isinstance(findings, list):
            return [finding for finding in findings if isinstance(finding, dict)]
        agent_findings = self._agent_findings(record, "performance-agent")
        if agent_findings:
            return agent_findings
        return self._findings_by_domain(record, "performance")

    def _agent_outputs(self, record: AnalysisRecord) -> dict[str, Any]:
        workflow_state = record.workflow_state or {}
        context = workflow_state.get("context") or {}
        metadata = context.get("metadata") or {}
        if isinstance(metadata, dict) and isinstance(metadata.get("agent_outputs"), dict):
            return metadata["agent_outputs"]
        outputs = workflow_state.get("agent_outputs")
        return outputs if isinstance(outputs, dict) else {}

    def _agent_findings(self, record: AnalysisRecord, agent_name: str) -> list[dict[str, Any]]:
        output = self._agent_outputs(record).get(agent_name)
        if not isinstance(output, dict):
            return []
        findings = output.get("findings")
        if not isinstance(findings, list):
            return []
        return [finding for finding in findings if isinstance(finding, dict)]

    def _agent_recommendations(self, record: AnalysisRecord) -> list[dict[str, Any]]:
        output = self._agent_outputs(record).get("recommendation-agent")
        if not isinstance(output, dict):
            return []
        recommendations = output.get("recommendations")
        if not isinstance(recommendations, list):
            return []
        return [
            recommendation
            for recommendation in recommendations
            if isinstance(recommendation, dict)
        ]

    def _get_agent_statuses(self, record: AnalysisRecord) -> list[AgentStatusInfo]:
        agent_definitions = [
            AgentStatusInfo(
                name="parser-agent",
                label="Parser Agent",
                description="Parses Talend project XML files into jobs, components, and contextual metadata",
                status="pending",
            ),
            AgentStatusInfo(
                name="security-agent",
                label="Security Agent",
                description="Scans for security vulnerabilities including exposed secrets, hardcoded credentials, and insecure configurations",
                status="pending",
            ),
            AgentStatusInfo(
                name="performance-agent",
                label="Performance Agent",
                description="Analyzes runtime efficiency such as tMap usage, parallelization, commit sizes, and resource utilization",
                status="pending",
            ),
            AgentStatusInfo(
                name="recommendation-agent",
                label="Recommendation Agent",
                description="Generates prioritized remediation recommendations using AI classification and RAG context",
                status="pending",
            ),
            AgentStatusInfo(
                name="dashboard-agent",
                label="Dashboard Agent",
                description="Aggregates all agent results, computes health scores and risk levels, and produces the consolidated dashboard",
                status="pending",
            ),
        ]

        outputs = self._agent_outputs(record)
        for agent in agent_definitions:
            output = outputs.get(agent.name)
            if not isinstance(output, dict):
                continue
            agent.status = output.get("status", agent.status)
            agent.duration_ms = output.get("duration_ms")
            findings = output.get("findings")
            if isinstance(findings, list):
                agent.findings_count = len(findings)
            agent_errors = output.get("errors")
            if isinstance(agent_errors, list):
                agent.errors = [str(e) for e in agent_errors if e]
        return agent_definitions

    def _findings_by_domain(self, record: AnalysisRecord, domain: str) -> list[dict[str, Any]]:
        findings = (record.dashboard or {}).get("findings") or []
        filtered: list[dict[str, Any]] = []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            evidence = finding.get("evidence") or {}
            if str(evidence.get("domain") or finding.get("category") or "").startswith(domain):
                filtered.append(finding)
        return filtered

    def _dashboard_metric(self, value: dict[str, Any]) -> DashboardMetric:
        return DashboardMetric(
            label=str(value.get("label") or "Metric"),
            value=int(value.get("value") or 0),
            suffix=value.get("suffix"),
            change=str(value.get("change") or ""),
            severity=str(value.get("severity") or "informational"),
        )

    def _empty_score_breakdown(self) -> dict[str, Any]:
        return {
            "overall_score": 100,
            "grade": "Optimized",
            "category_scores": [],
        }

    def _chart_points(self, values: list[dict[str, Any]]) -> list[ChartPoint]:
        return [ChartPoint(**value) for value in values if isinstance(value, dict)]

    def _issue_chart_points(self, findings: list[dict[str, Any]]) -> list[ChartPoint]:
        grouped: dict[str, dict[str, int | str]] = {}
        for finding in findings:
            category = str(finding.get("category") or "unknown")
            severity = str(finding.get("severity") or "informational").lower()
            bucket = grouped.setdefault(
                category,
                {"name": category, "critical_risk": 0, "risk": 0, "warning": 0, "advisory": 0},
            )
            if severity in {"critical_risk", "risk", "warning"}:
                bucket[severity] = int(bucket.get(severity, 0)) + 1
            else:
                bucket["advisory"] = int(bucket.get("advisory", 0)) + 1
        return [ChartPoint(**value) for value in grouped.values()]

    def _risk_timeline(self, record: AnalysisRecord, dashboard: dict[str, Any]) -> list[ChartPoint]:
        severity_summary = dashboard.get("severity_summary") or {}
        return [
            ChartPoint(
                name=self._format_date(record.updated_at),
                critical_risk=int(severity_summary.get("critical_risk", 0)),
                risk=int(severity_summary.get("risk", 0)),
                warning=int(severity_summary.get("warning", 0)),
                advisory=int(severity_summary.get("advisory", 0)),
                informational=int(severity_summary.get("informational", 0)),
            )
        ]

    def _finding(self, value: dict[str, Any], owner: str) -> Finding:
        evidence = value.get("evidence") or {}
        recommendation = self._finding_recommendation(value)
        return Finding(
            id=str(value.get("id") or evidence.get("rule_id") or "finding"),
            name=str(value.get("title") or value.get("name") or "Finding"),
            job_name=str(value.get("job_name") or evidence.get("job_name") or evidence.get("job") or "unknown"),
            component_name=str(
                value.get("component_name")
                or evidence.get("component")
                or evidence.get("component_name")
                or evidence.get("target")
                or "unknown"
            ),
            component_type=str(
                value.get("component_type")
                or evidence.get("component_type")
                or evidence.get("component_name")
                or "unknown"
            ),
            category=str(value.get("category") or evidence.get("domain") or "unknown"),
            severity=str(value.get("severity") or evidence.get("severity") or "informational"),
            rule_triggered=str(
                value.get("rule_triggered")
                or evidence.get("rule_triggered")
                or evidence.get("rule_id")
                or value.get("id")
                or "unknown"
            ),
            status=str(value.get("status") or "open"),
            owner=str(value.get("owner") or owner),
            impact=str(value.get("description") or value.get("impact") or ""),
            recommendation=recommendation,
            remediation=evidence.get("remediation"),
            evidence=evidence if isinstance(evidence, dict) else {},
        )

    def _recommendation(self, value: dict[str, Any]) -> Recommendation:
        return Recommendation(
            id=str(value.get("id") or "recommendation"),
            title=str(value.get("title") or "Recommendation"),
            category=str(value.get("category") or "recommendation"),
            severity=str(value.get("severity") or value.get("priority") or "informational"),
            priority=str(value.get("priority") or "P3"),
            job_name=value.get("job_name"),
            component_name=value.get("component_name"),
            component_type=value.get("component_type"),
            rule_triggered=value.get("rule_triggered"),
            finding_id=value.get("finding_id"),
            suggestion=str(value.get("action") or value.get("suggestion") or value.get("summary") or ""),
            expected_impact=str(value.get("expected_impact") or ""),
            rationale=value.get("rationale"),
        )

    def _component_recommendations(self, record: AnalysisRecord) -> list[Recommendation]:
        findings = [
            *[
                self._finding(finding, owner="Security")
                for finding in self._security_finding_payloads(record)
            ],
            *[
                self._finding(finding, owner="Performance")
                for finding in self._performance_finding_payloads(record)
            ],
        ]
        recommendations: list[Recommendation] = []
        for index, finding in enumerate(findings, start=1):
            recommendations.append(
                Recommendation(
                    id=f"COMP-REC-{index:03d}",
                    title=f"Remediate {finding.component_name}: {finding.name}",
                    category=finding.category,
                    severity=finding.severity,
                    priority=self._priority_for_severity(finding.severity),
                    job_name=finding.job_name,
                    component_name=finding.component_name,
                    component_type=finding.component_type,
                    rule_triggered=finding.rule_triggered,
                    finding_id=finding.id,
                    suggestion=finding.recommendation,
                    expected_impact=str(
                        finding.evidence.get("optimization_suggestion")
                        or finding.evidence.get("expected_impact")
                        or "Reduces risk and improves component maintainability."
                    ),
                    rationale=finding.impact,
                )
            )
        return recommendations

    def _finding_recommendation(self, value: dict[str, Any]) -> str:
        evidence = value.get("evidence") or {}
        return str(
            value.get("recommendation")
            or evidence.get("recommendation")
            or evidence.get("remediation")
            or evidence.get("optimization_suggestion")
            or "Review this component and apply the rule-specific remediation."
        )

    def _priority_for_severity(self, severity: str) -> str:
        normalized = severity.lower()
        if normalized == "critical":
            return "P1"
        if normalized == "high":
            return "P2"
        return "P3"

    def _current_step(self, status_value: str) -> str:
        if status_value == "completed":
            return "Dashboard ready"
        if status_value == "failed":
            return "Analysis failed"
        if status_value == "partial":
            return "Dashboard partially ready"
        return "Analysis queued"

    def _last_analyzed_at(self, record: AnalysisRecord) -> str:
        return (record.completed_at or record.updated_at).isoformat()

    def _format_time(self, value: datetime) -> str:
        return value.astimezone(timezone.utc).strftime("%H:%M:%S")

    def _format_date(self, value: datetime) -> str:
        return value.astimezone(timezone.utc).strftime("%Y-%m-%d")


dashboard_service = DashboardService()

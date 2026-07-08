from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.core.exceptions import AppError
from backend.core.logging import get_logger
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
    OperationalPerformanceMetrics,
    Recommendation,
    RecommendationsResponse,
)
from backend.services.analysis_service import AnalysisRecord, analysis_service


logger = get_logger(__name__)


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
        job_name: str | None = None,
    ) -> DashboardOverviewResponse:
        record = self._record_or_latest(analysis_id)
        return DashboardOverviewResponse(
            analysis_id=record.analysis_id,
            status=record.status.value,
            summary=self.get_dashboard_summary(record.analysis_id, job_name),
            charts=self.get_chart_data(record.analysis_id, job_name),
            recommendations=self.get_recommendations(record.analysis_id, job_name),
            security_findings=self.get_security_findings(record.analysis_id, job_name),
            performance_findings=self.get_performance_findings(record.analysis_id, job_name),
            operational_performance=self._get_operational_performance_metrics(record, job_name),
            component_drilldown=self.get_component_drilldown(record.analysis_id, job_name),
            agents=self._get_agent_statuses(record),
        )

    def _get_operational_performance_metrics(
        self,
        record: AnalysisRecord,
        job_name: str | None = None,
    ) -> OperationalPerformanceMetrics:
        logger.info("=== DEBUG PERFORMANCE ===")
        logger.info("Project Selected (analysis_id): %s", record.analysis_id)
        logger.info("Job Name filter: %s", job_name or "none")

        try:
            from backend.execution_logs.records.service import get_execution_record_service
            svc = get_execution_record_service()
            exec_records = svc.get_records(record.analysis_id, job_name)

            logger.info("Execution Records Loaded: %d", len(exec_records))

            if exec_records:
                logger.info("Records Used For Performance: %d", len(exec_records))
                for rec in exec_records:
                    logger.info("  Record: artifact=%s status=%s start=%s end=%s duration=%s",
                                rec.artifact_name or "(empty)",
                                rec.execution_status or "(empty)",
                                rec.execution_start_time.isoformat()
                                if rec.execution_start_time else "null",
                                rec.execution_end_time.isoformat()
                                if rec.execution_end_time else "null",
                                rec.execution_duration_seconds
                                if rec.execution_duration_seconds is not None else "null")
                raw_dicts = [
                    {
                        "job_name": rec.job_name,
                        "status": (rec.execution_status or "unknown").lower(),
                        "started_at": rec.execution_start_time,
                        "finished_at": rec.execution_end_time,
                        "duration_seconds": rec.execution_duration_seconds,
                        "error_message": rec.error_message or "",
                        "execution_id": rec.plan_execution_id or rec.task_execution_id or "",
                    }
                    for rec in exec_records
                    if rec.job_name
                ]
                logger.info("Branch: computing performance from %d raw dicts",
                             len(raw_dicts))
                return self._compute_performance_from_raw_dicts(raw_dicts)
        except ImportError:
            logger.info("Branch: ImportError, falling back to file storage")

        logger.info("Branch: No execution records found, trying file storage")
        from backend.execution_logs.storage.file_storage import FileStorage

        storage = FileStorage()
        all_records = storage.list_all()
        logs_for_project = [r for r in all_records if r.project_id == record.analysis_id]

        logger.info("File storage records: %d", len(logs_for_project))
        if logs_for_project:
            logger.info("Branch: computing from %d file storage records",
                        len(logs_for_project))
            try:
                return self._compute_performance_from_logs(logs_for_project, job_name)
            except Exception as exc:
                logger.exception("File storage performance computation failed: %s", exc)
                pass

        logger.info("Branch: trying agent output fallback")
        perf_agent_output = self._agent_outputs(record).get("performance-agent", {})
        metrics = perf_agent_output.get("metrics", {})
        if isinstance(metrics, dict) and metrics.get("total_executions", 0) > 0:
            logger.info("Using agent output metrics with %d executions",
                        metrics["total_executions"])
            return OperationalPerformanceMetrics(
                performance_score=metrics.get("performance_score", 100),
                performance_grade=metrics.get("performance_grade", "Optimized"),
                overall_failure_rate=float(metrics.get("overall_failure_rate", 0.0)),
                total_executions=int(metrics.get("total_executions", 0)),
                total_failures=int(metrics.get("total_failures", 0)),
                recurring_failures=int(metrics.get("recurring_failures", 0)),
                average_duration_seconds=float(metrics.get("average_duration_seconds", 0.0)),
                max_duration_seconds=float(metrics.get("max_duration_seconds", 0.0)),
                min_duration_seconds=float(metrics.get("min_duration_seconds", 0.0)),
                average_restart_delay_hours=float(metrics.get("average_restart_delay_hours", 0.0)),
                total_restarts=int(metrics.get("total_restarts", 0)),
                top_5_longest_jobs=metrics.get("top_5_longest_jobs", []),
                daily_trend=metrics.get("daily_trend", []),
                failed_jobs_count=int(metrics.get("failed_jobs_count", 0)),
                failed_executions=metrics.get("failed_executions", []),
                error_groups=metrics.get("error_groups", {}),
                has_execution_data=True,
            )

        logger.info("Branch: No performance data found in any layer \u2014 returning empty metrics (--)")
        return OperationalPerformanceMetrics()

    def _compute_performance_from_raw_dicts(self, raw_dicts: list[dict]) -> OperationalPerformanceMetrics:
        from backend.agents.performance_agent.analyzer import PerformanceAnalyzer

        if not raw_dicts:
            logger.info("Branch: No raw dicts to compute performance from \u2014 returning empty")
            return OperationalPerformanceMetrics()

        analyzer = PerformanceAnalyzer()
        _, _, metrics = analyzer.analyze(raw_dicts)

        return OperationalPerformanceMetrics(
            performance_score=metrics.get("performance_score", 100),
            performance_grade=metrics.get("performance_grade", "Optimized"),
            overall_failure_rate=float(metrics.get("overall_failure_rate", 0.0)),
            total_executions=int(metrics.get("total_executions", 0)),
            total_failures=int(metrics.get("total_failures", 0)),
            recurring_failures=int(metrics.get("recurring_failures", 0)),
            average_duration_seconds=float(metrics.get("average_duration_seconds", 0.0)),
            max_duration_seconds=float(metrics.get("max_duration_seconds", 0.0)),
            min_duration_seconds=float(metrics.get("min_duration_seconds", 0.0)),
            average_restart_delay_hours=float(metrics.get("average_restart_delay_hours", 0.0)),
            total_restarts=int(metrics.get("total_restarts", 0)),
            top_5_longest_jobs=metrics.get("top_5_longest_jobs", []),
            daily_trend=metrics.get("daily_trend", []),
            failed_jobs_count=int(metrics.get("failed_jobs_count", 0)),
            failed_executions=metrics.get("failed_executions", []),
            error_groups=metrics.get("error_groups", {}),
            has_execution_data=True,
        )

    def _compute_performance_from_logs(
        self,
        upload_records: list,
        job_name: str | None = None,
    ) -> OperationalPerformanceMetrics:
        raw_dicts: list[dict] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=10)

        for upload_rec in upload_records:
            for entry in upload_rec.entries:
                started_at = entry.start_time if hasattr(entry, "start_time") else getattr(entry, "started_at", None)
                finished_at = entry.end_time if hasattr(entry, "end_time") else getattr(entry, "finished_at", None)

                if started_at and isinstance(started_at, datetime):
                    if started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=timezone.utc)
                    if started_at < cutoff:
                        continue

                raw_dicts.append({
                    "job_name": entry.job_name or "unknown",
                    "status": (entry.status or "unknown").lower(),
                    "started_at": started_at,
                    "finished_at": finished_at if (hasattr(entry, "end_time") or hasattr(entry, "finished_at")) else None,
                    "duration_seconds": entry.duration_seconds,
                    "error_message": entry.error_message or "",
                    "execution_id": entry.execution_id or "",
                })

        if job_name:
            raw_dicts = [d for d in raw_dicts if d["job_name"] == job_name]

        return self._compute_performance_from_raw_dicts(raw_dicts)

    def get_dashboard_summary(
        self,
        analysis_id: str | None = None,
        job_name: str | None = None,
    ) -> DashboardSummaryResponse:
        record = self._record_or_latest(analysis_id)
        dashboard = self._dashboard(record)
        kpis = dashboard.get("kpis") or []

        job_names = [
            str(jn) for jn in dashboard.get("job_names", []) if str(jn).strip()
        ]
        subjob_names = [
            str(n) for n in dashboard.get("subjob_names", []) if str(n).strip()
        ]
        master_job_names = [
            str(n) for n in dashboard.get("master_job_names", []) if str(n).strip()
        ]

        if job_name:
            job_names = [jn for jn in job_names if jn == job_name]
            subjob_names = [n for n in subjob_names if n == job_name]
            master_job_names = [n for n in master_job_names if n == job_name]
            kpis = self._filtered_kpis(record, job_name, kpis)
        else:
            total, active, disabled = self._get_all_component_counts(record)
            kpi_map = {str(kpi.get("label")): dict(kpi) for kpi in kpis}
            kpi_map["Total Components"] = {"label": "Total Components", "value": total, "severity": "informational"}
            kpi_map["Active Components"] = {"label": "Active Components", "value": active, "severity": "informational"}
            kpi_map["Disabled Components"] = {"label": "Disabled Components", "value": disabled, "severity": "informational"}
            kpis = list(kpi_map.values())

        return DashboardSummaryResponse(
            project_name=str(dashboard.get("project_name") or "Talend Health Analyzer"),
            environment="analysis",
            total_jobs=len(job_names),
            job_names=job_names,
            total_subjobs=len(subjob_names),
            total_master_jobs=len(master_job_names),
            subjob_names=subjob_names,
            master_job_names=master_job_names,
            compliance_score=int(dashboard.get("compliance_score") or 100),
            compliance_grade=str(dashboard.get("compliance_grade") or "Optimized"),
            compliance_maturity=str(dashboard.get("compliance_maturity") or "standard"),
            compliance_breakdown=dashboard.get("compliance_breakdown"),
            last_analyzed_at=self._last_analyzed_at(record),
            metrics=[self._dashboard_metric(kpi) for kpi in kpis],
            score_breakdown=dashboard.get("score_breakdown") or self._empty_score_breakdown(),
        )

    def get_chart_data(self, analysis_id: str | None = None, job_name: str | None = None) -> ChartDataResponse:
        record = self._record_or_latest(analysis_id)
        dashboard = self._dashboard(record)
        charts = dashboard.get("charts") or {}
        security_findings = self._security_finding_payloads(record)
        performance_findings = self._performance_finding_payloads(record)

        if job_name:
            security_findings = [f for f in security_findings if self._finding_job_name(f) == job_name]
            performance_findings = [f for f in performance_findings if self._finding_job_name(f) == job_name]

        all_comps = self._get_inventory_components(record, job_name)
        active_comps = [c for c in all_comps if not c.get("disabled", False)]
        disabled_comps = [c for c in all_comps if c.get("disabled", False)]
        _name = lambda c: str(c.get("component_name") or c.get("name") or "unknown")
        component_distribution = [ChartPoint(name=n, value=v) for n, v in Counter(_name(c) for c in all_comps).most_common()]
        active_component_distribution = [ChartPoint(name=n, value=v) for n, v in Counter(_name(c) for c in active_comps).most_common()]
        disabled_component_distribution = [ChartPoint(name=n, value=v) for n, v in Counter(_name(c) for c in disabled_comps).most_common()]

        return ChartDataResponse(
            component_distribution=component_distribution,
            active_component_distribution=active_component_distribution,
            disabled_component_distribution=disabled_component_distribution,
            performance_issues=self._issue_chart_points(performance_findings),
            security_issues=self._issue_chart_points(security_findings),
            source_target_systems=self._chart_points(
                charts.get("source_target_systems")
                or [{"name": "MS SQL Server", "source": 1, "target": 1}]
            ),
            score_breakdown=self._chart_points(charts.get("score_breakdown", [])),
            risk_timeline=self._risk_timeline(record, dashboard),
        )

    def get_security_findings(self, analysis_id: str | None = None, job_name: str | None = None) -> FindingsResponse:
        record = self._record_or_latest(analysis_id)
        dashboard = self._dashboard(record)
        subjob_set = set(dashboard.get("subjob_names", []))
        findings = [
            f for payload in self._security_finding_payloads(record)
            if not job_name or self._finding_job_name(payload) == job_name
            for f in [self._finding(payload, owner="Security", subjob_set=subjob_set)]
        ]
        return FindingsResponse(total=len(findings), items=findings)

    def get_performance_findings(self, analysis_id: str | None = None, job_name: str | None = None) -> FindingsResponse:
        record = self._record_or_latest(analysis_id)
        dashboard = self._dashboard(record)
        subjob_set = set(dashboard.get("subjob_names", []))
        findings = [
            f for payload in self._performance_finding_payloads(record)
            if not job_name or self._finding_job_name(payload) == job_name
            for f in [self._finding(payload, owner="Performance", subjob_set=subjob_set)]
        ]
        return FindingsResponse(total=len(findings), items=findings)

    def get_recommendations(self, analysis_id: str | None = None, job_name: str | None = None) -> RecommendationsResponse:
        record = self._record_or_latest(analysis_id)
        component_recs = self._component_recommendations(record)
        agent_recs = [
            self._recommendation(rec)
            for rec in self._agent_recommendations(record)
            if rec.get("category") == "cleanup"
        ]
        all_recs = [*component_recs, *agent_recs]
        if job_name:
            all_recs = [r for r in all_recs if r.job_name and r.job_name == job_name]
        return RecommendationsResponse(total=len(all_recs), items=all_recs)

    def get_component_drilldown(self, analysis_id: str | None = None, job_name: str | None = None) -> list[ComponentDrillDown]:
        record = self._record_or_latest(analysis_id)
        findings = [
            *self.get_security_findings(record.analysis_id, job_name).items,
            *self.get_performance_findings(record.analysis_id, job_name).items,
        ]
        recommendations = self.get_recommendations(record.analysis_id, job_name).items
        grouped: dict[tuple[str, str, str], ComponentDrillDown] = {}

        all_comps = self._get_inventory_components(record, job_name)
        for comp in all_comps:
            cname = str(comp.get("name") or comp.get("component_name") or "unknown")
            ctype = str(comp.get("component_name") or "unknown")
            if cname == ctype:
                continue
            jn = comp.get("_job_name", "unknown")
            key = (jn, cname, ctype)
            if key not in grouped:
                grouped[key] = ComponentDrillDown(
                    job_name=jn,
                    component_name=cname,
                    component_type=ctype,
                )

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
            [v for v in grouped.values() if v.component_name != v.component_type],
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

    def _finding(self, value: dict[str, Any], owner: str, subjob_set: set[str] | None = None) -> Finding:
        evidence = value.get("evidence") or {}
        recommendation = self._finding_recommendation(value)
        job_name = str(value.get("job_name") or evidence.get("job_name") or evidence.get("job") or "unknown")
        return Finding(
            id=str(value.get("id") or evidence.get("rule_id") or "finding"),
            name=str(value.get("title") or value.get("name") or "Finding"),
            job_name=job_name,
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
            subjob_name=job_name if subjob_set and job_name in subjob_set else "",
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

    def _filtered_kpis(self, record, job_name: str, original_kpis: list[dict[str, Any]]) -> list[dict[str, Any]]:
        security_payloads = self._security_finding_payloads(record)
        performance_payloads = self._performance_finding_payloads(record)
        security_payloads = [f for f in security_payloads if self._finding_job_name(f) == job_name]
        performance_payloads = [f for f in performance_payloads if self._finding_job_name(f) == job_name]
        all_filtered = [*security_payloads, *performance_payloads]
        critical_count = sum(
            1 for f in all_filtered
            if str(f.get("severity") or "").lower() in {"critical", "critical_risk"}
        )
        total_components, active_components, disabled_components = self._get_job_component_counts(record, job_name)
        kpi_map = {str(kpi.get("label")): dict(kpi) for kpi in original_kpis}
        kpi_map["Total Jobs"] = {"label": "Total Jobs", "value": 1, "severity": "informational"}
        kpi_map["Critical Issues"] = {"label": "Critical Issues", "value": critical_count, "severity": "critical_risk" if critical_count else "informational"}
        kpi_map["Security Findings"] = {"label": "Security Findings", "value": len(security_payloads), "severity": "warning" if security_payloads else "informational"}
        kpi_map["Performance Findings"] = {"label": "Performance Findings", "value": len(performance_payloads), "severity": "warning" if performance_payloads else "informational"}
        kpi_map["Total Components"] = {"label": "Total Components", "value": total_components, "severity": "informational"}
        kpi_map["Active Components"] = {"label": "Active Components", "value": active_components, "severity": "informational"}
        kpi_map["Disabled Components"] = {"label": "Disabled Components", "value": disabled_components, "severity": "informational"}
        return list(kpi_map.values())

    def _get_all_component_counts(self, record) -> tuple[int, int, int]:
        all_comps = self._get_inventory_components(record, None)
        total = len(all_comps)
        disabled = sum(1 for c in all_comps if c.get("disabled", False))
        active = max(0, total - disabled)
        return (total, active, disabled)

    def _get_job_component_counts(self, record, job_name: str) -> tuple[int, int, int]:
        all_comps = self._get_inventory_components(record, job_name)
        total = len(all_comps)
        disabled = sum(1 for c in all_comps if c.get("disabled", False))
        active = max(0, total - disabled)
        return (total, active, disabled)

    def _get_inventory_components(self, record, job_name: str | None) -> list[dict]:
        metadata = self._metadata(record)
        inventory = metadata.get("talend_inventory", {})
        if not isinstance(inventory, dict):
            return []
        jobs = inventory.get("jobs", [])
        if not isinstance(jobs, list):
            return []
        result: list[dict] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            jn = job.get("name", "unknown")
            if job_name and jn != job_name:
                continue
            comps = job.get("components", [])
            if not isinstance(comps, list):
                continue
            for comp in comps:
                if not isinstance(comp, dict):
                    continue
                entry = dict(comp)
                entry["_job_name"] = jn
                result.append(entry)
        return result

    def _finding_job_name(self, value: dict[str, Any]) -> str:
        evidence = value.get("evidence") or {}
        return str(value.get("job_name") or evidence.get("job_name") or evidence.get("job") or "unknown")

    def _finding_component_type(self, value: dict[str, Any]) -> str:
        evidence = value.get("evidence") or {}
        return str(
            value.get("component_type")
            or evidence.get("component_type")
            or evidence.get("component_name")
            or "unknown"
        )

    def _finding_component_name(self, value: dict[str, Any]) -> str:
        evidence = value.get("evidence") or {}
        return str(
            value.get("component_name")
            or evidence.get("component")
            or evidence.get("component_name")
            or evidence.get("target")
            or "unknown"
        )

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

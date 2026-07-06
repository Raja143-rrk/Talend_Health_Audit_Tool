from collections import Counter
from datetime import timezone

from backend.agents.performance_agent.operational.failure_analyzer import FailureAnalyzer
from backend.agents.performance_agent.operational.latency_analyzer import LatencyAnalyzer
from backend.agents.performance_agent.operational.log_parser import LogParser
from backend.agents.performance_agent.operational.models import (
    ExecutionLogEntry,
    OperationalMetrics,
)
from backend.agents.performance_agent.operational.restart_delay_analyzer import (
    RestartDelayAnalyzer,
)
from backend.agents.performance_agent.operational.score_calculator import (
    PerformanceScoreCalculator,
)
from backend.agents.performance_agent.rules import (
    DEFAULT_PERFORMANCE_RULES,
    PerformanceRule,
)
from backend.core.logging import get_logger
from backend.shared.models import AgentFinding, AgentRecommendation, FindingSeverity

OP_RULE_CATEGORY_MAP: dict[str, str] = {
    "PERF-OP-001": "failure_frequency",
    "PERF-OP-002": "recurring_failures",
    "PERF-OP-003": "execution_latency",
    "PERF-OP-004": "restart_delay",
    "PERF-OP-005": "failure_frequency",
}

OP_RULE_SEVERITY_MAP: dict[str, str] = {
    "PERF-OP-001": "risk",
    "PERF-OP-002": "warning",
    "PERF-OP-003": "warning",
    "PERF-OP-004": "advisory",
    "PERF-OP-005": "advisory",
}

logger = get_logger(__name__)


class PerformanceAnalyzer:
    def __init__(
        self,
        rules: list[PerformanceRule] | None = None,
        log_parser: LogParser | None = None,
        failure_analyzer: FailureAnalyzer | None = None,
        latency_analyzer: LatencyAnalyzer | None = None,
        restart_delay_analyzer: RestartDelayAnalyzer | None = None,
        score_calculator: PerformanceScoreCalculator | None = None,
    ) -> None:
        self.rules = rules or DEFAULT_PERFORMANCE_RULES
        self.log_parser = log_parser or LogParser()
        self.failure_analyzer = failure_analyzer or FailureAnalyzer()
        self.latency_analyzer = latency_analyzer or LatencyAnalyzer()
        self.restart_delay_analyzer = restart_delay_analyzer or RestartDelayAnalyzer()
        self.score_calculator = score_calculator or PerformanceScoreCalculator()

    def analyze(
        self,
        execution_logs: list[dict] | None = None,
    ) -> tuple[list[AgentFinding], list[AgentRecommendation], dict]:
        parsed_logs = self.log_parser.parse(execution_logs)

        if not parsed_logs:
            logger.info("No execution logs to analyze.")
            return [], [], self._empty_metrics()

        failure_freq, failed_execs = self.failure_analyzer.analyze(parsed_logs)
        latency = self.latency_analyzer.analyze(parsed_logs)
        restart_delay = self.restart_delay_analyzer.analyze(parsed_logs)
        daily_trend = self._compute_daily_trend(parsed_logs)

        perf_score = self.score_calculator.calculate(failure_freq, latency, restart_delay)

        operational_metrics = OperationalMetrics(
            failure_frequency=failure_freq,
            execution_latency=latency,
            failed_executions=failed_execs,
            restart_delay=restart_delay,
            performance_score=perf_score,
        )

        findings = self._evaluate_rules(parsed_logs, operational_metrics)
        recommendations = self._build_recommendations(findings)
        metrics = self._build_metrics(findings, operational_metrics)

        logger.info(
            "Operational analysis complete: %d findings, score=%d",
            len(findings),
            perf_score.overall_score,
        )

        return findings, recommendations, metrics

    def _evaluate_rules(
        self,
        logs: list[ExecutionLogEntry],
        operational_metrics: OperationalMetrics,
    ) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for rule in self.rules:
            if not rule.predicate(logs):
                continue

            rule_id = rule.id
            severity_str = OP_RULE_SEVERITY_MAP.get(rule_id, "advisory")
            try:
                severity = FindingSeverity(severity_str)
            except ValueError:
                severity = FindingSeverity.INFORMATIONAL

            detail = self._rule_detail(rule_id, operational_metrics)

            findings.append(
                AgentFinding(
                    id=f"{rule_id}-op",
                    title=rule.title,
                    job_name=detail.get("job_name", "multiple"),
                    component_name=detail.get("component_name", "execution"),
                    component_type=detail.get("component_type", "operational"),
                    category=OP_RULE_CATEGORY_MAP.get(rule_id, "operational"),
                    severity=severity,
                    rule_triggered=rule_id,
                    description=(
                        f"{rule.title}: {detail.get('summary', 'Operational issue detected')}."
                    ),
                    impact=detail.get("impact", "May affect system reliability and performance."),
                    recommendation=rule.recommendation,
                    source="operational_analysis",
                    evidence={
                        "rule_id": rule_id,
                        "rule_triggered": rule_id,
                        "rule_title": rule.title,
                        "category": OP_RULE_CATEGORY_MAP.get(rule_id, "operational"),
                        "metric_value": detail.get("metric_value"),
                        "metric_unit": detail.get("metric_unit"),
                        "threshold": detail.get("threshold"),
                        "summary": detail.get("summary", ""),
                        "job_name": detail.get("job_name", "multiple"),
                        "remediation": rule.recommendation,
                        "optimization_suggestion": rule.optimization_suggestion,
                    },
                )
            )

        return findings

    def _rule_detail(
        self,
        rule_id: str,
        metrics: OperationalMetrics,
    ) -> dict:
        if rule_id == "PERF-OP-001":
            return {
                "job_name": "multiple",
                "component_name": "execution",
                "component_type": "operational",
                "metric_value": metrics.failure_frequency.overall_failure_rate,
                "metric_unit": "%",
                "threshold": 20.0,
                "summary": f"Overall failure rate is {metrics.failure_frequency.overall_failure_rate:.1f}%",
                "impact": "High failure rate indicates unstable jobs requiring immediate attention.",
            }
        if rule_id == "PERF-OP-002":
            recurring = metrics.failure_frequency.recurring_failures
            return {
                "job_name": "multiple",
                "component_name": "execution",
                "component_type": "operational",
                "metric_value": len(recurring),
                "metric_unit": "jobs",
                "threshold": 0,
                "summary": f"{len(recurring)} job(s) with recurring failures: {', '.join(recurring[:5])}",
                "impact": "Recurring failures indicate systemic issues that need root cause analysis.",
            }
        if rule_id == "PERF-OP-003":
            return {
                "job_name": "multiple",
                "component_name": "execution",
                "component_type": "operational",
                "metric_value": metrics.execution_latency.average_duration_seconds,
                "metric_unit": "seconds",
                "threshold": 300.0,
                "summary": f"Average execution duration is {metrics.execution_latency.average_duration_seconds:.1f}s",
                "impact": "High latency impacts data freshness and overall system throughput.",
            }
        if rule_id == "PERF-OP-004":
            return {
                "job_name": "multiple",
                "component_name": "execution",
                "component_type": "operational",
                "metric_value": metrics.restart_delay.average_delay_hours,
                "metric_unit": "hours",
                "threshold": 24.0,
                "summary": f"Average restart delay is {metrics.restart_delay.average_delay_hours:.1f}h",
                "impact": "Long restart delays increase data processing gaps and SLAs may be violated.",
            }
        if rule_id == "PERF-OP-005":
            failure_jobs = metrics.failure_frequency.job_failure_counts
            failing = [j for j, c in failure_jobs.items() if c > 0]
            return {
                "job_name": "multiple",
                "component_name": "execution",
                "component_type": "operational",
                "metric_value": len(failing),
                "metric_unit": "jobs",
                "threshold": 0,
                "summary": f"{len(failing)} job(s) have experienced failures",
                "impact": "Jobs with failures need review and potential redesign.",
            }
        return {}

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
                    title=f"Address {finding.category.replace('_', ' ')}",
                    category=finding.category,
                    severity=finding.severity.value,
                    priority=priority,
                    job_name=finding.job_name,
                    component_name=finding.component_name,
                    component_type=finding.component_type,
                    rule_triggered=finding.rule_triggered,
                    finding_id=finding.id,
                    rationale=finding.description,
                    action=str(finding.evidence.get("remediation")),
                    expected_impact=str(finding.evidence.get("optimization_suggestion")),
                )
            )

        return recommendations

    def _build_metrics(
        self,
        findings: list[AgentFinding],
        operational_metrics: OperationalMetrics,
    ) -> dict:
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for finding in findings:
            by_severity[finding.severity.value] = by_severity.get(finding.severity.value, 0) + 1
            by_category[finding.category] = by_category.get(finding.category, 0) + 1

        perf_score = operational_metrics.performance_score

        return {
            "performance_findings": len(findings),
            "performance_findings_by_severity": by_severity,
            "performance_findings_by_category": by_category,
            "performance_score": perf_score.overall_score,
            "performance_grade": perf_score.grade,
            "overall_failure_rate": operational_metrics.failure_frequency.overall_failure_rate,
            "total_executions": operational_metrics.failure_frequency.total_executions,
            "total_failures": operational_metrics.failure_frequency.total_failures,
            "recurring_failures": len(operational_metrics.failure_frequency.recurring_failures),
            "average_duration_seconds": operational_metrics.execution_latency.average_duration_seconds,
            "max_duration_seconds": operational_metrics.execution_latency.max_duration_seconds,
            "average_restart_delay_hours": operational_metrics.restart_delay.average_delay_hours,
            "total_restarts": operational_metrics.restart_delay.total_restarts,
            "top_5_longest_jobs": operational_metrics.execution_latency.top_5_longest_jobs,
            "daily_trend": daily_trend,
            "failed_jobs_count": operational_metrics.failed_executions.total_failed_jobs,
            "failed_executions": operational_metrics.failed_executions.failed_jobs,
            "error_groups": operational_metrics.failed_executions.error_groups,
        }

    def _empty_metrics(self) -> dict:
        return {
            "performance_findings": 0,
            "performance_findings_by_severity": {},
            "performance_findings_by_category": {},
            "performance_score": 100,
            "performance_grade": "Optimized",
            "overall_failure_rate": 0.0,
            "total_executions": 0,
            "total_failures": 0,
            "recurring_failures": 0,
            "average_duration_seconds": 0.0,
            "max_duration_seconds": 0.0,
            "average_restart_delay_hours": 0.0,
            "total_restarts": 0,
            "top_5_longest_jobs": [],
            "daily_trend": [],
            "failed_jobs_count": 0,
            "failed_executions": [],
            "error_groups": {},
        }

    def _compute_daily_trend(self, logs: list[ExecutionLogEntry]) -> list[dict]:
        if not logs:
            return []
        daily_executions: Counter[str] = Counter()
        daily_failures: Counter[str] = Counter()
        for entry in logs:
            if entry.started_at is None:
                continue
            day_key = entry.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
            daily_executions[day_key] += 1
            if entry.status == "failure":
                daily_failures[day_key] += 1
        all_days = sorted(daily_executions.keys())
        return [
            {
                "date": day,
                "executions": daily_executions.get(day, 0),
                "failures": daily_failures.get(day, 0),
            }
            for day in all_days
        ]

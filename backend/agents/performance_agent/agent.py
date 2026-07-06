from datetime import datetime
import asyncio

from backend.agents.base import BaseAgent
from backend.agents.performance_agent.analyzer import PerformanceAnalyzer
from backend.rule_engine.engine import RuleEngine
from backend.rule_engine.models import RuleCategory
from backend.rule_engine.rules.performance import PERFORMANCE_RULES
from backend.shared.models import (
    AgentArtifact,
    AgentContext,
    AgentResponse,
)

OP_RULE_SEVERITY_MAP: dict[str, str] = {
    "PERF-OP-001": "risk",
    "PERF-OP-002": "warning",
    "PERF-OP-003": "warning",
    "PERF-OP-004": "advisory",
    "PERF-OP-005": "advisory",
}


class PerformanceAgent(BaseAgent):
    name = "performance-agent"
    description = "Analyzes operational performance health based on execution logs."

    def __init__(
        self,
        analyzer: PerformanceAnalyzer | None = None,
        rule_engine: RuleEngine | None = None,
    ) -> None:
        super().__init__()
        self.analyzer = analyzer or PerformanceAnalyzer()
        self.rule_engine = rule_engine or RuleEngine(PERFORMANCE_RULES)

    async def execute(
        self,
        context: AgentContext,
        started_at: datetime,
    ) -> AgentResponse:
        execution_logs = self._resolve_execution_logs(context)
        operational_findings, operational_recommendations, operational_metrics = await asyncio.to_thread(
            self.analyzer.analyze,
            execution_logs,
        )

        inventory = self._resolve_inventory(context)
        rule_findings = await asyncio.to_thread(
            self.rule_engine.evaluate,
            self._build_rule_payload(inventory, operational_findings),
            {RuleCategory.PERFORMANCE},
        )

        findings = self.rule_engine.validate_findings(
            findings=[*operational_findings, *rule_findings],
            source_agent=self.name,
            domain=RuleCategory.PERFORMANCE,
        )

        metrics = self._build_metrics(
            operational_findings=operational_findings,
            operational_metrics=operational_metrics,
        )

        self.logger.info(
            "Operational performance scan completed for analysis %s: %s findings",
            context.analysis_id,
            len(findings),
        )

        return AgentResponse.completed(
            agent_name=self.name,
            started_at=started_at,
            artifacts=[
                AgentArtifact(
                    name="performance-analysis",
                    artifact_type="performance-report",
                    payload={
                        "findings": [finding.model_dump(mode="json") for finding in findings],
                        "recommendations": [
                            recommendation.model_dump(mode="json")
                            for recommendation in operational_recommendations
                        ],
                        "metrics": metrics,
                        "operational_metrics": operational_metrics,
                    },
                )
            ],
            findings=findings,
            recommendations=operational_recommendations,
            metrics=metrics,
        )

    def _build_rule_payload(self, inventory: dict | None, findings) -> dict:
        payload = dict(inventory or {})
        payload["performance_findings"] = [
            finding.model_dump(mode="json") for finding in findings
        ]
        payload["performance_findings_count"] = len(findings)
        return payload

    def _build_metrics(
        self,
        operational_findings: list,
        operational_metrics: dict,
    ) -> dict:
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for finding in operational_findings:
            by_severity[finding.severity.value] = by_severity.get(finding.severity.value, 0) + 1
            by_category[finding.category] = by_category.get(finding.category, 0) + 1

        return {
            **operational_metrics,
            "performance_findings": len(operational_findings),
            "performance_findings_by_severity": by_severity,
            "performance_findings_by_category": by_category,
        }

    def _resolve_execution_logs(self, context: AgentContext) -> list[dict] | None:
        from backend.execution_logs.storage.file_storage import FileStorage

        metadata_logs = context.metadata.get("execution_logs")
        if metadata_logs:
            return metadata_logs

        storage = FileStorage()
        all_records = storage.list_all()
        project_records = [r for r in all_records if r.project_id == context.analysis_id]

        if not project_records:
            return None

        raw_dicts: list[dict] = []
        for upload_rec in project_records:
            for entry in upload_rec.entries:
                started_at = entry.start_time if hasattr(entry, "start_time") else getattr(entry, "started_at", None)
                finished_at = entry.end_time if hasattr(entry, "end_time") else getattr(entry, "finished_at", None)
                raw_dicts.append({
                    "job_name": entry.job_name or "unknown",
                    "status": (entry.status or "unknown").lower(),
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duration_seconds": entry.duration_seconds,
                    "error_message": entry.error_message or "",
                    "execution_id": entry.execution_id or "",
                })
        return raw_dicts if raw_dicts else None

    def _resolve_inventory(self, context: AgentContext) -> dict | None:
        inventory = context.metadata.get("talend_inventory")
        if isinstance(inventory, dict):
            return inventory
        return None

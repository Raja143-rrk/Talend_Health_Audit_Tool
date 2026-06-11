from datetime import datetime
import asyncio

from backend.agents.base import BaseAgent
from backend.agents.dashboard_agent.aggregator import DashboardAggregator
from backend.rule_engine.engine import RuleEngine
from backend.rule_engine.models import RuleCategory
from backend.rule_engine.rules.performance import PERFORMANCE_RULES
from backend.rule_engine.rules.security import SECURITY_RULES
from backend.shared.models import AgentArtifact, AgentContext, AgentFinding, AgentResponse


class DashboardAgent(BaseAgent):
    name = "dashboard-agent"
    description = "Aggregates agent outputs into dashboard-ready summaries."

    def __init__(
        self,
        aggregator: DashboardAggregator | None = None,
        security_rule_engine: RuleEngine | None = None,
        performance_rule_engine: RuleEngine | None = None,
    ) -> None:
        super().__init__()
        self.aggregator = aggregator or DashboardAggregator()
        self.security_rule_engine = security_rule_engine or RuleEngine(SECURITY_RULES)
        self.performance_rule_engine = performance_rule_engine or RuleEngine(PERFORMANCE_RULES)

    async def execute(
        self,
        context: AgentContext,
        started_at: datetime,
    ) -> AgentResponse:
        context_payload = self._build_context_payload(context)
        context_payload = await asyncio.to_thread(
            self._standardize_context_findings,
            context_payload,
        )
        dashboard = await asyncio.to_thread(
            self.aggregator.aggregate,
            context_payload,
        )
        payload = dashboard.model_dump(mode="json")

        self.logger.info(
            "Generated dashboard for analysis %s",
            context.analysis_id,
        )

        return AgentResponse.completed(
            agent_name=self.name,
            started_at=started_at,
            artifacts=[
                AgentArtifact(
                    name="dashboard-response",
                    artifact_type="dashboard",
                    payload=payload,
                )
            ],
            metrics={
                "dashboard_views_prepared": 1,
                "critical_issues": dashboard.critical_issues,
                "total_jobs": dashboard.total_jobs,
                "total_components": dashboard.total_components,
            },
        )

    def _build_context_payload(self, context: AgentContext) -> dict:
        return {
            "analysis_id": context.analysis_id,
            "project_name": context.project_name,
            "talend_inventory": context.metadata.get("talend_inventory", {}),
            "security_findings": context.metadata.get("security_findings", []),
            "performance_findings": context.metadata.get("performance_findings", []),
            "recommendations": context.metadata.get("recommendations", []),
        }

    def _standardize_context_findings(self, payload: dict) -> dict:
        security_findings = self._to_agent_findings(payload.get("security_findings", []))
        performance_findings = self._to_agent_findings(payload.get("performance_findings", []))

        payload["security_findings"] = [
            finding.model_dump(mode="json")
            for finding in self.security_rule_engine.validate_findings(
                findings=security_findings,
                source_agent="security-agent",
                domain=RuleCategory.SECURITY,
            )
        ]
        payload["performance_findings"] = [
            finding.model_dump(mode="json")
            for finding in self.performance_rule_engine.validate_findings(
                findings=performance_findings,
                source_agent="performance-agent",
                domain=RuleCategory.PERFORMANCE,
            )
        ]
        return payload

    def _to_agent_findings(self, findings: list[dict]) -> list[AgentFinding]:
        parsed_findings: list[AgentFinding] = []
        for finding in findings:
            try:
                parsed_findings.append(AgentFinding.model_validate(finding))
            except Exception:
                self.logger.warning("Skipping invalid dashboard finding payload: %s", finding)
        return parsed_findings

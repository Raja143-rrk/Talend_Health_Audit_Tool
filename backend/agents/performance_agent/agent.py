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


class PerformanceAgent(BaseAgent):
    name = "performance-agent"
    description = "Analyzes performance anti-patterns in Talend job designs."

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
        inventory = self._resolve_inventory(context)
        analyzer_findings, analyzer_recommendations, analyzer_metrics = await asyncio.to_thread(
            self.analyzer.analyze,
            inventory,
        )
        rule_findings = await asyncio.to_thread(
            self.rule_engine.evaluate,
            self._build_rule_payload(inventory, analyzer_findings),
            {RuleCategory.PERFORMANCE},
        )
        findings = self.rule_engine.validate_findings(
            findings=[*analyzer_findings, *rule_findings],
            source_agent=self.name,
            domain=RuleCategory.PERFORMANCE,
        )
        findings = self._component_evidence_findings(findings)
        metrics = self._build_metrics(
            findings=findings,
            base_metrics=analyzer_metrics,
            jobs_analyzed=len(inventory.get("jobs", [])) if inventory else 0,
        )

        self.logger.info(
            "Performance scan completed for analysis %s: %s findings",
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
                            for recommendation in analyzer_recommendations
                        ],
                        "metrics": metrics,
                    },
                )
            ],
            findings=findings,
            recommendations=analyzer_recommendations,
            metrics=metrics,
        )

    def _component_evidence_findings(self, findings):
        required_evidence = {
            "job_name",
            "component_name",
            "component_type",
            "xml_file",
            "xml_path",
            "matched_value",
            "rule_triggered",
        }
        evidence_backed = []
        for finding in findings:
            evidence = finding.evidence or {}
            if all(evidence.get(key) for key in required_evidence):
                evidence_backed.append(finding)
            else:
                self.logger.info(
                    "Suppressing performance finding without component evidence: %s",
                    finding.id,
                )
        return evidence_backed

    def _build_rule_payload(self, inventory: dict | None, findings) -> dict:
        payload = dict(inventory or {})
        payload["performance_findings"] = [
            finding.model_dump(mode="json") for finding in findings
        ]
        payload["performance_findings_count"] = len(findings)
        return payload

    def _build_metrics(
        self,
        findings,
        base_metrics: dict,
        jobs_analyzed: int,
    ) -> dict:
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for finding in findings:
            by_severity[finding.severity.value] = by_severity.get(finding.severity.value, 0) + 1
            by_category[finding.category] = by_category.get(finding.category, 0) + 1

        return {
            **base_metrics,
            "performance_findings": len(findings),
            "performance_findings_by_severity": by_severity,
            "performance_findings_by_category": by_category,
            "jobs_analyzed": jobs_analyzed,
            "rule_engine_validated_findings": len(findings),
        }

    def _resolve_inventory(self, context: AgentContext) -> dict | None:
        inventory = context.metadata.get("talend_inventory")
        if isinstance(inventory, dict):
            return inventory
        return None

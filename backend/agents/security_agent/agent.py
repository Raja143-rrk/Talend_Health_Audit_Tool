from datetime import datetime
import asyncio

from backend.agents.base import BaseAgent
from backend.agents.security_agent.scanner import SecurityScanner
from backend.rule_engine.engine import RuleEngine
from backend.rule_engine.models import RuleCategory
from backend.rule_engine.rules.security import SECURITY_RULES
from backend.shared.models import (
    AgentArtifact,
    AgentContext,
    AgentResponse,
)


class SecurityAgent(BaseAgent):
    name = "security-agent"
    description = "Detects secrets, insecure contexts, and risky integration patterns."

    def __init__(
        self,
        scanner: SecurityScanner | None = None,
        rule_engine: RuleEngine | None = None,
    ) -> None:
        super().__init__()
        self.scanner = scanner or SecurityScanner()
        self.rule_engine = rule_engine or RuleEngine(SECURITY_RULES)

    async def execute(
        self,
        context: AgentContext,
        started_at: datetime,
    ) -> AgentResponse:
        workspace_path = self._resolve_workspace_path(context)
        inventory = self._resolve_inventory(context)
        findings, recommendations, metrics = await asyncio.to_thread(
            self.scanner.scan,
            workspace_path,
            inventory,
        )
        rule_findings = await asyncio.to_thread(
            self.rule_engine.evaluate,
            self._build_rule_payload(inventory, findings),
            {RuleCategory.SECURITY},
        )
        findings = self.rule_engine.validate_findings(
            findings=[*findings, *rule_findings],
            source_agent=self.name,
            domain=RuleCategory.SECURITY,
        )
        findings = self._evidence_backed_findings(findings)
        metrics = self._build_metrics(findings, metrics)

        self.logger.info(
            "Security scan completed for analysis %s: %s findings",
            context.analysis_id,
            len(findings),
        )

        return AgentResponse.completed(
            agent_name=self.name,
            started_at=started_at,
            artifacts=[
                AgentArtifact(
                    name="security-analysis",
                    artifact_type="security-report",
                    path=workspace_path,
                    payload={
                        "findings": [finding.model_dump(mode="json") for finding in findings],
                        "recommendations": [
                            recommendation.model_dump(mode="json")
                            for recommendation in recommendations
                        ],
                        "metrics": metrics,
                    },
                )
            ],
            findings=findings,
            recommendations=recommendations,
            metrics=metrics,
        )

    def _evidence_backed_findings(
        self,
        findings,
    ):
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
                    "Suppressing security finding without complete evidence: %s",
                    finding.id,
                )
        return evidence_backed

    def _build_rule_payload(
        self,
        inventory: dict | None,
        findings,
    ) -> dict:
        payload = dict(inventory or {})
        payload["security_findings"] = [
            finding.model_dump(mode="json") for finding in findings
        ]
        payload["security_findings_count"] = len(findings)
        return payload

    def _build_metrics(self, findings, base_metrics: dict) -> dict:
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for finding in findings:
            by_severity[finding.severity.value] = by_severity.get(finding.severity.value, 0) + 1
            by_category[finding.category] = by_category.get(finding.category, 0) + 1

        return {
            **base_metrics,
            "security_findings": len(findings),
            "security_findings_by_severity": by_severity,
            "security_findings_by_category": by_category,
            "rule_engine_validated_findings": len(findings),
        }

    def _resolve_workspace_path(self, context: AgentContext) -> str | None:
        workspace_path = context.metadata.get("workspace_path")
        if workspace_path:
            return str(workspace_path)

        extracted_workspace = context.metadata.get("extracted_workspace")
        if extracted_workspace:
            return str(extracted_workspace)

        return None

    def _resolve_inventory(self, context: AgentContext) -> dict | None:
        inventory = context.metadata.get("talend_inventory")
        if isinstance(inventory, dict):
            return inventory
        return None

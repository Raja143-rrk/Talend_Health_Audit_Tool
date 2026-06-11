from datetime import datetime
import asyncio
from pathlib import Path

from backend.agents.base import BaseAgent
from backend.shared.models import AgentArtifact, AgentContext, AgentResponse
from backend.agents.parser_agent.talend_parser import TalendParser

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ParserAgent(BaseAgent):
    name = "parser-agent"
    description = "Parses Talend jobs, contexts, metadata, and component graphs."

    def __init__(self, parser: TalendParser | None = None) -> None:
        super().__init__()
        self.parser = parser or TalendParser()

    async def execute(
        self,
        context: AgentContext,
        started_at: datetime,
    ) -> AgentResponse:
        workspace_path = self._resolve_workspace_path(context)
        inventory = await asyncio.to_thread(self.parser.parse_workspace, workspace_path)
        payload = inventory.model_dump()

        self.logger.info(
            "Parsed Talend workspace %s: %s jobs, %s components",
            workspace_path,
            len(inventory.jobs),
            len(inventory.components),
        )

        return AgentResponse.completed(
            agent_name=self.name,
            started_at=started_at,
            artifacts=[
                AgentArtifact(
                    name="talend-inventory",
                    artifact_type="inventory",
                    path=workspace_path,
                    payload=payload,
                )
            ],
            metrics={
                "jobs_parsed": len(inventory.jobs),
                "components_parsed": len(inventory.components),
                "contexts_detected": len(inventory.contexts),
                "source_systems_detected": len(inventory.source_systems),
                "target_systems_detected": len(inventory.target_systems),
                "disabled_components_detected": len(inventory.disabled_components),
                "parse_errors": len(inventory.parse_errors),
            },
        )

    def _resolve_workspace_path(self, context: AgentContext) -> str:
        workspace_path = context.metadata.get("workspace_path")
        if workspace_path:
            return str(workspace_path)

        extracted_workspace = context.metadata.get("extracted_workspace")
        if extracted_workspace:
            return str(extracted_workspace)

        if context.upload_path:
            return context.upload_path

        return str(PROJECT_ROOT / "reports" / "workspaces" / context.analysis_id)

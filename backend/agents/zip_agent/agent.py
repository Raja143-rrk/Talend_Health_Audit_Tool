from datetime import datetime
import asyncio

from backend.agents.base import BaseAgent
from backend.shared.models import AgentArtifact, AgentContext, AgentResponse
from backend.agents.zip_agent.extractor import ZipExtractor


class ZipAgent(BaseAgent):
    name = "zip-agent"
    description = "Validates and prepares uploaded Talend ZIP packages."

    def __init__(self, extractor: ZipExtractor | None = None) -> None:
        super().__init__()
        self.extractor = extractor or ZipExtractor()

    async def execute(
        self,
        context: AgentContext,
        started_at: datetime,
    ) -> AgentResponse:
        extraction_result = await asyncio.to_thread(
            self.extractor.extract,
            context.analysis_id,
            context.upload_path,
        )

        self.logger.info(
            "Extracted %s files for analysis %s into %s",
            extraction_result["file_count"],
            context.analysis_id,
            extraction_result["workspace_path"],
        )

        return AgentResponse.completed(
            agent_name=self.name,
            started_at=started_at,
            artifacts=[
                AgentArtifact(
                    name="extracted-workspace",
                    artifact_type="workspace",
                    path=extraction_result["workspace_path"],
                    payload=extraction_result,
                )
            ],
            metrics={
                "archives_processed": 1,
                "files_extracted": extraction_result["file_count"],
            },
        )

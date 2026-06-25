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
        upload_paths = [context.upload_path, *context.additional_upload_paths] if context.upload_path else context.additional_upload_paths
        extraction_result = await asyncio.to_thread(
            self.extractor.extract,
            context.analysis_id,
            upload_paths,
        )

        self.logger.info(
            "Extracted %s files from %s archive(s) for analysis %s into %s",
            extraction_result["file_count"],
            extraction_result.get("archive_count", 1),
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
                "archives_processed": extraction_result.get("archive_count", 1),
                "files_extracted": extraction_result["file_count"],
            },
        )

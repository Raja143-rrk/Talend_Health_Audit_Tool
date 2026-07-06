from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from backend.agents.zip_agent.agent import ZipAgent
from backend.shared.models import AgentResponse, AgentStatus


class TestZipAgent:
    async def test_execute_returns_completed_response(self, agent_context):
        mock_extractor = MagicMock()
        mock_extractor.extract = MagicMock(
            return_value={
                "workspace_path": "/tmp/workspace",
                "file_count": 10,
            }
        )
        agent = ZipAgent(extractor=mock_extractor)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert isinstance(result, AgentResponse)
        assert result.status == AgentStatus.COMPLETED

    async def test_execute_includes_artifact(self, agent_context):
        mock_extractor = MagicMock()
        mock_extractor.extract = MagicMock(
            return_value={
                "workspace_path": "/tmp/workspace",
                "file_count": 10,
            }
        )
        agent = ZipAgent(extractor=mock_extractor)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "extracted-workspace"

    async def test_execute_calls_extractor(self, agent_context):
        mock_extractor = MagicMock()
        mock_extractor.extract = MagicMock(
            return_value={
                "workspace_path": "/tmp/workspace",
                "file_count": 10,
            }
        )
        agent = ZipAgent(extractor=mock_extractor)
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_extractor.extract.assert_called_once()

    async def test_execute_returns_metrics(self, agent_context):
        mock_extractor = MagicMock()
        mock_extractor.extract = MagicMock(
            return_value={
                "workspace_path": "/tmp/workspace",
                "file_count": 10,
            }
        )
        agent = ZipAgent(extractor=mock_extractor)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert "files_extracted" in result.metrics
        assert result.metrics["files_extracted"] == 10
        assert result.metrics["archives_processed"] == 1

    async def test_execute_passes_analysis_id_and_upload_path(self, agent_context):
        mock_extractor = MagicMock()
        mock_extractor.extract = MagicMock(
            return_value={
                "workspace_path": "/tmp/workspace",
                "file_count": 10,
            }
        )
        agent = ZipAgent(extractor=mock_extractor)
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_extractor.extract.assert_called_with(
            agent_context.analysis_id,
            agent_context.upload_path,
        )

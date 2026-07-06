from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from backend.agents.parser_agent.agent import ParserAgent
from backend.shared.models import AgentResponse, AgentStatus


class TestParserAgent:
    async def test_execute_returns_completed_response(self, agent_context):
        mock_parser = MagicMock()
        mock_inventory = MagicMock()
        mock_inventory.model_dump = MagicMock(return_value={"jobs": [], "components": []})
        mock_inventory.jobs = []
        mock_inventory.components = []
        mock_inventory.contexts = []
        mock_inventory.source_systems = []
        mock_inventory.target_systems = []
        mock_inventory.disabled_components = []
        mock_inventory.parse_errors = []
        mock_parser.parse_workspace = MagicMock(return_value=mock_inventory)
        agent = ParserAgent(parser=mock_parser)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert isinstance(result, AgentResponse)
        assert result.status == AgentStatus.COMPLETED

    async def test_execute_includes_artifact(self, agent_context):
        mock_parser = MagicMock()
        mock_inventory = MagicMock()
        mock_inventory.model_dump = MagicMock(return_value={"jobs": [], "components": []})
        mock_inventory.jobs = []
        mock_inventory.components = []
        mock_inventory.contexts = []
        mock_inventory.source_systems = []
        mock_inventory.target_systems = []
        mock_inventory.disabled_components = []
        mock_inventory.parse_errors = []
        mock_parser.parse_workspace = MagicMock(return_value=mock_inventory)
        agent = ParserAgent(parser=mock_parser)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "talend-inventory"
        assert "jobs" in result.artifacts[0].payload

    async def test_execute_calls_parser(self, agent_context):
        mock_parser = MagicMock()
        mock_inventory = MagicMock()
        mock_inventory.model_dump = MagicMock(return_value={"jobs": [], "components": []})
        mock_inventory.jobs = []
        mock_inventory.components = []
        mock_inventory.contexts = []
        mock_inventory.source_systems = []
        mock_inventory.target_systems = []
        mock_inventory.disabled_components = []
        mock_inventory.parse_errors = []
        mock_parser.parse_workspace = MagicMock(return_value=mock_inventory)
        agent = ParserAgent(parser=mock_parser)
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_parser.parse_workspace.assert_called_once()

    async def test_execute_returns_metrics(self, agent_context):
        mock_parser = MagicMock()
        mock_inventory = MagicMock()
        mock_inventory.model_dump = MagicMock(return_value={"jobs": [], "components": []})
        mock_inventory.jobs = []
        mock_inventory.components = []
        mock_inventory.contexts = []
        mock_inventory.source_systems = []
        mock_inventory.target_systems = []
        mock_inventory.disabled_components = []
        mock_inventory.parse_errors = []
        mock_parser.parse_workspace = MagicMock(return_value=mock_inventory)
        agent = ParserAgent(parser=mock_parser)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert "jobs_parsed" in result.metrics
        assert result.metrics["parse_errors"] == 0

    async def test_resolve_workspace_path_from_metadata(self, agent_context):
        mock_parser = MagicMock()
        mock_inventory = MagicMock()
        mock_inventory.model_dump = MagicMock(return_value={"jobs": [], "components": []})
        mock_inventory.jobs = []
        mock_inventory.components = []
        mock_inventory.contexts = []
        mock_inventory.source_systems = []
        mock_inventory.target_systems = []
        mock_inventory.disabled_components = []
        mock_inventory.parse_errors = []
        mock_parser.parse_workspace = MagicMock(return_value=mock_inventory)
        agent = ParserAgent(parser=mock_parser)
        path = agent._resolve_workspace_path(agent_context)
        assert path == "/fake/workspace"

    async def test_resolve_workspace_path_extracted_fallback(self):
        mock_parser = MagicMock()
        mock_inventory = MagicMock()
        mock_inventory.model_dump = MagicMock(return_value={"jobs": [], "components": []})
        mock_inventory.jobs = []
        mock_inventory.components = []
        mock_inventory.contexts = []
        mock_inventory.source_systems = []
        mock_inventory.target_systems = []
        mock_inventory.disabled_components = []
        mock_inventory.parse_errors = []
        mock_parser.parse_workspace = MagicMock(return_value=mock_inventory)
        agent = ParserAgent(parser=mock_parser)
        context = MagicMock()
        context.metadata = {"extracted_workspace": "/extracted/path"}
        context.analysis_id = "test"
        path = agent._resolve_workspace_path(context)
        assert path == "/extracted/path"

    async def test_resolve_workspace_path_upload_path_fallback(self):
        mock_parser = MagicMock()
        mock_inventory = MagicMock()
        mock_inventory.model_dump = MagicMock(return_value={"jobs": [], "components": []})
        mock_inventory.jobs = []
        mock_inventory.components = []
        mock_inventory.contexts = []
        mock_inventory.source_systems = []
        mock_inventory.target_systems = []
        mock_inventory.disabled_components = []
        mock_inventory.parse_errors = []
        mock_parser.parse_workspace = MagicMock(return_value=mock_inventory)
        agent = ParserAgent(parser=mock_parser)
        context = MagicMock()
        context.metadata = {}
        context.upload_path = "/upload/path.zip"
        context.analysis_id = "test"
        path = agent._resolve_workspace_path(context)
        assert path == "/upload/path.zip"

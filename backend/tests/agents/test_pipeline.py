from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.agents.pipeline import UnifiedAgentPipeline
from backend.shared.execution import RetryConfig
from backend.shared.models import AgentResponse, AgentStatus


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.context.analysis_id = "test-analysis-001"
    state.context_for_agent = AsyncMock(return_value=MagicMock())
    state.activate_agent = AsyncMock()
    state.record_agent_output = AsyncMock()
    state.node_statuses = {}
    return state


class TestUnifiedAgentPipeline:
    def test_init_creates_all_agents(self):
        pipeline = UnifiedAgentPipeline()
        assert len(pipeline.agents) == 6
        names = {agent.name for agent in pipeline.agents}
        assert names == {
            "zip-agent",
            "parser-agent",
            "security-agent",
            "performance-agent",
            "recommendation-agent",
            "dashboard-agent",
        }

    def test_get_agent_by_name(self):
        pipeline = UnifiedAgentPipeline()
        agent = pipeline.get_agent("security-agent")
        assert agent.name == "security-agent"

    def test_get_agent_unknown(self):
        pipeline = UnifiedAgentPipeline()
        with pytest.raises(KeyError):
            pipeline.get_agent("unknown-agent")

    def test_graph_edges(self):
        pipeline = UnifiedAgentPipeline()
        edges = pipeline.graph_edges()
        assert len(edges) == 8
        assert edges[0] == ("START", "zip-agent")
        assert edges[-1] == ("dashboard-agent", "END")

    def test_apply_retry_config(self):
        pipeline = UnifiedAgentPipeline()
        config = RetryConfig(max_attempts=3, delay_seconds=1)
        pipeline.apply_retry_config(config)
        for agent in pipeline.agents:
            assert agent.retry_config.max_attempts == 3

    async def test_run_agent_success(self, mock_state):
        pipeline = UnifiedAgentPipeline()
        agent = pipeline.get_agent("parser-agent")
        result = await pipeline.run_agent(mock_state, agent)
        assert result.status in (AgentStatus.COMPLETED, AgentStatus.FAILED)
        mock_state.activate_agent.assert_called_once_with(agent.name)
        mock_state.record_agent_output.assert_called_once()

    async def test_run_agent_failure(self, mock_state):
        pipeline = UnifiedAgentPipeline()

        class FailingAgent:
            name = "failing-agent"
            retry_config = RetryConfig(max_attempts=1)

            async def run(self, context):
                msg = "Intentional failure"
                raise RuntimeError(msg)

        result = await pipeline.run_agent(mock_state, FailingAgent())
        assert result.status == AgentStatus.FAILED
        assert len(result.errors) > 0
        mock_state.record_agent_output.assert_called_once_with(result)

    def test_failed_required_nodes_none(self, mock_state):
        pipeline = UnifiedAgentPipeline()
        mock_state.node_statuses = {
            "zip-agent": AgentStatus.COMPLETED,
            "parser-agent": AgentStatus.COMPLETED,
        }
        failed = list(pipeline.failed_required_nodes(mock_state))
        assert failed == []

    def test_failed_required_nodes_detected(self, mock_state):
        pipeline = UnifiedAgentPipeline()
        mock_state.node_statuses = {
            "zip-agent": AgentStatus.FAILED,
            "parser-agent": AgentStatus.COMPLETED,
        }
        failed = list(pipeline.failed_required_nodes(mock_state))
        assert failed == ["zip-agent"]

    async def test_merge_agent_output(self, mock_state):
        pipeline = UnifiedAgentPipeline()
        result = AgentResponse.completed(
            agent_name="test-agent",
            started_at=MagicMock(),
        )
        await pipeline.merge_agent_output(mock_state, result)
        mock_state.record_agent_output.assert_called_once_with(result)

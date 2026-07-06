from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.base import BaseAgent
from backend.shared.execution import RetryConfig
from backend.shared.models import AgentContext, AgentResponse, AgentStatus


class _ConcreteAgent(BaseAgent):
    name = "test-agent"
    description = "Test agent for unit tests"

    def __init__(self, execute_result: AgentResponse | None = None, raise_error: bool = False):
        super().__init__()
        self._execute_result = execute_result or AgentResponse.completed(
            agent_name=self.name,
            started_at=datetime.now(timezone.utc),
        )
        self._raise_error = raise_error

    async def execute(self, context: AgentContext, started_at: datetime) -> AgentResponse:
        if self._raise_error:
            msg = "Intentional failure"
            raise RuntimeError(msg)
        return self._execute_result


class TestBaseAgent:
    async def test_run_returns_response(self, agent_context):
        agent = _ConcreteAgent()
        result = await agent.run(agent_context)
        assert isinstance(result, AgentResponse)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_name == "test-agent"

    async def test_run_sets_status(self, agent_context):
        agent = _ConcreteAgent()
        assert agent.status == AgentStatus.PENDING
        await agent.run(agent_context)
        assert agent.status == AgentStatus.COMPLETED

    async def test_run_handles_failure(self, agent_context):
        agent = _ConcreteAgent(raise_error=True)
        result = await agent.run(agent_context)
        assert result.status == AgentStatus.FAILED
        assert len(result.errors) > 0

    async def test_run_stores_last_response(self, agent_context):
        agent = _ConcreteAgent()
        result = await agent.run(agent_context)
        assert agent.last_response is result

    async def test_run_sets_duration_ms(self, agent_context):
        agent = _ConcreteAgent()
        result = await agent.run(agent_context)
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    async def test_run_with_retry_config(self, agent_context):
        agent = _ConcreteAgent(raise_error=True)
        agent.retry_config = RetryConfig(max_attempts=3, delay_seconds=0)
        result = await agent.run(agent_context)
        assert result.status == AgentStatus.FAILED
        assert result.attempts == 3

    async def test_run_successful_on_retry(self, agent_context):
        call_count = 0

        class _RetryAgent(BaseAgent):
            name = "retry-agent"

            async def execute(self, context, started_at):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    msg = "Temporary failure"
                    raise RuntimeError(msg)
                return AgentResponse.completed(
                    agent_name=self.name,
                    started_at=started_at,
                )

        agent = _RetryAgent()
        agent.retry_config = RetryConfig(max_attempts=3, delay_seconds=0)
        result = await agent.run(agent_context)
        assert result.status == AgentStatus.COMPLETED
        assert result.attempts == 2

    async def test_retry_attempts_propagation(self, agent_context):
        agent = _ConcreteAgent(raise_error=True)
        agent.retry_config = RetryConfig(max_attempts=3, delay_seconds=0)
        result = await agent.run(agent_context)
        assert result.attempts == 3

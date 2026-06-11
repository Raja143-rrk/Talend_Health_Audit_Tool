from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING
from typing import Protocol

from backend.agents.dashboard_agent import DashboardAgent
from backend.agents.parser_agent import ParserAgent
from backend.agents.performance_agent import PerformanceAgent
from backend.agents.recommendation_agent import RecommendationAgent
from backend.agents.security_agent import SecurityAgent
from backend.agents.zip_agent import ZipAgent
from backend.core.logging import get_logger
from backend.shared.execution import RetryConfig
from backend.shared.models import AgentContext, AgentResponse, AgentStatus
from backend.shared.utils import utc_now

if TYPE_CHECKING:
    from backend.langgraph.state import WorkflowState

logger = get_logger(__name__)


class PipelineAgent(Protocol):
    name: str
    retry_config: RetryConfig

    async def run(self, context: AgentContext) -> AgentResponse:
        ...


class UnifiedAgentPipeline:
    """Single execution surface for all Talend Health Analyzer agents."""

    def __init__(self, retry_config: RetryConfig | None = None) -> None:
        self.zip_agent = ZipAgent()
        self.parser_agent = ParserAgent()
        self.security_agent = SecurityAgent()
        self.performance_agent = PerformanceAgent()
        self.recommendation_agent = RecommendationAgent()
        self.dashboard_agent = DashboardAgent()
        self.agents = (
            self.zip_agent,
            self.parser_agent,
            self.security_agent,
            self.performance_agent,
            self.recommendation_agent,
            self.dashboard_agent,
        )
        self._agents_by_name = {agent.name: agent for agent in self.agents}
        if retry_config is not None:
            self.apply_retry_config(retry_config)

    def apply_retry_config(self, retry_config: RetryConfig) -> None:
        for agent in self.agents:
            agent.retry_config = retry_config

    async def run_agent(self, state: WorkflowState, agent: PipelineAgent) -> AgentResponse:
        await state.activate_agent(agent.name)

        logger.info(
            "Pipeline dispatching %s for analysis %s",
            agent.name,
            state.context.analysis_id,
        )

        try:
            result = await agent.run(await state.context_for_agent(agent.name))
        except Exception as exc:
            logger.exception(
                "Pipeline caught unhandled error from %s for analysis %s",
                agent.name,
                state.context.analysis_id,
            )
            result = AgentResponse.failed(
                agent_name=agent.name,
                started_at=utc_now(),
                error=exc,
                attempts=agent.retry_config.max_attempts,
            )

        await state.record_agent_output(result)
        return result

    def get_agent(self, agent_name: str) -> PipelineAgent:
        return self._agents_by_name[agent_name]

    def graph_edges(self) -> list[tuple[str, str]]:
        return [
            ("START", self.zip_agent.name),
            (self.zip_agent.name, self.parser_agent.name),
            (self.parser_agent.name, self.security_agent.name),
            (self.parser_agent.name, self.performance_agent.name),
            (self.security_agent.name, self.recommendation_agent.name),
            (self.performance_agent.name, self.recommendation_agent.name),
            (self.recommendation_agent.name, self.dashboard_agent.name),
            (self.dashboard_agent.name, "END"),
        ]

    def failed_required_nodes(self, state: WorkflowState) -> Iterable[str]:
        required_nodes = {self.zip_agent.name, self.parser_agent.name}
        return (
            node_name
            for node_name, status in state.node_statuses.items()
            if node_name in required_nodes and status == AgentStatus.FAILED
        )

    async def merge_agent_output(
        self,
        state: WorkflowState,
        result: AgentResponse,
    ) -> None:
        await state.record_agent_output(result)

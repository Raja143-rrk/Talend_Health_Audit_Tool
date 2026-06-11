import asyncio
import inspect
from collections.abc import Callable, Awaitable
from collections.abc import Iterable
from typing import Any

from backend.agents.pipeline import UnifiedAgentPipeline
from backend.core.logging import get_logger
from backend.langgraph.state import WorkflowState, WorkflowStatus
from backend.langgraph.visualization import workflow_mermaid
from backend.shared.execution import RetryConfig
from backend.shared.models import AgentContext, AgentResponse, AgentStatus
from backend.shared.utils import utc_now

try:
    from langgraph.graph import END, START, StateGraph
except ModuleNotFoundError:  # pragma: no cover - dependency is optional at import time.
    END = "__end__"
    START = "__start__"
    StateGraph = None

logger = get_logger(__name__)


ZIP_NODE = "zip"
PARSER_NODE = "parser"
QUALITY_NODE = "security_performance_parallel"
RECOMMENDATION_NODE = "recommendation"
DASHBOARD_NODE = "dashboard"


class AgentWorkflow:
    """Async LangGraph orchestration for the Talend analyzer agent graph."""

    def __init__(
        self,
        on_state_change: Callable[[WorkflowState], None | Awaitable[None]] | None = None,
        agent_retry_config: RetryConfig | None = None,
    ) -> None:
        self.on_state_change = on_state_change
        self.pipeline = UnifiedAgentPipeline(retry_config=agent_retry_config)
        self._graph = self._compile_graph()

    async def run(self, context: AgentContext) -> WorkflowState:
        state = WorkflowState(
            context=context,
            status=WorkflowStatus.RUNNING,
            started_at=utc_now(),
        )
        await self._notify(state)
        final_state = await self._invoke_graph(state)
        await self._notify(final_state)
        return final_state

    async def _zip_node(self, state: WorkflowState) -> WorkflowState:
        zip_result = await self._run_agent(state, self.pipeline.zip_agent)
        if self._failed(zip_result):
            await state.mark_skipped(
                self.pipeline.parser_agent.name,
                self.pipeline.security_agent.name,
                self.pipeline.performance_agent.name,
                self.pipeline.recommendation_agent.name,
                self.pipeline.dashboard_agent.name,
            )
            return await self._finish(state, WorkflowStatus.FAILED)
        return state

    async def _parser_node(self, state: WorkflowState) -> WorkflowState:
        parser_result = await self._run_agent(state, self.pipeline.parser_agent)
        if self._failed(parser_result):
            await state.mark_skipped(
                self.pipeline.security_agent.name,
                self.pipeline.performance_agent.name,
                self.pipeline.recommendation_agent.name,
                self.pipeline.dashboard_agent.name,
            )
            return await self._finish(state, WorkflowStatus.FAILED)
        return state

    async def _quality_parallel_node(self, state: WorkflowState) -> WorkflowState:
        security_result, performance_result = await asyncio.gather(
            self._run_agent(state, self.pipeline.security_agent),
            self._run_agent(state, self.pipeline.performance_agent),
        )

        if self._failed(security_result) and self._failed(performance_result):
            await state.mark_skipped(
                self.pipeline.recommendation_agent.name,
                self.pipeline.dashboard_agent.name,
            )
            return await self._finish(state, WorkflowStatus.FAILED)
        return state

    async def _recommendation_node(self, state: WorkflowState) -> WorkflowState:
        recommendation_result = await self._run_agent(
            state,
            self.pipeline.recommendation_agent,
        )
        if self._failed(recommendation_result):
            logger.warning(
                "Recommendation agent failed for analysis %s; dashboard will use partial outputs",
                state.context.analysis_id,
            )
        return state

    async def _dashboard_node(self, state: WorkflowState) -> WorkflowState:
        dashboard_result = await self._run_agent(state, self.pipeline.dashboard_agent)
        if self._failed(dashboard_result):
            return await self._finish(state, WorkflowStatus.PARTIAL)

        state.current_agent = None
        final_status = (
            WorkflowStatus.PARTIAL
            if any(self._failed(result) for result in state.results)
            else WorkflowStatus.COMPLETED
        )
        return await self._finish(state, final_status)

    def _compile_graph(self) -> Any:
        if StateGraph is None:
            logger.warning(
                "langgraph is not installed; AgentWorkflow will use the internal async runner"
            )
            return None

        graph = StateGraph(WorkflowState)
        graph.add_node(ZIP_NODE, self._zip_node)
        graph.add_node(PARSER_NODE, self._parser_node)
        graph.add_node(QUALITY_NODE, self._quality_parallel_node)
        graph.add_node(RECOMMENDATION_NODE, self._recommendation_node)
        graph.add_node(DASHBOARD_NODE, self._dashboard_node)

        graph.add_edge(START, ZIP_NODE)
        graph.add_conditional_edges(
            ZIP_NODE,
            self._route_after_required_node,
            {
                PARSER_NODE: PARSER_NODE,
                END: END,
            },
        )
        graph.add_conditional_edges(
            PARSER_NODE,
            self._route_after_required_node,
            {
                QUALITY_NODE: QUALITY_NODE,
                END: END,
            },
        )
        graph.add_conditional_edges(
            QUALITY_NODE,
            self._route_after_quality_node,
            {
                RECOMMENDATION_NODE: RECOMMENDATION_NODE,
                END: END,
            },
        )
        graph.add_edge(RECOMMENDATION_NODE, DASHBOARD_NODE)
        graph.add_edge(DASHBOARD_NODE, END)
        return graph.compile()

    async def _invoke_graph(self, state: WorkflowState) -> WorkflowState:
        if self._graph is not None:
            result = await self._graph.ainvoke(state)
            return self._coerce_state(result)

        state = await self._zip_node(state)
        if state.status == WorkflowStatus.FAILED:
            return state
        state = await self._parser_node(state)
        if state.status == WorkflowStatus.FAILED:
            return state
        state = await self._quality_parallel_node(state)
        if state.status == WorkflowStatus.FAILED:
            return state
        state = await self._recommendation_node(state)
        return await self._dashboard_node(state)

    def _coerce_state(self, state: WorkflowState | dict[str, Any]) -> WorkflowState:
        if isinstance(state, WorkflowState):
            return state
        return WorkflowState.model_validate(state)

    def _route_after_required_node(self, state: WorkflowState) -> str:
        if state.status == WorkflowStatus.FAILED:
            return END
        if (
            state.execution_order
            and state.execution_order[-1] == self.pipeline.zip_agent.name
        ):
            return PARSER_NODE
        return QUALITY_NODE

    def _route_after_quality_node(self, state: WorkflowState) -> str:
        if state.status == WorkflowStatus.FAILED:
            return END
        return RECOMMENDATION_NODE

    async def _run_agent(self, state: WorkflowState, agent) -> AgentResponse:
        await state.set_progress(self._progress_from_state(state))
        await self._notify(state)
        result = await self.pipeline.run_agent(state, agent)
        await state.set_progress(self._progress_from_state(state))
        await self._notify(state)
        return result

    async def _notify(self, state: WorkflowState) -> None:
        if self.on_state_change is None:
            return

        result = self.on_state_change(state)
        if inspect.isawaitable(result):
            await result

    async def _finish(self, state: WorkflowState, status: WorkflowStatus) -> WorkflowState:
        await state.finish(status=status, completed_at=utc_now())
        return state

    def _progress_from_state(self, state: WorkflowState) -> int:
        total_nodes = 6
        if not state.execution_order:
            return 5
        return min(95, int((len(state.execution_order) / total_nodes) * 100))

    def _failed(self, result: AgentResponse) -> bool:
        return result.status == AgentStatus.FAILED

    def graph_mermaid(self) -> str:
        return workflow_mermaid()

    def graph_edges(self) -> list[tuple[str, str]]:
        return self.pipeline.graph_edges()

    def failed_required_nodes(self, state: WorkflowState) -> Iterable[str]:
        return self.pipeline.failed_required_nodes(state)

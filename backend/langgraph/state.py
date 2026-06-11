import asyncio
from copy import deepcopy
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr

from backend.shared.models import (
    AgentArtifact,
    AgentContext,
    AgentFinding,
    AgentRecommendation,
    AgentResponse,
    AgentStatus,
)


class WorkflowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class WorkflowState(BaseModel):
    context: AgentContext
    status: WorkflowStatus = WorkflowStatus.PENDING
    results: list[AgentResponse] = Field(default_factory=list)
    agent_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    agent_inputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    shared_data: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, list[AgentArtifact]] = Field(default_factory=dict)
    findings: dict[str, list[AgentFinding]] = Field(default_factory=dict)
    recommendations: dict[str, list[AgentRecommendation]] = Field(default_factory=dict)
    current_agent: str | None = None
    active_agents: list[str] = Field(default_factory=list)
    node_statuses: dict[str, AgentStatus] = Field(default_factory=dict)
    execution_order: list[str] = Field(default_factory=list)
    skipped_nodes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    progress: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)

    async def activate_agent(self, agent_name: str) -> None:
        async with self._lock:
            self.current_agent = agent_name
            if agent_name not in self.active_agents:
                self.active_agents.append(agent_name)
            self.node_statuses[agent_name] = AgentStatus.RUNNING

    async def record_result(self, result: AgentResponse) -> None:
        async with self._lock:
            self._record_result_unlocked(result)

    async def record_agent_output(self, result: AgentResponse) -> None:
        async with self._lock:
            self._record_result_unlocked(result)
            self._merge_agent_output_unlocked(result)

    async def set_shared_data(self, key: str, value: Any) -> None:
        async with self._lock:
            self.shared_data[key] = value
            self.context.metadata[key] = value

    async def update_shared_data(self, values: dict[str, Any]) -> None:
        async with self._lock:
            self.shared_data.update(values)
            self.context.metadata.update(values)

    async def pass_data_to_agent(
        self,
        target_agent: str,
        key: str,
        value: Any,
        source_agent: str | None = None,
    ) -> None:
        async with self._lock:
            self._set_agent_input_unlocked(target_agent, key, value, source_agent)

    async def pass_data_to_agents(
        self,
        target_agents: list[str],
        values: dict[str, Any],
        source_agent: str | None = None,
    ) -> None:
        async with self._lock:
            for target_agent in target_agents:
                for key, value in values.items():
                    self._set_agent_input_unlocked(
                        target_agent,
                        key,
                        value,
                        source_agent,
                    )

    async def context_for_agent(self, agent_name: str) -> AgentContext:
        async with self._lock:
            metadata = {
                **deepcopy(self.context.metadata),
                **deepcopy(self.shared_data),
                **deepcopy(self.agent_inputs.get(agent_name, {})),
                "agent_outputs": deepcopy(self.agent_outputs),
                "workflow_context": {
                    "status": self.status.value,
                    "current_agent": self.current_agent,
                    "active_agents": list(self.active_agents),
                    "node_statuses": {
                        name: status.value
                        for name, status in self.node_statuses.items()
                    },
                    "execution_order": list(self.execution_order),
                    "skipped_nodes": list(self.skipped_nodes),
                    "progress": self.progress,
                },
            }
            return self.context.model_copy(update={"metadata": metadata}, deep=True)

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return self.model_dump(mode="json")

    async def set_progress(self, progress: int) -> None:
        async with self._lock:
            self.progress = max(0, min(100, progress))

    async def mark_skipped(self, *node_names: str) -> None:
        async with self._lock:
            for node_name in node_names:
                if node_name not in self.skipped_nodes:
                    self.skipped_nodes.append(node_name)

    async def finish(self, status: WorkflowStatus, completed_at: datetime) -> None:
        async with self._lock:
            self.status = status
            self.current_agent = None
            self.active_agents = []
            self.completed_at = completed_at
            self.progress = 100

    def get_context_value(self, key: str, default: Any = None) -> Any:
        if key in self.shared_data:
            return self.shared_data[key]
        return self.context.metadata.get(key, default)

    def get_agent_output(self, agent_name: str, default: Any = None) -> Any:
        return self.agent_outputs.get(agent_name, default)

    def get_agent_input(
        self,
        agent_name: str,
        key: str,
        default: Any = None,
    ) -> Any:
        return self.agent_inputs.get(agent_name, {}).get(key, default)

    def _record_result_unlocked(self, result: AgentResponse) -> None:
        if result.agent_name in self.active_agents:
            self.active_agents.remove(result.agent_name)
        self.current_agent = self.active_agents[-1] if self.active_agents else None
        self.results.append(result)
        self.node_statuses[result.agent_name] = result.status
        self.execution_order.append(result.agent_name)
        self.errors.extend(
            f"{result.agent_name}: {error}" for error in result.errors
        )

    def _merge_agent_output_unlocked(self, result: AgentResponse) -> None:
        serialized = result.model_dump(mode="json")
        self.agent_outputs[result.agent_name] = serialized
        self.context.metadata.setdefault("agent_outputs", {})[result.agent_name] = serialized
        self.artifacts[result.agent_name] = result.artifacts
        self.findings[result.agent_name] = result.findings
        self.recommendations[result.agent_name] = result.recommendations

        if result.agent_name == "parser-agent" and result.artifacts:
            inventory = result.artifacts[0].payload
            self._set_shared_value_unlocked("talend_inventory", inventory)
            for target_agent in (
                "security-agent",
                "performance-agent",
                "recommendation-agent",
                "dashboard-agent",
            ):
                self._set_agent_input_unlocked(
                    target_agent,
                    "talend_inventory",
                    inventory,
                    result.agent_name,
                )

        if result.agent_name == "security-agent":
            security_findings = [
                finding.model_dump(mode="json") for finding in result.findings
            ]
            self._set_shared_value_unlocked("security_findings", security_findings)
            security_recommendations = [
                recommendation.model_dump(mode="json")
                for recommendation in result.recommendations
            ]
            self._extend_shared_list_unlocked(
                "existing_recommendations",
                security_recommendations,
            )
            for target_agent in ("recommendation-agent", "dashboard-agent"):
                self._set_agent_input_unlocked(
                    target_agent,
                    "security_findings",
                    security_findings,
                    result.agent_name,
                )
                self._extend_agent_input_list_unlocked(
                    target_agent,
                    "existing_recommendations",
                    security_recommendations,
                    result.agent_name,
                )

        if result.agent_name == "performance-agent":
            performance_findings = [
                finding.model_dump(mode="json") for finding in result.findings
            ]
            self._set_shared_value_unlocked(
                "performance_findings",
                performance_findings,
            )
            performance_recommendations = [
                recommendation.model_dump(mode="json")
                for recommendation in result.recommendations
            ]
            self._extend_shared_list_unlocked(
                "existing_recommendations",
                performance_recommendations,
            )
            for target_agent in ("recommendation-agent", "dashboard-agent"):
                self._set_agent_input_unlocked(
                    target_agent,
                    "performance_findings",
                    performance_findings,
                    result.agent_name,
                )
                self._extend_agent_input_list_unlocked(
                    target_agent,
                    "existing_recommendations",
                    performance_recommendations,
                    result.agent_name,
                )

        if result.agent_name == "recommendation-agent":
            recommendations = [
                recommendation.model_dump(mode="json")
                for recommendation in result.recommendations
            ]
            self._set_shared_value_unlocked("recommendations", recommendations)
            self._set_agent_input_unlocked(
                "dashboard-agent",
                "recommendations",
                recommendations,
                result.agent_name,
            )

        if result.agent_name == "zip-agent" and result.artifacts:
            workspace_path = result.artifacts[0].payload.get("workspace_path")
            if workspace_path:
                self._set_shared_value_unlocked("workspace_path", workspace_path)
                self._set_shared_value_unlocked("extracted_workspace", workspace_path)
                self._set_agent_input_unlocked(
                    "parser-agent",
                    "workspace_path",
                    workspace_path,
                    result.agent_name,
                )
                self._set_agent_input_unlocked(
                    "parser-agent",
                    "extracted_workspace",
                    workspace_path,
                    result.agent_name,
                )

    def _set_shared_value_unlocked(self, key: str, value: Any) -> None:
        self.shared_data[key] = value
        self.context.metadata[key] = value

    def _extend_shared_list_unlocked(self, key: str, values: list[Any]) -> None:
        current = self.shared_data.setdefault(key, [])
        if not isinstance(current, list):
            current = []
            self.shared_data[key] = current
        current.extend(values)
        self.context.metadata[key] = current

    def _set_agent_input_unlocked(
        self,
        target_agent: str,
        key: str,
        value: Any,
        source_agent: str | None = None,
    ) -> None:
        agent_input = self.agent_inputs.setdefault(target_agent, {})
        agent_input[key] = value
        if source_agent:
            handoffs = agent_input.setdefault("_handoffs", [])
            handoffs.append({"source_agent": source_agent, "key": key})

    def _extend_agent_input_list_unlocked(
        self,
        target_agent: str,
        key: str,
        values: list[Any],
        source_agent: str | None = None,
    ) -> None:
        agent_input = self.agent_inputs.setdefault(target_agent, {})
        current = agent_input.setdefault(key, [])
        if not isinstance(current, list):
            current = []
            agent_input[key] = current
        current.extend(values)
        if source_agent:
            handoffs = agent_input.setdefault("_handoffs", [])
            handoffs.append({"source_agent": source_agent, "key": key})

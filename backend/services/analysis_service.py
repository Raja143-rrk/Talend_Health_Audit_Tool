import json
import uuid
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from threading import RLock
from typing import Any

from pydantic import BaseModel, Field

from backend.core.exceptions import AppError
from backend.core.logging import get_logger
from backend.langgraph import AgentWorkflow, WorkflowState
from backend.shared.execution import RetryConfig
from backend.shared.models import AgentContext

logger = get_logger(__name__)


class AnalysisRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class AnalysisRecord(BaseModel):
    task_id: str
    analysis_id: str
    upload_path: str
    original_filename: str
    status: AnalysisRunStatus = AnalysisRunStatus.QUEUED
    current_agent: str | None = None
    active_agents: list[str] = Field(default_factory=list)
    progress: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    workflow_state: dict[str, Any] | None = None
    dashboard: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    logs: list[dict[str, Any]] = Field(default_factory=list)


PERSIST_DIR = Path(__file__).resolve().parents[2] / "reports"
PERSIST_FILE = PERSIST_DIR / "analysis_records.json"


class AnalysisService:
    def __init__(self) -> None:
        self._records: dict[str, AnalysisRecord] = {}
        self._task_index: dict[str, str] = {}
        self._lock = RLock()
        self._load()

    def _persist(self) -> None:
        try:
            PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                aid: record.model_dump(mode="json")
                for aid, record in self._records.items()
            }
            PERSIST_FILE.write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")
        except Exception:
            logger.exception("Failed to persist analysis records")

    def _load(self) -> None:
        try:
            if not PERSIST_FILE.is_file():
                return
            data = json.loads(PERSIST_FILE.read_text(encoding="utf-8"))
            for analysis_id, record_data in data.items():
                record = AnalysisRecord(**record_data)
                self._records[analysis_id] = record
                self._task_index[record.task_id] = analysis_id
            if self._records:
                logger.info("Loaded %s analysis record(s) from disk", len(self._records))
        except Exception:
            logger.exception("Failed to load analysis records from disk, starting fresh")

    def create_analysis(self, upload_path: str, original_filename: str) -> AnalysisRecord:
        task_id = f"task_{uuid.uuid4().hex}"
        analysis_id = f"analysis_{uuid.uuid4().hex}"
        record = AnalysisRecord(
            task_id=task_id,
            analysis_id=analysis_id,
            upload_path=upload_path,
            original_filename=original_filename,
        )
        with self._lock:
            self._records[analysis_id] = record
            self._task_index[task_id] = analysis_id
            self._append_log(record, "info", "Analysis task queued")
            self._persist()
        logger.info("Created analysis %s task %s for %s", analysis_id, task_id, original_filename)
        return record

    async def run_analysis(self, analysis_id: str) -> None:
        record = self.get_record(analysis_id)
        self._mark_running(record)

        try:
            async def on_state_change(state: WorkflowState) -> None:
                self._update_running_state(record, await state.snapshot())

            workflow = AgentWorkflow(
                on_state_change=on_state_change,
                agent_retry_config=RetryConfig(
                    max_attempts=3,
                    delay_seconds=0.5,
                    backoff_multiplier=2,
                ),
            )
            context = AgentContext(
                analysis_id=record.analysis_id,
                upload_path=record.upload_path,
                metadata={"original_filename": record.original_filename},
            )
            state = await workflow.run(context)
            self._store_workflow_result(record, state)
        except Exception as exc:
            logger.exception("Analysis workflow failed for %s", analysis_id)
            with self._lock:
                record.status = AnalysisRunStatus.FAILED
                record.errors.append(str(exc))
                self._append_log(record, "error", f"Analysis workflow failed: {exc}")
                record.completed_at = datetime.now(timezone.utc)
                record.updated_at = record.completed_at
                self._persist()

    def get_status_payload(self, analysis_id: str) -> dict[str, Any]:
        record = self.get_record(analysis_id)
        with self._lock:
            workflow_state = record.workflow_state or {}
            return {
                "analysis_id": record.analysis_id,
                "task_id": record.task_id,
                "status": record.status.value,
                "current_agent": record.current_agent,
                "active_agents": list(record.active_agents),
                "progress": record.progress,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
                "completed_at": record.completed_at,
                "node_statuses": workflow_state.get("node_statuses", {}),
                "execution_order": workflow_state.get("execution_order", []),
                "skipped_nodes": workflow_state.get("skipped_nodes", []),
                "errors": list(dict.fromkeys([*record.errors, *workflow_state.get("errors", [])])),
                "logs": list(record.logs),
            }

    def get_task_status_payload(self, task_id: str) -> dict[str, Any]:
        record = self.get_record_by_task(task_id)
        with self._lock:
            return {
                "task_id": record.task_id,
                "analysis_id": record.analysis_id,
                "status": record.status.value,
                "progress": record.progress,
                "current_agent": record.current_agent,
                "active_agents": list(record.active_agents),
                "created_at": record.created_at,
                "started_at": record.started_at,
                "updated_at": record.updated_at,
                "completed_at": record.completed_at,
                "logs": list(record.logs),
                "errors": list(record.errors),
                "status_url": f"/api/v1/tasks/{record.task_id}/status",
                "dashboard_url": f"/api/v1/dashboard?analysis_id={record.analysis_id}",
            }

    def get_dashboard_payload(self, analysis_id: str) -> dict[str, Any]:
        record = self.get_record(analysis_id)
        with self._lock:
            if record.dashboard is None:
                raise AppError(
                    message="Dashboard is not available until analysis completes.",
                    status_code=202,
                )

            return {
                "analysis_id": record.analysis_id,
                "status": record.status.value,
                "dashboard": record.dashboard,
                "workflow": record.workflow_state or {},
            }

    def get_execution_payload(self, analysis_id: str) -> dict[str, Any]:
        record = self.get_record(analysis_id)
        with self._lock:
            return {
                "analysis_id": record.analysis_id,
                "task_id": record.task_id,
                "status": record.status.value,
                "dashboard": record.dashboard,
                "workflow": record.workflow_state or {},
                "errors": list(record.errors),
            }

    def get_record(self, analysis_id: str) -> AnalysisRecord:
        with self._lock:
            record = self._records.get(analysis_id)
        if record is None:
            raise AppError(message=f"Analysis not found: {analysis_id}", status_code=404)
        return record

    def get_record_by_task(self, task_id: str) -> AnalysisRecord:
        with self._lock:
            analysis_id = self._task_index.get(task_id)
        if analysis_id is None:
            raise AppError(message=f"Analysis task not found: {task_id}", status_code=404)
        return self.get_record(analysis_id)

    def get_latest_record(self) -> AnalysisRecord | None:
        with self._lock:
            if not self._records:
                return None
            return max(self._records.values(), key=lambda record: record.updated_at)

    def _mark_running(self, record: AnalysisRecord) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            record.status = AnalysisRunStatus.RUNNING
            record.progress = 5
            record.started_at = record.started_at or now
            record.updated_at = now
            self._append_log(record, "info", "Analysis task started")
            self._persist()

    def _store_workflow_result(self, record: AnalysisRecord, state: WorkflowState) -> None:
        now = datetime.now(timezone.utc)
        workflow_state = state.model_dump(mode="json")
        with self._lock:
            record.workflow_state = workflow_state
            record.current_agent = state.current_agent
            record.active_agents = list(state.active_agents)
            record.errors = list(state.errors)
            record.dashboard = self._extract_dashboard(state)
            record.status = self._map_workflow_status(str(state.status))
            record.progress = 100 if record.status in {
                AnalysisRunStatus.COMPLETED,
                AnalysisRunStatus.PARTIAL,
                AnalysisRunStatus.FAILED,
            } else self._progress_from_state(state)
            record.completed_at = now
            record.updated_at = now
            self._append_log(record, "info", f"Analysis task finished with status {record.status.value}")
            self._persist()
            logger.info("Analysis %s finished with status %s", record.analysis_id, record.status)

    def _update_running_state(
        self,
        record: AnalysisRecord,
        workflow_state: dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            record.status = AnalysisRunStatus.RUNNING
            record.current_agent = workflow_state.get("current_agent")
            record.active_agents = workflow_state.get("active_agents", [])
            record.progress = workflow_state.get("progress", 0)
            record.workflow_state = workflow_state
            record.errors = workflow_state.get("errors", [])
            record.updated_at = now
            self._sync_workflow_logs(record, workflow_state)
            self._persist()

    def _extract_dashboard(self, state: WorkflowState) -> dict[str, Any] | None:
        for result in reversed(state.results):
            if result.agent_name == "dashboard-agent" and result.artifacts:
                return result.artifacts[0].payload
        return None

    def _map_workflow_status(self, workflow_status: str) -> AnalysisRunStatus:
        normalized = workflow_status.split(".")[-1].lower()
        if normalized == "completed":
            return AnalysisRunStatus.COMPLETED
        if normalized == "partial":
            return AnalysisRunStatus.PARTIAL
        if normalized == "failed":
            return AnalysisRunStatus.FAILED
        return AnalysisRunStatus.RUNNING

    def _progress_from_state(self, state: WorkflowState) -> int:
        total_nodes = 6
        return min(95, int((len(state.execution_order) / total_nodes) * 100))

    def _sync_workflow_logs(
        self,
        record: AnalysisRecord,
        workflow_state: dict[str, Any],
    ) -> None:
        existing_messages = {
            (str(log.get("agent")), str(log.get("message")))
            for log in record.logs
        }

        for agent_name in workflow_state.get("active_agents", []):
            message = f"{agent_name} running"
            if (agent_name, message) not in existing_messages:
                self._append_log(record, "info", message, agent=agent_name)

        node_statuses = workflow_state.get("node_statuses", {})
        for agent_name in workflow_state.get("execution_order", []):
            status_value = str(node_statuses.get(agent_name, "completed"))
            message = f"{agent_name} {status_value}"
            level = "error" if status_value.endswith("failed") else "info"
            if (agent_name, message) not in existing_messages:
                self._append_log(record, level, message, agent=agent_name)

        for error in workflow_state.get("errors", []):
            message = str(error)
            if ("None", message) not in existing_messages:
                self._append_log(record, "error", message)

    def _append_log(
        self,
        record: AnalysisRecord,
        level: str,
        message: str,
        agent: str | None = None,
    ) -> None:
        record.logs.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "level": level,
                "message": message,
                "agent": agent,
            }
        )


analysis_service = AnalysisService()

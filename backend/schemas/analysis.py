from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalysisCreateResponse(BaseModel):
    task_id: str
    analysis_id: str
    status: str
    message: str
    upload: dict[str, Any]
    task_status_url: str
    status_url: str
    dashboard_url: str


class AnalysisTaskLog(BaseModel):
    timestamp: datetime
    level: str
    message: str
    agent: str | None = None


class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    task_id: str | None = None
    status: str
    current_agent: str | None = None
    active_agents: list[str] = Field(default_factory=list)
    progress: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    node_statuses: dict[str, str] = Field(default_factory=dict)
    execution_order: list[str] = Field(default_factory=list)
    skipped_nodes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    logs: list[AnalysisTaskLog] = Field(default_factory=list)


class AnalysisTaskStatusResponse(BaseModel):
    task_id: str
    analysis_id: str
    status: str
    progress: int
    current_agent: str | None = None
    active_agents: list[str] = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None = None
    updated_at: datetime
    completed_at: datetime | None = None
    logs: list[AnalysisTaskLog] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    status_url: str
    dashboard_url: str


class AnalysisDashboardResponse(BaseModel):
    analysis_id: str
    status: str
    dashboard: dict[str, Any]
    workflow: dict[str, Any]


class AnalysisExecutionResponse(BaseModel):
    task_id: str
    analysis_id: str
    status: str
    message: str
    upload: dict[str, Any]
    dashboard: dict[str, Any] | None = None
    workflow: dict[str, Any]
    task_status_url: str
    status_url: str
    dashboard_url: str

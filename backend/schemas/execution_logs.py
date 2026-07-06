from datetime import datetime

from pydantic import BaseModel


class ProjectInfo(BaseModel):
    analysis_id: str
    project_name: str
    uploaded_at: datetime


class ExecutionLogUploadResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    original_filename: str
    size_bytes: int
    status: str
    entries_count: int = 0


class ExecutionLogHistoryItem(BaseModel):
    id: str
    project_name: str
    project_id: str
    filename: str
    original_filename: str
    upload_date: datetime
    processing_status: str
    size_bytes: int
    entries_count: int = 0


class ExecutionLogEntryResponse(BaseModel):
    job_name: str | None = None
    execution_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: str | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    restart_time: datetime | None = None
    environment: str | None = None


class ExecutionLogUploadDetail(BaseModel):
    id: str
    project_id: str
    project_name: str
    filename: str
    original_filename: str
    size_bytes: int
    upload_date: datetime
    status: str
    error: str | None = None
    entries: list[ExecutionLogEntryResponse] = []

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class UploadStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ExecutionLogEntry(BaseModel):
    job_name: str | None = None
    execution_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: str | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    restart_time: datetime | None = None
    environment: str | None = None
    source_file: str | None = None


class ExecutionLogUploadRecord(BaseModel):
    id: str
    project_id: str
    project_name: str
    filename: str
    original_filename: str
    size_bytes: int
    upload_date: datetime = Field(default_factory=lambda: datetime.now())
    status: UploadStatus = UploadStatus.PENDING
    entries: list[ExecutionLogEntry] = Field(default_factory=list)
    error: str | None = None

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProjectInfo(BaseModel):
    analysis_id: str
    project_name: str
    uploaded_at: datetime


class ExecutionLogUploadResponse(BaseModel):
    id: str
    project_id: str
    project_name: str = ""
    filename: str
    original_filename: str
    size_bytes: int
    status: str
    entries_count: int = 0
    execution_records_count: int = 0
    duplicate_count: int = 0
    log_date_from: datetime | None = None
    log_date_to: datetime | None = None
    validation_messages: list[dict[str, Any]] = []
    upload_date: datetime | None = None
    total_log_lines: int = 0
    csv_rows_read: int = 0
    execution_starts_found: int = 0
    execution_ends_found: int = 0
    parse_errors: int = 0
    validation_warnings: int = 0


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


class ExecutionRecordResponse(BaseModel):
    project_id: str = ""
    project_name: str = ""
    workspace_name: str = ""
    environment_name: str = ""
    plan_name: str = ""
    artifact_name: str = ""
    task_execution_id: str = ""
    plan_execution_id: str = ""
    remote_engine_name: str = ""
    execution_start_time: datetime | None = None
    execution_end_time: datetime | None = None
    execution_status: str = ""
    execution_duration_seconds: float | None = None
    error_message: str = ""
    restart_time: datetime | None = None
    original_log_file_name: str = ""
    upload_date: datetime | None = None
    execution_attempt: int = 1
    source_file: str = ""


class ProjectUploadSummary(BaseModel):
    project_id: str
    project_name: str = ""
    upload_id: str
    original_filename: str
    upload_date: datetime | None = None
    status: str = ""
    entries_count: int = 0
    execution_records_count: int = 0
    log_date_from: datetime | None = None
    log_date_to: datetime | None = None
    validation_messages: list[dict[str, Any]] = []
    total_log_lines: int = 0
    csv_rows_read: int = 0
    execution_starts_found: int = 0
    execution_ends_found: int = 0
    parse_errors: int = 0
    validation_warnings: int = 0

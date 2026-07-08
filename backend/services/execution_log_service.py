import re

from datetime import datetime

from fastapi import UploadFile

from backend.core.logging import get_logger
from backend.execution_logs.models import (
    ExecutionLogEntry,
    ExecutionLogUploadRecord,
    UploadStatus,
)
from backend.execution_logs.processor import LogProcessor
from backend.execution_logs.storage.file_storage import FileStorage
from backend.execution_logs.records.service import get_execution_record_service
from backend.schemas.execution_logs import (
    ExecutionLogEntryResponse,
    ExecutionLogHistoryItem,
    ExecutionLogUploadDetail,
    ExecutionLogUploadResponse,
    ExecutionRecordResponse,
    ProjectInfo,
    ProjectUploadSummary,
)
from backend.services.analysis_service import analysis_service

logger = get_logger(__name__)


def _extract_diagnostics_counts(
    validation_msgs: list,
) -> dict[str, int]:
    total_log_lines = 0
    csv_rows_read = 0
    execution_starts_found = 0
    execution_ends_found = 0
    parse_errors = 0
    validation_warnings = 0
    for m in validation_msgs:
        field = getattr(m, "field", m.get("field", "") if isinstance(m, dict) else "")
        severity = getattr(m, "severity", m.get("severity", "") if isinstance(m, dict) else "")
        if field == "_parser_diagnostic":
            msg_text = getattr(m, "message", m.get("message", "") if isinstance(m, dict) else "")
            if "log lines read" in msg_text and "start events" in msg_text:
                lines_match = re.search(r"(\d+) log lines read", msg_text)
                if lines_match:
                    total_log_lines = max(total_log_lines, int(lines_match.group(1)))
                starts_match = re.search(r"(\d+) start events", msg_text)
                if starts_match:
                    execution_starts_found = max(execution_starts_found, int(starts_match.group(1)))
                ends_match = re.search(r"(\d+) end events", msg_text)
                if ends_match:
                    execution_ends_found = max(execution_ends_found, int(ends_match.group(1)))
            elif "csv records read" in msg_text or "csv rows read" in msg_text:
                csv_match = re.search(r"(\d+) (csv records|csv rows) read", msg_text)
                if csv_match:
                    csv_rows_read = max(csv_rows_read, int(csv_match.group(1)))
        else:
            if severity == "error":
                parse_errors += 1
            elif severity == "warning":
                validation_warnings += 1
    return {
        "total_log_lines": total_log_lines,
        "csv_rows_read": csv_rows_read,
        "execution_starts_found": execution_starts_found,
        "execution_ends_found": execution_ends_found,
        "parse_errors": parse_errors,
        "validation_warnings": validation_warnings,
    }


class ExecutionLogService:
    def __init__(self) -> None:
        self._storage = FileStorage()
        self._processor = LogProcessor(self._storage)

    def get_projects(self) -> list[ProjectInfo]:
        projects: list[ProjectInfo] = []
        with analysis_service._lock:
            for analysis_id, record in analysis_service._records.items():
                if record.status.value in ("completed", "partial"):
                    projects.append(
                        ProjectInfo(
                            analysis_id=analysis_id,
                            project_name=record.original_filename,
                            uploaded_at=record.created_at,
                        )
                    )
        projects.sort(key=lambda p: p.uploaded_at, reverse=True)
        return projects

    async def upload_log(
        self,
        project_id: str,
        project_name: str,
        file: UploadFile,
    ) -> ExecutionLogUploadResponse:
        record = await self._processor.process_upload(project_id, project_name, file)
        rs = get_execution_record_service()
        exec_records = rs.get_records(project_id)
        validation_msgs = rs.get_validation_messages(project_id)
        log_date_from: datetime | None = None
        log_date_to: datetime | None = None
        for r in exec_records:
            if r.execution_start_time:
                if log_date_from is None or r.execution_start_time < log_date_from:
                    log_date_from = r.execution_start_time
            if r.execution_end_time:
                if log_date_to is None or r.execution_end_time > log_date_to:
                    log_date_to = r.execution_end_time
        duplicate_count = sum(1 for m in validation_msgs if "duplicate" in m.message.lower())
        diag = _extract_diagnostics_counts(validation_msgs)
        return ExecutionLogUploadResponse(
            id=record.id,
            project_id=record.project_id,
            project_name=record.project_name or project_name,
            filename=record.filename,
            original_filename=record.original_filename,
            size_bytes=record.size_bytes,
            status=record.status.value,
            entries_count=len(record.entries),
            execution_records_count=len(exec_records),
            duplicate_count=duplicate_count,
            log_date_from=log_date_from,
            log_date_to=log_date_to,
            validation_messages=[m.model_dump() for m in validation_msgs],
            upload_date=record.upload_date,
            total_log_lines=diag["total_log_lines"],
            csv_rows_read=diag["csv_rows_read"],
            execution_starts_found=diag["execution_starts_found"],
            execution_ends_found=diag["execution_ends_found"],
            parse_errors=diag["parse_errors"],
            validation_warnings=diag["validation_warnings"],
        )

    def get_project_summary(self, project_id: str) -> ProjectUploadSummary | None:
        records = self._storage.list_all()
        project_records = [r for r in records if r.project_id == project_id]
        if not project_records:
            return None
        latest = max(project_records, key=lambda r: r.upload_date)
        rs = get_execution_record_service()
        exec_records = rs.get_records(project_id)
        validation_msgs = rs.get_validation_messages(project_id)
        log_date_from: datetime | None = None
        log_date_to: datetime | None = None
        for r in exec_records:
            if r.execution_start_time:
                if log_date_from is None or r.execution_start_time < log_date_from:
                    log_date_from = r.execution_start_time
            if r.execution_end_time:
                if log_date_to is None or r.execution_end_time > log_date_to:
                    log_date_to = r.execution_end_time
        diag = _extract_diagnostics_counts(validation_msgs)
        return ProjectUploadSummary(
            project_id=project_id,
            project_name=latest.project_name,
            upload_id=latest.id,
            original_filename=latest.original_filename,
            upload_date=latest.upload_date,
            status=latest.status.value,
            entries_count=len(latest.entries),
            execution_records_count=len(exec_records),
            log_date_from=log_date_from,
            log_date_to=log_date_to,
            validation_messages=[m.model_dump() for m in validation_msgs],
            total_log_lines=diag["total_log_lines"],
            csv_rows_read=diag["csv_rows_read"],
            execution_starts_found=diag["execution_starts_found"],
            execution_ends_found=diag["execution_ends_found"],
            parse_errors=diag["parse_errors"],
            validation_warnings=diag["validation_warnings"],
        )

    def get_upload_history(self) -> list[ExecutionLogHistoryItem]:
        records = self._storage.list_all()
        records.sort(key=lambda r: r.upload_date, reverse=True)
        return [
            ExecutionLogHistoryItem(
                id=rec.id,
                project_name=rec.project_name,
                project_id=rec.project_id,
                filename=rec.filename,
                original_filename=rec.original_filename,
                upload_date=rec.upload_date,
                processing_status=rec.status.value,
                size_bytes=rec.size_bytes,
                entries_count=len(rec.entries),
            )
            for rec in records
        ]

    def get_upload_detail(self, upload_id: str) -> ExecutionLogUploadDetail | None:
        record = self._storage.get(upload_id)
        if record is None:
            return None
        return ExecutionLogUploadDetail(
            id=record.id,
            project_id=record.project_id,
            project_name=record.project_name,
            filename=record.filename,
            original_filename=record.original_filename,
            size_bytes=record.size_bytes,
            upload_date=record.upload_date,
            status=record.status.value,
            error=record.error,
            entries=[
                ExecutionLogEntryResponse(
                    job_name=e.job_name,
                    execution_id=e.execution_id,
                    start_time=e.start_time,
                    end_time=e.end_time,
                    status=e.status,
                    duration_seconds=e.duration_seconds,
                    error_message=e.error_message,
                    restart_time=e.restart_time,
                    environment=e.environment,
                )
                for e in record.entries
            ],
        )


    def get_execution_records(self, project_id: str) -> list[ExecutionRecordResponse]:
        rs = get_execution_record_service()
        records = rs.get_records(project_id)
        return [
            ExecutionRecordResponse(**r.model_dump())
            for r in records
        ]


execution_log_service = ExecutionLogService()

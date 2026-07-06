from fastapi import UploadFile

from backend.core.logging import get_logger
from backend.execution_logs.models import (
    ExecutionLogEntry,
    ExecutionLogUploadRecord,
    UploadStatus,
)
from backend.execution_logs.processor import LogProcessor
from backend.execution_logs.storage.file_storage import FileStorage
from backend.schemas.execution_logs import (
    ExecutionLogEntryResponse,
    ExecutionLogHistoryItem,
    ExecutionLogUploadDetail,
    ExecutionLogUploadResponse,
    ProjectInfo,
)
from backend.services.analysis_service import analysis_service

logger = get_logger(__name__)


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
        return ExecutionLogUploadResponse(
            id=record.id,
            project_id=record.project_id,
            filename=record.filename,
            original_filename=record.original_filename,
            size_bytes=record.size_bytes,
            status=record.status.value,
            entries_count=len(record.entries),
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


execution_log_service = ExecutionLogService()

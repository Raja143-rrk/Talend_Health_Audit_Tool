import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from backend.core.exceptions import AppError
from backend.core.logging import get_logger
from backend.execution_logs.models import (
    ExecutionLogEntry,
    ExecutionLogUploadRecord,
    UploadStatus,
)
from backend.execution_logs.parsers.factory import ParserFactory
from backend.execution_logs.storage.base import BaseStorage
from backend.execution_logs.upload_handler import upload_handler

logger = get_logger(__name__)


class LogProcessor:
    """Orchestrates the upload, parse, and store lifecycle for a single file."""

    def __init__(self, storage: BaseStorage) -> None:
        self._storage = storage

    async def process_upload(
        self,
        project_id: str,
        project_name: str,
        file: UploadFile,
    ) -> ExecutionLogUploadRecord:
        record_id = f"el_{uuid.uuid4().hex}"
        record = ExecutionLogUploadRecord(
            id=record_id,
            project_id=project_id,
            project_name=project_name,
            filename="",
            original_filename=file.filename or "execution-log",
            size_bytes=0,
            upload_date=datetime.now(timezone.utc),
            status=UploadStatus.PROCESSING,
        )
        self._storage.save(record)

        try:
            saved_path = await upload_handler.receive(project_id, file)
            record.filename = saved_path.name
            record.size_bytes = saved_path.stat().st_size
            self._storage.save(record)

            entries = self._parse(saved_path)
            record.entries = entries
            record.status = UploadStatus.COMPLETED if entries else UploadStatus.PARTIAL
            self._storage.save(record)

            logger.info(
                "Processed upload %s for project %s: %s entries",
                record_id,
                project_id,
                len(entries),
            )
        except Exception as exc:
            record.status = UploadStatus.FAILED
            record.error = str(exc)
            self._storage.save(record)
            logger.exception("Processing failed for upload %s", record_id)
            raise AppError(f"Execution log processing failed: {exc}") from exc

        return record

    def _parse(self, file_path: Path) -> list[ExecutionLogEntry]:
        parser = ParserFactory.get_parser(file_path)
        if parser is None:
            logger.warning("No parser available for %s", file_path.name)
            return []
        try:
            return parser.parse(file_path)
        except Exception as exc:
            logger.exception("Parse error for %s", file_path.name)
            raise AppError(f"Failed to parse {file_path.name}: {exc}") from exc

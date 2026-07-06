import json
from datetime import datetime
from pathlib import Path
from threading import RLock

from backend.core.logging import get_logger
from backend.execution_logs.models import ExecutionLogUploadRecord
from backend.execution_logs.storage.base import BaseStorage

logger = get_logger(__name__)


PERSIST_DIR = Path(__file__).resolve().parents[3] / "reports"
PERSIST_FILE = PERSIST_DIR / "execution_log_records.json"


def _serialize_datetime(obj: object) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _parse_record(data: dict) -> ExecutionLogUploadRecord:
    entries_data = data.pop("entries", [])
    record = ExecutionLogUploadRecord(**data)
    for entry_data in entries_data:
        record.entries.append(ExecutionLogEntry(**entry_data))
    return record


from backend.execution_logs.models import ExecutionLogEntry  # noqa: E402


class FileStorage(BaseStorage):
    def __init__(self) -> None:
        self._records: dict[str, ExecutionLogUploadRecord] = {}
        self._lock = RLock()
        self._load()

    def _persist(self) -> None:
        try:
            PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                rid: record.model_dump(mode="json")
                for rid, record in self._records.items()
            }
            PERSIST_FILE.write_text(
                json.dumps(data, indent=2, default=_serialize_datetime),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to persist execution log records")

    def _load(self) -> None:
        try:
            if not PERSIST_FILE.is_file():
                return
            data = json.loads(PERSIST_FILE.read_text(encoding="utf-8"))
            for record_id, record_data in data.items():
                self._records[record_id] = _parse_record(record_data)
            if self._records:
                logger.info("Loaded %s execution log record(s) from disk", len(self._records))
        except Exception:
            logger.exception("Failed to load execution log records, starting fresh")

    def save(self, record: ExecutionLogUploadRecord) -> None:
        with self._lock:
            self._records[record.id] = record
            self._persist()

    def get(self, record_id: str) -> ExecutionLogUploadRecord | None:
        with self._lock:
            return self._records.get(record_id)

    def list_all(self) -> list[ExecutionLogUploadRecord]:
        with self._lock:
            return list(self._records.values())

    def delete(self, record_id: str) -> bool:
        with self._lock:
            if record_id not in self._records:
                return False
            del self._records[record_id]
            self._persist()
            return True

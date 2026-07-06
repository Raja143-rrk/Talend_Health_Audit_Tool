import csv
import io
from datetime import datetime
from pathlib import Path

from backend.core.logging import get_logger
from backend.execution_logs.models import ExecutionLogEntry
from backend.execution_logs.parsers.base import BaseParser

logger = get_logger(__name__)

FIELD_ALIASES: dict[str, str] = {
    "job name": "job_name",
    "jobname": "job_name",
    "job": "job_name",
    "execution id": "execution_id",
    "executionid": "execution_id",
    "execution": "execution_id",
    "request id": "execution_id",
    "run id": "execution_id",
    "task id": "execution_id",
    "start time": "start_time",
    "start": "start_time",
    "end time": "end_time",
    "end": "end_time",
    "finish time": "end_time",
    "completed at": "end_time",
    "duration": "duration_seconds",
    "duration (s)": "duration_seconds",
    "duration (seconds)": "duration_seconds",
    "duration seconds": "duration_seconds",
    "elapsed": "duration_seconds",
    "error message": "error_message",
    "errormessage": "error_message",
    "error": "error_message",
    "exception": "error_message",
    "restart time": "restart_time",
    "restart": "restart_time",
    "environment": "environment",
    "env": "environment",
}

DATETIME_FIELDS = {"start_time", "end_time", "restart_time"}
FLOAT_FIELDS = {"duration_seconds"}


def _normalize_header(header: str) -> str:
    key = header.strip().lower()
    return FIELD_ALIASES.get(key, key)


def _parse_value(value: str, field: str) -> str | float | datetime | None:
    stripped = value.strip()
    if not stripped or stripped == "N/A":
        return None
    if field in DATETIME_FIELDS:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
        ):
            try:
                return datetime.strptime(stripped, fmt)
            except ValueError:
                continue
        return stripped
    if field in FLOAT_FIELDS:
        try:
            return float(stripped)
        except ValueError:
            return None
    return stripped


class CsvParser(BaseParser):

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".csv"

    def parse(self, file_path: Path) -> list[ExecutionLogEntry]:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Cannot read CSV file %s: %s", file_path, exc)
            return []

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return []

        field_map = {_normalize_header(h): h for h in reader.fieldnames}
        source = file_path.name
        entries: list[ExecutionLogEntry] = []

        for row in reader:
            kwargs: dict = {"source_file": source}
            for canonical, original in field_map.items():
                raw = row.get(original, "")
                kwargs[canonical] = _parse_value(raw, canonical)
            entries.append(ExecutionLogEntry(**kwargs))

        logger.info("Parsed %s execution record(s) from %s", len(entries), source)
        return entries

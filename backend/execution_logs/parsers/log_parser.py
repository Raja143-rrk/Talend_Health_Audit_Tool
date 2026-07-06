import re
from datetime import datetime
from pathlib import Path

from backend.core.logging import get_logger
from backend.execution_logs.models import ExecutionLogEntry
from backend.execution_logs.parsers.base import BaseParser

logger = get_logger(__name__)

TIMESTAMP_PATTERNS = [
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.,]\d{3}"),
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"),
    re.compile(r"\d{2}/\d{2}/\d{4}[ ]\d{2}:\d{2}:\d{2}"),
]

JOB_START_RE = re.compile(
    r"(?:Starting|Begin)\s+(?:job\s+)?['\"]?([\w\s._-]+)['\"]?", re.IGNORECASE
)
JOB_END_RE = re.compile(
    r"(?:Finished|Complete|Stop)\s+(?:job\s+)?['\"]?([\w\s._-]+)['\"]?", re.IGNORECASE
)
STATUS_RE = re.compile(
    r"(?:status|result|exit)[:\s]+(success|failure|error|completed|failed|running|warning)",
    re.IGNORECASE,
)
ERROR_RE = re.compile(
    r"(?:error|exception|failure|failed|fault)[:\s]+(.+)", re.IGNORECASE
)
JOB_NAME_INLINE_RE = re.compile(
    r"-\s+(\S+)\s+-\s+(start|begin|end|stop|complete|running|finished)", re.IGNORECASE
)
DURATION_RE = re.compile(
    r"(?:duration|took|elapsed|ran\s+for)[:\s]+(\d+(?:\.\d+)?)\s*(?:ms|s|sec|seconds|milliseconds)?",
    re.IGNORECASE,
)
EXECUTION_ID_RE = re.compile(
    r"(?:execution[_\s]?id|request[_\s]?id|run[_\s]?id|task[_\s]?id)[:\s]+(\S+)",
    re.IGNORECASE,
)
ENVIRONMENT_RE = re.compile(
    r"(?:environment|env|context)[:\s]+(\w+)", re.IGNORECASE
)


def _extract_timestamp(line: str) -> datetime | None:
    for pattern in TIMESTAMP_PATTERNS:
        match = pattern.search(line)
        if match:
            raw = match.group(0)
            sep = " " if " " in raw else "T"
            for fmt in (
                f"%Y-%m-%d{sep}%H:%M:%S.%f",
                f"%Y-%m-%d{sep}%H:%M:%S",
                "%m/%d/%Y %H:%M:%S",
            ):
                try:
                    cleaned = raw.replace(",", ".")
                    return datetime.strptime(cleaned, fmt)
                except ValueError:
                    continue
    return None


class LogParser(BaseParser):

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".log", ".txt")

    def parse(self, file_path: Path) -> list[ExecutionLogEntry]:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Cannot read log file %s: %s", file_path, exc)
            return []

        lines = text.splitlines()
        if not lines:
            return []

        source = file_path.name
        seen_sigs: set[str] = set()
        entries: list[ExecutionLogEntry] = []

        current: ExecutionLogEntry | None = None
        start_idx: int | None = None

        def flush(last_ts: datetime | None = None) -> None:
            nonlocal current
            if current is None:
                return
            if last_ts and current.end_time is None:
                current.end_time = last_ts
            sig = f"{current.job_name or ''}|{str(current.start_time or '')}"
            if sig not in seen_sigs:
                seen_sigs.add(sig)
                if current.job_name or current.start_time:
                    entries.append(current)
            current = None

        for i, line in enumerate(lines):
            ts = _extract_timestamp(line)
            start_m = JOB_START_RE.search(line)

            if ts and start_m:
                flush(ts)
                current = ExecutionLogEntry(source_file=source)
                start_idx = i
                current.start_time = ts
                current.job_name = start_m.group(1).strip()
                continue

            if current is None:
                continue

            m = JOB_NAME_INLINE_RE.search(line)
            if m and current.job_name is None:
                current.job_name = m.group(1)

            m = EXECUTION_ID_RE.search(line)
            if m and current.execution_id is None:
                current.execution_id = m.group(1).strip()

            m = ENVIRONMENT_RE.search(line)
            if m and current.environment is None:
                current.environment = m.group(1).strip()

            m = JOB_END_RE.search(line)
            if m:
                if ts and current.end_time is None:
                    current.end_time = ts

            m = STATUS_RE.search(line)
            if m:
                if current.status is None:
                    current.status = m.group(1).lower()
                if ts and current.end_time is None:
                    current.end_time = ts

            m = DURATION_RE.search(line)
            if m and current.duration_seconds is None:
                current.duration_seconds = float(m.group(1))

            m = ERROR_RE.search(line)
            if m and current.error_message is None:
                current.error_message = m.group(1).strip()

            if JOB_END_RE.search(line) or STATUS_RE.search(line):
                flush(ts)

        flush()

        for entry in entries:
            if entry.duration_seconds is None and entry.start_time and entry.end_time:
                diff = (entry.end_time - entry.start_time).total_seconds()
                if diff >= 0:
                    entry.duration_seconds = round(diff, 3)

        logger.info("Parsed %s job execution(s) from %s", len(entries), source)
        return entries

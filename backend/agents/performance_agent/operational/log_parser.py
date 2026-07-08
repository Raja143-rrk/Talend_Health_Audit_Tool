from datetime import datetime, timedelta, timezone
from typing import Any

from backend.agents.performance_agent.operational.models import ExecutionLogEntry
from backend.core.logging import get_logger

logger = get_logger(__name__)


class LogParser:
    LOOKBACK_DAYS = 10

    def parse(self, raw_logs: list[dict[str, Any]] | None) -> list[ExecutionLogEntry]:
        if not raw_logs:
            logger.info("--- DEBUG: No execution logs provided for parsing.")
            return []

        logger.info("--- DEBUG: Performance LogParser received %d raw records ---",
                     len(raw_logs))
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.LOOKBACK_DAYS)
        parsed: list[ExecutionLogEntry] = []
        skipped_no_job = 0
        skipped_cutoff = 0

        for entry in raw_logs:
            try:
                log_entry = self._parse_single(entry, cutoff)
                if log_entry is not None:
                    parsed.append(log_entry)
                else:
                    job_name = str(entry.get("job_name") or "")
                    status = str(entry.get("status") or "")
                    started_at = entry.get("started_at")
                    if not job_name:
                        skipped_no_job += 1
                        logger.debug("Skipped (no job_name): status=%s started=%s",
                                     status, started_at)
                    elif started_at:
                        try:
                            dt = self._parse_datetime(started_at)
                            if dt and dt < cutoff:
                                skipped_cutoff += 1
                        except Exception:
                            pass
            except Exception as exc:
                logger.warning("Failed to parse execution log entry: %s", exc)

        logger.info(
            "--- DEBUG: Parsed %d / %d records. Skipped (no job_name)=%d, (cutoff)=%d ---",
            len(parsed), len(raw_logs), skipped_no_job, skipped_cutoff,
        )
        return parsed

    def _parse_single(
        self,
        entry: dict[str, Any],
        cutoff: datetime,
    ) -> ExecutionLogEntry | None:
        job_name = str(entry.get("job_name") or "")
        if not job_name:
            logger.debug("Skipping log entry without job_name.")
            return None

        status = str(entry.get("status") or "").lower()
        started_at = self._parse_datetime(entry.get("started_at"))
        finished_at = self._parse_datetime(entry.get("finished_at"))

        logger.info(
            "Processing record: job_name=%s status=%s started=%s finished=%s duration=%s exec_id=%s",
            job_name, status,
            started_at.isoformat() if started_at else "null",
            finished_at.isoformat() if finished_at else "null",
            entry.get("duration_seconds"),
            entry.get("execution_id", ""),
        )

        if started_at and started_at < cutoff:
            logger.info("Skipping record (older than %d day cutoff): %s started=%s",
                        self.LOOKBACK_DAYS, job_name, started_at.isoformat())
            return None

        duration = entry.get("duration_seconds")
        if duration is None and started_at and finished_at:
            duration = (finished_at - started_at).total_seconds()
        if duration is not None:
            duration = float(duration)

        return ExecutionLogEntry(
            job_name=job_name,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration,
            error_message=str(entry.get("error_message") or ""),
            execution_id=str(entry.get("execution_id") or ""),
        )

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                pass
        logger.debug("Could not parse datetime value: %s", value)
        return None

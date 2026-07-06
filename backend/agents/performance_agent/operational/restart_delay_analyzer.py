from statistics import mean

from backend.agents.performance_agent.operational.models import (
    ExecutionLogEntry,
    RestartDelayMetrics,
)
from backend.core.logging import get_logger

logger = get_logger(__name__)


class RestartDelayAnalyzer:
    def analyze(self, logs: list[ExecutionLogEntry]) -> RestartDelayMetrics:
        job_entries: dict[str, list[ExecutionLogEntry]] = {}
        for entry in logs:
            if entry.started_at is None:
                continue
            job_entries.setdefault(entry.job_name, []).append(entry)

        for job_name in job_entries:
            job_entries[job_name].sort(key=lambda e: e.started_at)

        all_delays: list[float] = []
        job_delays_map: dict[str, list[float]] = {}

        for job_name, entries in job_entries.items():
            last_failure_time = None

            for entry in entries:
                if entry.status == "failure" and entry.started_at:
                    last_failure_time = entry.started_at

                elif entry.status == "success" and entry.started_at and last_failure_time is not None:
                    delay_seconds = (entry.started_at - last_failure_time).total_seconds()
                    delay_hours = round(delay_seconds / 3600, 2)

                    if delay_hours >= 0:
                        all_delays.append(delay_hours)
                        job_delays_map.setdefault(job_name, []).append(delay_hours)

                    last_failure_time = None

        total_restarts = len(all_delays)

        if not all_delays:
            logger.info("No restart delay data available.")
            return RestartDelayMetrics()

        result = RestartDelayMetrics(
            average_delay_hours=round(mean(all_delays), 2),
            min_delay_hours=round(min(all_delays), 2),
            max_delay_hours=round(max(all_delays), 2),
            job_delays=job_delays_map,
            total_restarts=total_restarts,
        )

        logger.info(
            "Restart delay analysis: avg=%.2fh min=%.2fh max=%.2fh across %d restarts.",
            result.average_delay_hours,
            result.min_delay_hours,
            result.max_delay_hours,
            total_restarts,
        )

        return result

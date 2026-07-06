from statistics import mean

from backend.agents.performance_agent.operational.models import (
    ExecutionLatencyMetrics,
    ExecutionLogEntry,
)
from backend.core.logging import get_logger

logger = get_logger(__name__)


class LatencyAnalyzer:
    def analyze(self, logs: list[ExecutionLogEntry]) -> ExecutionLatencyMetrics:
        job_durations: dict[str, list[float]] = {}

        for entry in logs:
            if entry.duration_seconds is None:
                continue
            job_durations.setdefault(entry.job_name, []).append(entry.duration_seconds)

        if not job_durations:
            logger.info("No duration data available for latency analysis.")
            return ExecutionLatencyMetrics()

        job_avg_durations: list[tuple[str, float]] = []
        all_durations: list[float] = []

        for job_name, durations in job_durations.items():
            avg = mean(durations)
            job_avg_durations.append((job_name, avg))
            all_durations.extend(durations)

        job_avg_durations.sort(key=lambda x: x[1], reverse=True)

        top_5 = [
            {"job_name": job_name, "average_duration_seconds": round(avg, 2)}
            for job_name, avg in job_avg_durations[:5]
        ]

        overall_avg = round(mean(all_durations), 2) if all_durations else 0.0
        overall_max = round(max(all_durations), 2) if all_durations else 0.0
        overall_min = round(min(all_durations), 2) if all_durations else 0.0

        logger.info(
            "Latency analysis: avg=%.2fs max=%.2fs min=%.2fs across %d jobs.",
            overall_avg,
            overall_max,
            overall_min,
            len(job_durations),
        )

        return ExecutionLatencyMetrics(
            top_5_longest_jobs=top_5,
            average_duration_seconds=overall_avg,
            max_duration_seconds=overall_max,
            min_duration_seconds=overall_min,
            job_durations={job: [round(d, 2) for d in durations] for job, durations in job_durations.items()},
        )

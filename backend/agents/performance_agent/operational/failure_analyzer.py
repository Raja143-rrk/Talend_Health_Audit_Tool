from collections import Counter

from backend.agents.performance_agent.operational.models import (
    ExecutionLogEntry,
    FailedExecutionMetrics,
    FailureFrequencyMetrics,
)
from backend.core.logging import get_logger

logger = get_logger(__name__)


class FailureAnalyzer:
    RECURRING_FAILURE_THRESHOLD = 3

    def analyze(
        self,
        logs: list[ExecutionLogEntry],
    ) -> tuple[FailureFrequencyMetrics, FailedExecutionMetrics]:
        job_failure_counts: Counter[str] = Counter()
        total_executions = len(logs)
        failed_entries: list[ExecutionLogEntry] = []
        error_message_map: dict[str, list[str]] = {}

        for entry in logs:
            if entry.status == "failure":
                job_failure_counts[entry.job_name] += 1
                failed_entries.append(entry)

                error_key = entry.job_name
                if entry.error_message:
                    normalized = self._normalize_error(entry.error_message)
                    error_message_map.setdefault(normalized, [])
                    if entry.job_name not in error_message_map[normalized]:
                        error_message_map[normalized].append(entry.job_name)
                else:
                    error_message_map.setdefault("unknown_error", [])
                    if entry.job_name not in error_message_map["unknown_error"]:
                        error_message_map["unknown_error"].append(entry.job_name)

        total_failures = len(failed_entries)
        overall_failure_rate = (
            round((total_failures / total_executions) * 100, 2)
            if total_executions > 0
            else 0.0
        )

        recurring_failures = [
            job_name
            for job_name, count in job_failure_counts.most_common()
            if count >= self.RECURRING_FAILURE_THRESHOLD
        ]

        failure_frequency = FailureFrequencyMetrics(
            job_failure_counts=dict(job_failure_counts.most_common()),
            overall_failure_rate=overall_failure_rate,
            recurring_failures=recurring_failures,
            total_executions=total_executions,
            total_failures=total_failures,
        )

        failed_executions = FailedExecutionMetrics(
            failed_jobs=[
                {
                    "job_name": entry.job_name,
                    "timestamp": entry.started_at.isoformat() if entry.started_at else None,
                    "error_message": entry.error_message,
                    "execution_id": entry.execution_id,
                }
                for entry in failed_entries
            ],
            error_groups=dict(error_message_map),
            total_failed_jobs=len(set(entry.job_name for entry in failed_entries)),
        )

        logger.info(
            "Failure analysis: %d failures out of %d executions (%.2f%%), %d recurring jobs.",
            total_failures,
            total_executions,
            overall_failure_rate,
            len(recurring_failures),
        )

        return failure_frequency, failed_executions

    def _normalize_error(self, error_message: str) -> str:
        lower = error_message.lower().strip()
        for keyword, label in [
            ("connection refused", "connection_error"),
            ("timeout", "timeout_error"),
            ("permission denied", "permission_error"),
            ("null pointer", "null_pointer_error"),
            ("out of memory", "out_of_memory_error"),
            ("sql", "sql_error"),
            ("file not found", "file_not_found_error"),
            ("class not found", "class_not_found_error"),
        ]:
            if keyword in lower:
                return label
        words = lower.split()
        if words:
            return "_".join(words[:3])
        return "unknown_error"

from collections.abc import Callable
from dataclasses import dataclass

from backend.agents.performance_agent.operational.models import (
    ExecutionLogEntry,
    FailureFrequencyMetrics,
    ExecutionLatencyMetrics,
    RestartDelayMetrics,
)


@dataclass(frozen=True)
class PerformanceRule:
    id: str
    title: str
    category: str
    recommendation: str
    optimization_suggestion: str
    predicate: Callable[[list[ExecutionLogEntry]], bool]


def component_name(component: dict) -> str:
    return str(component.get("component_name") or "").lower()


def parameter_value(component: dict, *keys: str) -> str | None:
    parameters = component.get("parameters") or {}
    normalized = {str(key).upper(): str(value) for key, value in parameters.items()}
    for key in keys:
        value = normalized.get(key.upper())
        if value not in {None, ""}:
            return value
    return None


def is_enabled(component: dict) -> bool:
    return not bool(component.get("disabled"))


def commit_size(component: dict) -> int | None:
    raw_value = parameter_value(
        component,
        "COMMIT_EVERY",
        "COMMIT_SIZE",
        "BATCH_SIZE",
        "NB_LINE",
    )
    if raw_value is None:
        return None
    try:
        return int(raw_value.strip('"'))
    except ValueError:
        return None


DEFAULT_PERFORMANCE_RULES = [
    PerformanceRule(
        id="PERF-OP-001",
        title="High failure rate detected",
        category="failure_frequency",
        recommendation="Investigate root cause of job failures and implement error handling.",
        optimization_suggestion="Add retry logic, improve error handling, and set up monitoring alerts.",
        predicate=lambda logs: _failure_rate(logs) > 20.0,
    ),
    PerformanceRule(
        id="PERF-OP-002",
        title="Recurring job failures detected",
        category="recurring_failures",
        recommendation="Review jobs with repeated failures and implement permanent fixes.",
        optimization_suggestion="Analyze failure patterns, fix underlying issues, and add automated recovery.",
        predicate=lambda logs: _recurring_failure_count(logs) > 0,
    ),
    PerformanceRule(
        id="PERF-OP-003",
        title="High execution latency detected",
        category="execution_latency",
        recommendation="Optimize long-running jobs to reduce execution time.",
        optimization_suggestion="Review job design, add indexing, optimize queries, and consider parallel execution.",
        predicate=lambda logs: _average_latency(logs) > 300.0,
    ),
    PerformanceRule(
        id="PERF-OP-004",
        title="Long restart delay detected",
        category="restart_delay",
        recommendation="Reduce time between failure and successful recovery.",
        optimization_suggestion="Set up automated job restart, improve alerting, and define escalation paths.",
        predicate=lambda logs: _average_restart_delay(logs) > 24.0,
    ),
    PerformanceRule(
        id="PERF-OP-005",
        title="Elevated failure rate in jobs",
        category="failure_frequency",
        recommendation="Review the top failing jobs and address recurring issues.",
        optimization_suggestion="Prioritize fixes for jobs with highest failure rates.",
        predicate=lambda logs: _job_count_with_failures(logs) > 0,
    ),
]


def _failure_rate(logs: list[ExecutionLogEntry]) -> float:
    if not logs:
        return 0.0
    failures = sum(1 for log in logs if log.status == "failure")
    return (failures / len(logs)) * 100


def _recurring_failure_count(logs: list[ExecutionLogEntry]) -> int:
    from collections import Counter
    counter = Counter(log.job_name for log in logs if log.status == "failure")
    return sum(1 for count in counter.values() if count >= 3)


def _average_latency(logs: list[ExecutionLogEntry]) -> float:
    durations = [log.duration_seconds for log in logs if log.duration_seconds is not None]
    if not durations:
        return 0.0
    return sum(durations) / len(durations)


def _average_restart_delay(logs: list[ExecutionLogEntry]) -> float:
    job_entries: dict[str, list[ExecutionLogEntry]] = {}
    for log in logs:
        if log.started_at is None:
            continue
        job_entries.setdefault(log.job_name, []).append(log)

    delays: list[float] = []
    for entries in job_entries.values():
        entries.sort(key=lambda e: e.started_at)
        last_failure = None
        for entry in entries:
            if entry.status == "failure" and entry.started_at:
                last_failure = entry.started_at
            elif entry.status == "success" and entry.started_at and last_failure is not None:
                delay = (entry.started_at - last_failure).total_seconds() / 3600
                if delay >= 0:
                    delays.append(delay)
                last_failure = None

    if not delays:
        return 0.0
    return sum(delays) / len(delays)


def _job_count_with_failures(logs: list[ExecutionLogEntry]) -> int:
    job_names = set(log.job_name for log in logs if log.status == "failure")
    return len(job_names)

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExecutionLogEntry(BaseModel):
    job_name: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    execution_id: str | None = None


class FailureFrequencyMetrics(BaseModel):
    job_failure_counts: dict[str, int] = Field(default_factory=dict)
    overall_failure_rate: float = 0.0
    recurring_failures: list[str] = Field(default_factory=list)
    total_executions: int = 0
    total_failures: int = 0


class ExecutionLatencyMetrics(BaseModel):
    top_5_longest_jobs: list[dict[str, Any]] = Field(default_factory=list)
    average_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0
    min_duration_seconds: float = 0.0
    job_durations: dict[str, list[float]] = Field(default_factory=dict)


class FailedExecutionMetrics(BaseModel):
    failed_jobs: list[dict[str, Any]] = Field(default_factory=list)
    error_groups: dict[str, list[str]] = Field(default_factory=dict)
    total_failed_jobs: int = 0


class RestartDelayMetrics(BaseModel):
    average_delay_hours: float = 0.0
    min_delay_hours: float = 0.0
    max_delay_hours: float = 0.0
    job_delays: dict[str, list[float]] = Field(default_factory=dict)
    total_restarts: int = 0


class PerformanceScore(BaseModel):
    overall_score: int = 100
    grade: str = "Optimized"
    failure_score: int = 100
    latency_score: int = 100
    restart_delay_score: int = 100
    deductions: dict[str, int] = Field(default_factory=dict)


class OperationalMetrics(BaseModel):
    failure_frequency: FailureFrequencyMetrics = Field(default_factory=FailureFrequencyMetrics)
    execution_latency: ExecutionLatencyMetrics = Field(default_factory=ExecutionLatencyMetrics)
    failed_executions: FailedExecutionMetrics = Field(default_factory=FailedExecutionMetrics)
    restart_delay: RestartDelayMetrics = Field(default_factory=RestartDelayMetrics)
    performance_score: PerformanceScore = Field(default_factory=PerformanceScore)

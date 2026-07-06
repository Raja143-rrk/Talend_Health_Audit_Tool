from backend.agents.performance_agent.operational.models import (
    FailureFrequencyMetrics,
    ExecutionLatencyMetrics,
    RestartDelayMetrics,
    PerformanceScore,
)
from backend.core.logging import get_logger

logger = get_logger(__name__)


class PerformanceScoreCalculator:
    FAILURE_RATE_WEIGHT = 40
    LATENCY_WEIGHT = 30
    RESTART_DELAY_WEIGHT = 30

    FAILURE_RATE_THRESHOLD = 20.0
    LATENCY_THRESHOLD_SECONDS = 300.0
    RESTART_DELAY_THRESHOLD_HOURS = 24.0

    MAX_DEDUCTION_PER_CATEGORY = 100

    def calculate(
        self,
        failure_frequency: FailureFrequencyMetrics,
        latency: ExecutionLatencyMetrics,
        restart_delay: RestartDelayMetrics,
    ) -> PerformanceScore:
        failure_score = self._calculate_failure_score(failure_frequency)
        latency_score = self._calculate_latency_score(latency)
        restart_score = self._calculate_restart_score(restart_delay)

        weighted_score = (
            failure_score * (self.FAILURE_RATE_WEIGHT / 100)
            + latency_score * (self.LATENCY_WEIGHT / 100)
            + restart_score * (self.RESTART_DELAY_WEIGHT / 100)
        )

        overall_score = max(0, min(100, round(weighted_score)))

        deductions = {
            "failure_deduction": 100 - failure_score,
            "latency_deduction": 100 - latency_score,
            "restart_delay_deduction": 100 - restart_score,
        }

        grade = self._grade_for_score(overall_score)

        logger.info(
            "Performance score calculated: overall=%d failure=%d latency=%d restart=%d grade=%s",
            overall_score,
            failure_score,
            latency_score,
            restart_score,
            grade,
        )

        return PerformanceScore(
            overall_score=overall_score,
            grade=grade,
            failure_score=failure_score,
            latency_score=latency_score,
            restart_delay_score=restart_score,
            deductions=deductions,
        )

    def _calculate_failure_score(self, metrics: FailureFrequencyMetrics) -> int:
        if metrics.total_executions == 0:
            return 100

        rate = metrics.overall_failure_rate
        score = max(
            0,
            100 - int((rate / self.FAILURE_RATE_THRESHOLD) * self.MAX_DEDUCTION_PER_CATEGORY),
        )

        recurring_penalty = len(metrics.recurring_failures) * 5
        score = max(0, score - recurring_penalty)

        return score

    def _calculate_latency_score(self, metrics: ExecutionLatencyMetrics) -> int:
        if metrics.average_duration_seconds <= 0:
            return 100

        avg = metrics.average_duration_seconds
        score = max(
            0,
            100 - int((avg / self.LATENCY_THRESHOLD_SECONDS) * self.MAX_DEDUCTION_PER_CATEGORY),
        )

        return score

    def _calculate_restart_score(self, metrics: RestartDelayMetrics) -> int:
        if metrics.total_restarts == 0:
            return 100

        avg = metrics.average_delay_hours
        score = max(
            0,
            100
            - int(
                (avg / self.RESTART_DELAY_THRESHOLD_HOURS)
                * self.MAX_DEDUCTION_PER_CATEGORY
            ),
        )

        return score

    def _grade_for_score(self, score: int) -> str:
        if score >= 90:
            return "Optimized"
        if score >= 80:
            return "Healthy"
        if score >= 60:
            return "Needs Improvement"
        if score >= 40:
            return "At Risk"
        return "Critical"

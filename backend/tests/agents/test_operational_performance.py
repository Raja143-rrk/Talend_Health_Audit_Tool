from datetime import datetime, timedelta, timezone

import pytest

from backend.agents.performance_agent.operational.failure_analyzer import (
    FailureAnalyzer,
)
from backend.agents.performance_agent.operational.latency_analyzer import (
    LatencyAnalyzer,
)
from backend.agents.performance_agent.operational.log_parser import LogParser
from backend.agents.performance_agent.operational.models import ExecutionLogEntry
from backend.agents.performance_agent.operational.restart_delay_analyzer import (
    RestartDelayAnalyzer,
)
from backend.agents.performance_agent.operational.score_calculator import (
    PerformanceScoreCalculator,
)


@pytest.fixture
def sample_logs():
    now = datetime.now(timezone.utc)
    return [
        ExecutionLogEntry(
            job_name="job_a",
            status="success",
            started_at=now - timedelta(hours=2),
            finished_at=now - timedelta(hours=1, minutes=30),
            duration_seconds=1800.0,
            execution_id="exec-001",
        ),
        ExecutionLogEntry(
            job_name="job_b",
            status="failure",
            started_at=now - timedelta(hours=3),
            duration_seconds=None,
            error_message="Connection refused: timeout",
            execution_id="exec-002",
        ),
        ExecutionLogEntry(
            job_name="job_a",
            status="success",
            started_at=now - timedelta(hours=5),
            finished_at=now - timedelta(hours=4, minutes=45),
            duration_seconds=900.0,
            execution_id="exec-003",
        ),
        ExecutionLogEntry(
            job_name="job_c",
            status="failure",
            started_at=now - timedelta(hours=6),
            duration_seconds=None,
            error_message="Null pointer exception in tMap",
            execution_id="exec-004",
        ),
        ExecutionLogEntry(
            job_name="job_b",
            status="success",
            started_at=now - timedelta(hours=7),
            finished_at=now - timedelta(hours=6, minutes=30),
            duration_seconds=1800.0,
            execution_id="exec-005",
        ),
        ExecutionLogEntry(
            job_name="job_b",
            status="failure",
            started_at=now - timedelta(hours=9),
            error_message="Connection refused: timeout",
            execution_id="exec-006",
        ),
        ExecutionLogEntry(
            job_name="job_b",
            status="failure",
            started_at=now - timedelta(hours=10),
            error_message="Connection refused: timeout",
            execution_id="exec-007",
        ),
        ExecutionLogEntry(
            job_name="job_a",
            status="success",
            started_at=now - timedelta(hours=12),
            finished_at=now - timedelta(hours=11),
            duration_seconds=3600.0,
            execution_id="exec-008",
        ),
    ]


@pytest.fixture
def sample_raw_logs():
    now = datetime.now(timezone.utc)
    return [
        {
            "job_name": "job_a",
            "status": "success",
            "started_at": (now - timedelta(hours=2)).isoformat(),
            "finished_at": (now - timedelta(hours=1, minutes=30)).isoformat(),
            "duration_seconds": 1800,
            "execution_id": "exec-001",
        },
        {
            "job_name": "job_b",
            "status": "failure",
            "started_at": (now - timedelta(hours=3)).isoformat(),
            "error_message": "Connection refused: timeout",
            "execution_id": "exec-002",
        },
    ]


class TestLogParser:
    def test_parse_valid_logs(self, sample_raw_logs):
        parser = LogParser()
        result = parser.parse(sample_raw_logs)
        assert len(result) == 2
        assert result[0].job_name == "job_a"
        assert result[0].status == "success"
        assert result[1].job_name == "job_b"
        assert result[1].status == "failure"

    def test_parse_empty_logs(self):
        parser = LogParser()
        result = parser.parse([])
        assert result == []

    def test_parse_none_logs(self):
        parser = LogParser()
        result = parser.parse(None)
        assert result == []

    def test_parse_skip_old_logs(self):
        parser = LogParser()
        old_entry = {
            "job_name": "old_job",
            "status": "success",
            "started_at": (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(),
        }
        result = parser.parse([old_entry])
        assert len(result) == 0

    def test_parse_datetime_various_formats(self):
        parser = LogParser()
        now = datetime.now(timezone.utc)
        formats = [
            (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S.%f"),
            (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
        ]
        logs = [
            {"job_name": f"job_{i}", "status": "success", "started_at": fmt}
            for i, fmt in enumerate(formats)
        ]
        result = parser.parse(logs)
        assert len(result) == 4

    def test_parse_entry_without_job_name(self):
        parser = LogParser()
        now = datetime.now(timezone.utc)
        logs = [
            {"status": "success", "started_at": (now - timedelta(hours=1)).isoformat()},
        ]
        result = parser.parse(logs)
        assert len(result) == 0


class TestFailureAnalyzer:
    def test_analyze_failure_rate(self, sample_logs):
        analyzer = FailureAnalyzer()
        freq, failed = analyzer.analyze(sample_logs)
        assert freq.total_executions == 8
        assert freq.total_failures == 4
        assert freq.overall_failure_rate == 50.0
        assert "Connection refused" in failed.failed_jobs[0]["error_message"]

    def test_analyze_recurring_failures(self, sample_logs):
        analyzer = FailureAnalyzer()
        freq, failed = analyzer.analyze(sample_logs)
        assert "job_b" in freq.recurring_failures
        assert "job_a" not in freq.recurring_failures

    def test_analyze_job_failure_counts(self, sample_logs):
        analyzer = FailureAnalyzer()
        freq, failed = analyzer.analyze(sample_logs)
        assert freq.job_failure_counts["job_b"] == 3
        assert freq.job_failure_counts.get("job_a", 0) == 0
        assert freq.job_failure_counts["job_c"] == 1

    def test_analyze_error_groups(self, sample_logs):
        analyzer = FailureAnalyzer()
        freq, failed = analyzer.analyze(sample_logs)
        assert "connection_error" in failed.error_groups
        assert "null_pointer_error" in failed.error_groups

    def test_analyze_empty_logs(self):
        analyzer = FailureAnalyzer()
        freq, failed = analyzer.analyze([])
        assert freq.total_executions == 0
        assert freq.total_failures == 0
        assert freq.overall_failure_rate == 0.0
        assert len(freq.recurring_failures) == 0

    def test_analyze_no_failures(self):
        analyzer = FailureAnalyzer()
        logs = [
            ExecutionLogEntry(
                job_name="job_a",
                status="success",
                started_at=datetime.now(timezone.utc),
                duration_seconds=100.0,
            ),
        ]
        freq, failed = analyzer.analyze(logs)
        assert freq.overall_failure_rate == 0.0
        assert len(failed.failed_jobs) == 0


class TestLatencyAnalyzer:
    def test_analyze_latency(self, sample_logs):
        analyzer = LatencyAnalyzer()
        metrics = analyzer.analyze(sample_logs)
        assert metrics.average_duration_seconds == 2025.0
        assert metrics.max_duration_seconds == 3600.0
        assert metrics.min_duration_seconds == 900.0

    def test_analyze_top_5(self, sample_logs):
        analyzer = LatencyAnalyzer()
        metrics = analyzer.analyze(sample_logs)
        assert len(metrics.top_5_longest_jobs) >= 1
        assert metrics.top_5_longest_jobs[0]["job_name"] == "job_a"

    def test_analyze_empty_logs(self):
        analyzer = LatencyAnalyzer()
        metrics = analyzer.analyze([])
        assert metrics.average_duration_seconds == 0.0
        assert metrics.max_duration_seconds == 0.0
        assert len(metrics.top_5_longest_jobs) == 0


class TestRestartDelayAnalyzer:
    def test_analyze_restart_delay(self):
        now = datetime.now(timezone.utc)
        logs = [
            ExecutionLogEntry(
                job_name="job_a",
                status="failure",
                started_at=now - timedelta(hours=5),
                execution_id="exec-001",
            ),
            ExecutionLogEntry(
                job_name="job_a",
                status="success",
                started_at=now - timedelta(hours=3),
                duration_seconds=100.0,
                execution_id="exec-002",
            ),
            ExecutionLogEntry(
                job_name="job_b",
                status="failure",
                started_at=now - timedelta(hours=10),
                execution_id="exec-003",
            ),
            ExecutionLogEntry(
                job_name="job_b",
                status="success",
                started_at=now - timedelta(hours=6),
                duration_seconds=200.0,
                execution_id="exec-004",
            ),
        ]
        analyzer = RestartDelayAnalyzer()
        metrics = analyzer.analyze(logs)
        assert metrics.total_restarts == 2
        assert metrics.average_delay_hours == 3.0
        assert metrics.max_delay_hours == 4.0
        assert metrics.min_delay_hours == 2.0

    def test_analyze_no_restarts(self):
        analyzer = RestartDelayAnalyzer()
        logs = [
            ExecutionLogEntry(
                job_name="job_a",
                status="success",
                started_at=datetime.now(timezone.utc),
                duration_seconds=100.0,
            ),
        ]
        metrics = analyzer.analyze(logs)
        assert metrics.total_restarts == 0

    def test_analyze_empty_logs(self):
        analyzer = RestartDelayAnalyzer()
        metrics = analyzer.analyze([])
        assert metrics.total_restarts == 0
        assert metrics.average_delay_hours == 0.0

    def test_analyze_multiple_failures_one_success(self):
        now = datetime.now(timezone.utc)
        logs = [
            ExecutionLogEntry(
                job_name="job_a",
                status="failure",
                started_at=now - timedelta(hours=10),
                execution_id="exec-001",
            ),
            ExecutionLogEntry(
                job_name="job_a",
                status="failure",
                started_at=now - timedelta(hours=8),
                execution_id="exec-002",
            ),
            ExecutionLogEntry(
                job_name="job_a",
                status="success",
                started_at=now - timedelta(hours=5),
                duration_seconds=100.0,
                execution_id="exec-003",
            ),
        ]
        analyzer = RestartDelayAnalyzer()
        metrics = analyzer.analyze(logs)
        assert metrics.total_restarts == 1
        assert 2.0 <= metrics.average_delay_hours <= 4.0


class TestPerformanceScoreCalculator:
    def test_calculate_perfect_score(self):
        calculator = PerformanceScoreCalculator()
        from backend.agents.performance_agent.operational.models import (
            ExecutionLatencyMetrics,
            FailureFrequencyMetrics,
            RestartDelayMetrics,
        )

        score = calculator.calculate(
            FailureFrequencyMetrics(total_executions=10, total_failures=0, overall_failure_rate=0.0),
            ExecutionLatencyMetrics(average_duration_seconds=0.0, max_duration_seconds=0.0),
            RestartDelayMetrics(average_delay_hours=0.0, total_restarts=0),
        )
        assert score.overall_score == 100
        assert score.grade == "Optimized"

    def test_calculate_poor_score(self):
        calculator = PerformanceScoreCalculator()
        from backend.agents.performance_agent.operational.models import (
            ExecutionLatencyMetrics,
            FailureFrequencyMetrics,
            RestartDelayMetrics,
        )

        score = calculator.calculate(
            FailureFrequencyMetrics(
                total_executions=10,
                total_failures=8,
                overall_failure_rate=80.0,
                recurring_failures=["job_a", "job_b"],
            ),
            ExecutionLatencyMetrics(
                average_duration_seconds=600.0,
                max_duration_seconds=1200.0,
            ),
            RestartDelayMetrics(
                average_delay_hours=72.0,
                max_delay_hours=120.0,
                total_restarts=5,
            ),
        )
        assert score.overall_score < 40
        assert score.grade == "Critical"

    def test_calculate_no_data(self):
        calculator = PerformanceScoreCalculator()
        from backend.agents.performance_agent.operational.models import (
            ExecutionLatencyMetrics,
            FailureFrequencyMetrics,
            RestartDelayMetrics,
        )

        score = calculator.calculate(
            FailureFrequencyMetrics(),
            ExecutionLatencyMetrics(),
            RestartDelayMetrics(),
        )
        assert score.overall_score == 100

    def test_grade_thresholds(self):
        calculator = PerformanceScoreCalculator()
        cases = [
            (100, "Optimized"),
            (90, "Optimized"),
            (85, "Healthy"),
            (70, "Needs Improvement"),
            (50, "At Risk"),
            (20, "Critical"),
        ]
        for score_value, expected_grade in cases:
            grade = calculator._grade_for_score(score_value)
            assert grade == expected_grade, f"Score {score_value}: expected {expected_grade}, got {grade}"

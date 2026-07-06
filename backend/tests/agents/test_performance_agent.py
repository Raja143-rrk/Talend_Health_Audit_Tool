from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from backend.agents.performance_agent.agent import PerformanceAgent
from backend.shared.models import AgentResponse, AgentStatus, FindingSeverity


class TestPerformanceAgent:
    async def test_execute_returns_completed_response(self, agent_context, mock_rule_engine, sample_finding):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=([sample_finding], [], {"performance_findings": 1}))
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert isinstance(result, AgentResponse)
        assert result.status == AgentStatus.COMPLETED

    async def test_execute_includes_artifact(self, agent_context, mock_rule_engine, sample_finding):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=([sample_finding], [], {"performance_findings": 1}))
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "performance-analysis"
        assert "findings" in result.artifacts[0].payload

    async def test_execute_calls_analyzer(self, agent_context, mock_rule_engine, sample_finding):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=([sample_finding], [], {"performance_findings": 1}))
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_analyzer.analyze.assert_called_once()

    async def test_execute_calls_rule_engine(self, agent_context, mock_rule_engine, sample_finding):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=([sample_finding], [], {"performance_findings": 1}))
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_rule_engine.evaluate.assert_called_once()

    async def test_execute_returns_findings(self, agent_context, mock_rule_engine, sample_finding):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=([sample_finding], [], {"performance_findings": 1}))
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert len(result.findings) > 0

    async def test_execute_returns_metrics(self, agent_context, mock_rule_engine, sample_finding):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=([sample_finding], [], {"performance_findings": 1}))
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert "performance_findings" in result.metrics

    async def test_execute_without_logs(self, mock_rule_engine):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=([], [], {"performance_findings": 0}))
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        context = MagicMock()
        context.metadata = {}
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(context, started_at)
        assert result.status == AgentStatus.COMPLETED
        assert len(result.findings) == 0

    async def test_build_rule_payload_merges_findings(self, mock_rule_engine, sample_finding):
        mock_analyzer = MagicMock()
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        payload = agent._build_rule_payload({"jobs": []}, [sample_finding])
        assert "performance_findings" in payload
        assert payload["performance_findings_count"] == 1

    async def test_build_metrics(self, mock_rule_engine, sample_finding):
        mock_analyzer = MagicMock()
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        metrics = agent._build_metrics(
            operational_findings=[sample_finding],
            operational_metrics={"existing": 1},
        )
        assert metrics["performance_findings"] == 1
        assert metrics["existing"] == 1

    async def test_resolve_execution_logs_from_context(self, mock_rule_engine):
        mock_analyzer = MagicMock()
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        context = MagicMock()
        context.metadata = {"execution_logs": [{"job_name": "test", "status": "success"}]}
        logs = agent._resolve_execution_logs(context)
        assert logs == [{"job_name": "test", "status": "success"}]

    async def test_resolve_execution_logs_missing(self, mock_rule_engine):
        mock_analyzer = MagicMock()
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        context = MagicMock()
        context.metadata = {}
        logs = agent._resolve_execution_logs(context)
        assert logs is None

    async def test_execute_passes_execution_logs_to_analyzer(self, agent_context, mock_rule_engine, sample_finding):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=([sample_finding], [], {"performance_findings": 1}))
        agent = PerformanceAgent(analyzer=mock_analyzer, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_analyzer.analyze.assert_called_once_with(agent_context.metadata.get("execution_logs"))

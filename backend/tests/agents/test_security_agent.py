from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents.security_agent.agent import SecurityAgent
from backend.shared.models import AgentFinding, AgentResponse, AgentStatus, FindingSeverity
from backend.rule_engine.models import RuleCategory


class TestSecurityAgent:
    async def test_execute_returns_completed_response(self, agent_context, mock_rule_engine, sample_finding):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([sample_finding], [], {"security_findings": 1}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert isinstance(result, AgentResponse)
        assert result.status == AgentStatus.COMPLETED

    async def test_execute_includes_artifact(self, agent_context, mock_rule_engine, sample_finding):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([sample_finding], [], {"security_findings": 1}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "security-analysis"
        assert "findings" in result.artifacts[0].payload

    async def test_execute_calls_scanner(self, agent_context, mock_rule_engine, sample_finding):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([sample_finding], [], {"security_findings": 1}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_scanner.scan.assert_called_once()

    async def test_execute_calls_rule_engine(self, agent_context, mock_rule_engine, sample_finding):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([sample_finding], [], {"security_findings": 1}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_rule_engine.evaluate.assert_called_once()

    async def test_execute_returns_findings(self, agent_context, mock_rule_engine, sample_finding):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([sample_finding], [], {"security_findings": 1}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert len(result.findings) > 0

    async def test_execute_returns_metrics(self, agent_context, mock_rule_engine, sample_finding):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([sample_finding], [], {"security_findings": 1}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert "security_findings" in result.metrics
        assert result.metrics["security_findings"] > 0

    async def test_execute_without_inventory(self, mock_rule_engine):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([], [], {"security_findings": 0}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        context = MagicMock()
        context.metadata = {}
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(context, started_at)
        assert result.status == AgentStatus.COMPLETED
        assert len(result.findings) == 0

    async def test_build_rule_payload_merges_findings(self, sample_finding):
        mock_scanner = MagicMock()
        mock_rule_engine = MagicMock()
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        payload = agent._build_rule_payload({"jobs": []}, [sample_finding])
        assert "security_findings" in payload
        assert payload["security_findings_count"] == 1

    async def test_resolve_workspace_path_from_metadata(self, agent_context, mock_rule_engine):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([], [], {}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        path = agent._resolve_workspace_path(agent_context)
        assert path == "/fake/workspace"

    async def test_resolve_workspace_path_extracted_fallback(self, mock_rule_engine):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([], [], {}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        context = MagicMock()
        context.metadata = {"extracted_workspace": "/extracted/path"}
        path = agent._resolve_workspace_path(context)
        assert path == "/extracted/path"

    async def test_resolve_workspace_path_none(self, mock_rule_engine):
        mock_scanner = MagicMock()
        mock_scanner.scan = MagicMock(return_value=([], [], {}))
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        context = MagicMock()
        context.metadata = {}
        path = agent._resolve_workspace_path(context)
        assert path is None

    async def test_evidence_backed_findings_filters_incomplete(self, sample_finding):
        mock_scanner = MagicMock()
        mock_rule_engine = MagicMock()
        agent = SecurityAgent(scanner=mock_scanner, rule_engine=mock_rule_engine)
        incomplete = AgentFinding(
            id="incomplete",
            title="Incomplete",
            job_name="unknown",
            component_name="unknown",
            component_type="unknown",
            category="security",
            severity=FindingSeverity.INFORMATIONAL,
            description="Missing evidence",
        )
        result = agent._evidence_backed_findings([sample_finding, incomplete])
        assert len(result) == 1
        assert result[0].id == sample_finding.id

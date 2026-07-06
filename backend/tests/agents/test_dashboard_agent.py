from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from backend.agents.dashboard_agent.agent import DashboardAgent
from backend.agents.dashboard_agent.models import (
    DashboardChartData,
    DashboardKpi,
    DashboardResponse,
)
from backend.shared.models import AgentResponse, AgentStatus


class TestDashboardAgent:
    async def test_execute_returns_completed_response(self, agent_context, mock_rule_engine):
        mock_aggregator = MagicMock()
        mock_aggregator.aggregate = MagicMock(
            return_value=DashboardResponse(
                analysis_id="test-analysis-001",
                project_name="TestProject",
                total_jobs=0,
                total_components=0,
                critical_issues=0,
                compliance_score=100,
                compliance_grade="Optimized",
                compliance_maturity="standard",
                compliance_breakdown={},
                kpis=[
                    DashboardKpi(label="Compliance Score", value=100, suffix="%", severity="optimized"),
                    DashboardKpi(label="Total Jobs", value=0, severity="informational"),
                    DashboardKpi(label="Total Components", value=0, severity="informational"),
                    DashboardKpi(label="Disabled Components", value=0, severity="warning"),
                    DashboardKpi(label="Critical Issues", value=0, severity="critical_risk"),
                    DashboardKpi(label="Security Findings", value=0, severity="warning"),
                    DashboardKpi(label="Performance Findings", value=0, severity="warning"),
                ],
                severity_summary={"critical_risk": 0, "risk": 0, "warning": 0, "advisory": 0, "informational": 0},
                charts=DashboardChartData(),
            )
        )
        agent = DashboardAgent(
            aggregator=mock_aggregator,
            security_rule_engine=mock_rule_engine,
            performance_rule_engine=mock_rule_engine,
        )
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert isinstance(result, AgentResponse)
        assert result.status == AgentStatus.COMPLETED

    async def test_execute_includes_artifact(self, agent_context, mock_rule_engine):
        mock_aggregator = MagicMock()
        mock_aggregator.aggregate = MagicMock(
            return_value=DashboardResponse(
                analysis_id="test-analysis-001",
                project_name="TestProject",
                total_jobs=0,
                total_components=0,
                critical_issues=0,
                kpis=[],
                severity_summary={},
                charts=DashboardChartData(),
            )
        )
        agent = DashboardAgent(
            aggregator=mock_aggregator,
            security_rule_engine=mock_rule_engine,
            performance_rule_engine=mock_rule_engine,
        )
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "dashboard-response"

    async def test_execute_calls_aggregator(self, agent_context, mock_rule_engine):
        mock_aggregator = MagicMock()
        mock_aggregator.aggregate = MagicMock(
            return_value=DashboardResponse(
                analysis_id="test-analysis-001",
                project_name="TestProject",
                total_jobs=0,
                total_components=0,
                critical_issues=0,
                kpis=[],
                severity_summary={},
                charts=DashboardChartData(),
            )
        )
        agent = DashboardAgent(
            aggregator=mock_aggregator,
            security_rule_engine=mock_rule_engine,
            performance_rule_engine=mock_rule_engine,
        )
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_aggregator.aggregate.assert_called_once()

    async def test_execute_returns_metrics(self, agent_context, mock_rule_engine):
        mock_aggregator = MagicMock()
        mock_aggregator.aggregate = MagicMock(
            return_value=DashboardResponse(
                analysis_id="test-analysis-001",
                project_name="TestProject",
                total_jobs=5,
                total_components=20,
                critical_issues=1,
                kpis=[],
                severity_summary={},
                charts=DashboardChartData(),
            )
        )
        agent = DashboardAgent(
            aggregator=mock_aggregator,
            security_rule_engine=mock_rule_engine,
            performance_rule_engine=mock_rule_engine,
        )
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert "dashboard_views_prepared" in result.metrics
        assert result.metrics["total_jobs"] == 5
        assert result.metrics["critical_issues"] == 1

    async def test_standardize_context_findings(self, agent_context, mock_rule_engine, sample_finding):
        mock_aggregator = MagicMock()
        mock_aggregator.aggregate = MagicMock(
            return_value=DashboardResponse(
                analysis_id="test-analysis-001",
                project_name="TestProject",
                total_jobs=0,
                total_components=0,
                critical_issues=0,
                kpis=[],
                severity_summary={},
                charts=DashboardChartData(),
            )
        )
        agent = DashboardAgent(
            aggregator=mock_aggregator,
            security_rule_engine=mock_rule_engine,
            performance_rule_engine=mock_rule_engine,
        )
        payload = {
            "security_findings": [sample_finding.model_dump(mode="json")],
            "performance_findings": [],
        }
        result = agent._standardize_context_findings(payload)
        assert "security_findings" in result
        assert isinstance(result["security_findings"], list)

    async def test_build_context_payload(self, agent_context, mock_rule_engine):
        mock_aggregator = MagicMock()
        agent = DashboardAgent(
            aggregator=mock_aggregator,
            security_rule_engine=mock_rule_engine,
            performance_rule_engine=mock_rule_engine,
        )
        payload = agent._build_context_payload(agent_context)
        assert payload["analysis_id"] == "test-analysis-001"
        assert "talend_inventory" in payload
        assert "security_findings" in payload

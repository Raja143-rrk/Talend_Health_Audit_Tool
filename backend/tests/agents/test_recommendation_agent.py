from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents.recommendation_agent.agent import RecommendationAgent
from backend.agents.recommendation_agent.models import (
    CategorizedSuggestion,
    RecommendationCategory,
    RecommendationSummary,
)
from backend.shared.models import AgentResponse, AgentStatus


class TestRecommendationAgent:
    async def test_execute_returns_completed_response(self, agent_context):
        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(
            return_value=RecommendationSummary(
                executive_summary="Test",
                risk_posture="low",
                suggestions=[
                    CategorizedSuggestion(
                        id="REC-001",
                        category=RecommendationCategory.BEST_PRACTICE,
                        title="Test",
                        priority="P3",
                        summary="Test summary",
                        rationale="Test rationale",
                        action_items=["Do something"],
                        expected_impact="Good impact",
                    )
                ],
            )
        )
        mock_retriever = MagicMock()
        mock_retriever.retrieve_context = MagicMock(
            return_value=MagicMock(
                query="test",
                results=[],
                context_text="",
                backend="memory",
            )
        )
        agent = RecommendationAgent(generator=mock_generator, retriever=mock_retriever)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert isinstance(result, AgentResponse)
        assert result.status == AgentStatus.COMPLETED

    async def test_execute_includes_artifact(self, agent_context):
        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(
            return_value=RecommendationSummary(
                executive_summary="Test",
                risk_posture="low",
                suggestions=[
                    CategorizedSuggestion(
                        id="REC-001",
                        category=RecommendationCategory.BEST_PRACTICE,
                        title="Test",
                        priority="P3",
                        summary="Test summary",
                        rationale="Test rationale",
                        action_items=["Do something"],
                        expected_impact="Good impact",
                    )
                ],
            )
        )
        mock_retriever = MagicMock()
        mock_retriever.retrieve_context = MagicMock(
            return_value=MagicMock(
                query="test",
                results=[],
                context_text="",
                backend="memory",
            )
        )
        agent = RecommendationAgent(generator=mock_generator, retriever=mock_retriever)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "ai-recommendation-summary"

    async def test_execute_calls_generator(self, agent_context):
        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(
            return_value=RecommendationSummary(
                executive_summary="Test",
                risk_posture="low",
                suggestions=[],
            )
        )
        mock_retriever = MagicMock()
        mock_retriever.retrieve_context = MagicMock(
            return_value=MagicMock(
                query="test",
                results=[],
                context_text="",
                backend="memory",
            )
        )
        agent = RecommendationAgent(generator=mock_generator, retriever=mock_retriever)
        started_at = datetime.now(timezone.utc)
        await agent.execute(agent_context, started_at)
        mock_generator.generate.assert_called_once()
        mock_retriever.retrieve_context.assert_called()

    async def test_execute_returns_metrics(self, agent_context):
        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(
            return_value=RecommendationSummary(
                executive_summary="Test",
                risk_posture="low",
                suggestions=[
                    CategorizedSuggestion(
                        id="REC-001",
                        category=RecommendationCategory.BEST_PRACTICE,
                        title="Test",
                        priority="P3",
                        summary="Test summary",
                        rationale="Test rationale",
                        action_items=["Do something"],
                        expected_impact="Good impact",
                    )
                ],
            )
        )
        mock_retriever = MagicMock()
        mock_retriever.retrieve_context = MagicMock(
            return_value=MagicMock(
                query="test",
                results=[],
                context_text="",
                backend="memory",
            )
        )
        agent = RecommendationAgent(generator=mock_generator, retriever=mock_retriever)
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(agent_context, started_at)
        assert "recommendations_generated" in result.metrics
        assert result.metrics["rag_queries"] >= 0

    async def test_execute_without_findings(self, agent_context):
        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(
            return_value=RecommendationSummary(
                executive_summary="Test",
                risk_posture="low",
                suggestions=[],
            )
        )
        mock_retriever = MagicMock()
        mock_retriever.retrieve_context = MagicMock(
            return_value=MagicMock(
                query="test",
                results=[],
                context_text="",
                backend="memory",
            )
        )
        agent = RecommendationAgent(generator=mock_generator, retriever=mock_retriever)
        context = MagicMock()
        context.metadata = {}
        context.analysis_id = "test"
        context.project_name = "Test"
        started_at = datetime.now(timezone.utc)
        result = await agent.execute(context, started_at)
        assert result.status == AgentStatus.COMPLETED

    async def test_build_context_payload(self, agent_context):
        mock_generator = MagicMock()
        mock_retriever = MagicMock()
        agent = RecommendationAgent(generator=mock_generator, retriever=mock_retriever)
        payload = agent._build_context_payload(agent_context)
        assert "project_name" in payload
        assert "talend_inventory" in payload
        assert "disabled_components" in payload

    async def test_build_retrieval_queries(self):
        mock_generator = MagicMock()
        mock_retriever = MagicMock()
        agent = RecommendationAgent(generator=mock_generator, retriever=mock_retriever)
        payload = {
            "security_findings": [{"category": "secrets"}],
            "performance_findings": [{"category": "tmap"}],
            "talend_inventory": {
                "components": [{"component_name": "tJDBCConnection"}],
                "jobs": [{"components": [{"component_name": "tMap"}]}],
            },
        }
        queries = agent._build_retrieval_queries(payload)
        assert len(queries) >= 2
        assert any("secrets" in q for q in queries)

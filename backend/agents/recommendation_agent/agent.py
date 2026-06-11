from datetime import datetime
import asyncio

from backend.agents.base import BaseAgent
from backend.agents.recommendation_agent.generator import RecommendationGenerator
from backend.rag import RagRetriever, RetrievalContext
from backend.shared.models import (
    AgentArtifact,
    AgentContext,
    AgentResponse,
    AgentRecommendation,
)


class RecommendationAgent(BaseAgent):
    name = "recommendation-agent"
    description = "Generates prioritized remediation guidance from findings."

    def __init__(
        self,
        generator: RecommendationGenerator | None = None,
        retriever: RagRetriever | None = None,
    ) -> None:
        super().__init__()
        self.generator = generator or RecommendationGenerator()
        self.retriever = retriever or RagRetriever()

    async def execute(
        self,
        context: AgentContext,
        started_at: datetime,
    ) -> AgentResponse:
        context_payload = self._build_context_payload(context)
        retrieval_contexts = await self._retrieve_guidance(context_payload)
        context_payload["retrieval_contexts"] = [
            retrieval_context.model_dump(mode="json")
            for retrieval_context in retrieval_contexts
        ]
        summary = await self.generator.generate(context_payload)
        disabled_components = context_payload.get("disabled_components", [])
        recommendations = await asyncio.to_thread(
            self._to_agent_recommendations, summary, disabled_components
        )

        self.logger.info(
            "Generated %s AI recommendations for analysis %s",
            len(recommendations),
            context.analysis_id,
        )

        return AgentResponse.completed(
            agent_name=self.name,
            started_at=started_at,
            artifacts=[
                AgentArtifact(
                    name="ai-recommendation-summary",
                    artifact_type="recommendation-report",
                    payload={
                        **summary.model_dump(mode="json"),
                        "retrieval_contexts": [
                            retrieval_context.model_dump(mode="json")
                            for retrieval_context in retrieval_contexts
                        ],
                    },
                )
            ],
            recommendations=recommendations,
            metrics={
                "recommendations_generated": len(recommendations),
                "rag_queries": len(retrieval_contexts),
                "rag_documents_retrieved": sum(
                    len(retrieval_context.results)
                    for retrieval_context in retrieval_contexts
                ),
                "recommendation_categories": sorted(
                    {suggestion.category.value for suggestion in summary.suggestions}
                ),
                "risk_posture": summary.risk_posture,
            },
        )

    def _build_context_payload(self, context: AgentContext) -> dict:
        inventory = context.metadata.get("talend_inventory", {})
        return {
            "project_name": context.project_name,
            "talend_inventory": inventory,
            "disabled_components": inventory.get("disabled_components", []),
            "security_findings": context.metadata.get("security_findings", []),
            "performance_findings": context.metadata.get("performance_findings", []),
            "existing_recommendations": context.metadata.get("existing_recommendations", []),
        }

    async def _retrieve_guidance(self, context_payload: dict) -> list[RetrievalContext]:
        queries = self._build_retrieval_queries(context_payload)
        retrieval_tasks = [
            asyncio.to_thread(self.retriever.retrieve_context, query, 4)
            for query in queries
        ]
        if not retrieval_tasks:
            return []

        results = await asyncio.gather(*retrieval_tasks, return_exceptions=True)
        retrieval_contexts: list[RetrievalContext] = []
        for result in results:
            if isinstance(result, RetrievalContext):
                retrieval_contexts.append(result)
            elif isinstance(result, Exception):
                self.logger.warning("RAG retrieval failed: %s", result)
        return retrieval_contexts

    def _build_retrieval_queries(self, context_payload: dict) -> list[str]:
        security_findings = context_payload.get("security_findings", [])
        performance_findings = context_payload.get("performance_findings", [])
        inventory = context_payload.get("talend_inventory", {})
        query_parts = [
            "Talend best practices contexts metadata connections error handling",
            "Talend optimization guidance tMap commit size row processing custom Java",
        ]

        security_categories = self._finding_categories(security_findings)
        if security_categories:
            query_parts.append(
                "Talend security remediation "
                + " ".join(sorted(security_categories))
                + " secrets JDBC credentials vault contexts"
            )

        performance_categories = self._finding_categories(performance_findings)
        if performance_categories:
            query_parts.append(
                "Talend performance optimization "
                + " ".join(sorted(performance_categories))
                + " throughput batch commit tMap pushdown"
            )

        component_names = self._component_names(inventory)
        if component_names:
            query_parts.append(
                "Talend optimization best practices for components "
                + " ".join(component_names[:10])
            )

        return list(dict.fromkeys(query_parts))

    def _finding_categories(self, findings: list[dict]) -> set[str]:
        return {
            str(finding.get("category"))
            for finding in findings
            if finding.get("category")
        }

    def _component_names(self, inventory: dict) -> list[str]:
        if not isinstance(inventory, dict):
            return []

        names: list[str] = []
        for component in inventory.get("components", []):
            component_name = component.get("component_name")
            if component_name:
                names.append(str(component_name))

        for job in inventory.get("jobs", []):
            for component in job.get("components", []):
                component_name = component.get("component_name")
                if component_name:
                    names.append(str(component_name))

        return sorted(dict.fromkeys(names))

    def _to_agent_recommendations(
        self,
        summary,
        disabled_components: list[dict] | None = None,
    ) -> list[AgentRecommendation]:
        recommendations: list[AgentRecommendation] = []
        for suggestion in summary.suggestions:
            if suggestion.category.value == "cleanup":
                component_types = sorted(
                    {
                        str(c.get("component_name") or c.get("name", "unknown"))
                        for c in (disabled_components or [])
                    }
                )
                count = len(disabled_components or [])
                type_hint = ", ".join(component_types[:5])
                if len(component_types) > 5:
                    type_hint += f" +{len(component_types) - 5} more"
                group_title = (
                    f"Disabled component(s) — {type_hint}"
                    if component_types
                    else suggestion.title
                )
                recommendations.append(
                    AgentRecommendation(
                        id=suggestion.id,
                        title=group_title,
                        priority=suggestion.priority,
                        category=suggestion.category.value,
                        component_name=f"{count} disabled",
                        component_type="cleanup",
                        rationale=suggestion.rationale,
                        action=" ".join(suggestion.action_items) or suggestion.summary,
                        expected_impact=suggestion.expected_impact,
                    )
                )
        return recommendations

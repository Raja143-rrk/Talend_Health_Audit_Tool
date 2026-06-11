import json
import os
from typing import Any

from backend.rag.documents import RetrievalContext
from backend.agents.recommendation_agent.models import (
    CategorizedSuggestion,
    RecommendationCategory,
    RecommendationSummary,
)
from backend.agents.recommendation_agent.prompts import (
    RECOMMENDATION_SYSTEM_PROMPT,
    RECOMMENDATION_USER_PROMPT,
)


class RecommendationGenerator:
    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> None:
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.temperature = temperature

    async def generate(self, context_payload: dict[str, Any]) -> RecommendationSummary:
        if self._llm_enabled():
            try:
                return await self._generate_with_langchain(context_payload)
            except Exception:
                return self._generate_fallback(context_payload)

        return self._generate_fallback(context_payload)

    def _llm_enabled(self) -> bool:
        return bool(os.getenv("GROQ_API_KEY"))

    async def _generate_with_langchain(
        self,
        context_payload: dict[str, Any],
    ) -> RecommendationSummary:
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("LangChain OpenAI packages are not installed.") from exc

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", RECOMMENDATION_SYSTEM_PROMPT),
                ("user", RECOMMENDATION_USER_PROMPT),
            ]
        )
        llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            base_url=os.getenv("GROQ_API_BASE_URL"),
        )
        structured_llm = llm.with_structured_output(RecommendationSummary)
        chain = prompt | structured_llm
        result = await chain.ainvoke(self._prompt_variables(context_payload))

        if isinstance(result, RecommendationSummary):
            return result

        if isinstance(result, dict):
            return RecommendationSummary.model_validate(result)

        raise TypeError(f"Unexpected recommendation response type: {type(result)!r}")

    def _generate_fallback(self, context_payload: dict[str, Any]) -> RecommendationSummary:
        security_findings = context_payload.get("security_findings", [])
        performance_findings = context_payload.get("performance_findings", [])
        inventory = context_payload.get("talend_inventory", {})
        disabled_components = context_payload.get("disabled_components", [])
        retrieval_contexts = self._retrieval_contexts(context_payload)
        jobs_count = len(inventory.get("jobs", [])) if isinstance(inventory, dict) else 0
        best_practice_context = self._context_excerpt(retrieval_contexts, "best")
        optimization_context = self._context_excerpt(retrieval_contexts, "optimization")
        remediation_context = self._context_excerpt(retrieval_contexts, "security")

        disabled_jobs = sorted(
            {str(c.get("job")) for c in disabled_components if c.get("job")}
        )
        disabled_names = sorted(
            {str(c.get("component_name") or c.get("name", "unknown")) for c in disabled_components}
        )

        suggestions = [
            CategorizedSuggestion(
                id="AI-REC-001",
                category=RecommendationCategory.REMEDIATION,
                title="Prioritize critical security remediation",
                priority="P1",
                summary="Resolve hardcoded credentials, API keys, tokens, and JDBC exposure before production promotion.",
                rationale=(
                    f"{len(security_findings)} security findings were supplied for recommendation generation. "
                    f"Retrieved guidance: {remediation_context}"
                ),
                action_items=[
                    "Move secrets into a managed vault or encrypted Talend contexts.",
                    "Rotate exposed credentials and tokens.",
                    "Replace inline JDBC strings with governed metadata connections.",
                ],
                expected_impact="Reduces credential exposure and improves audit readiness.",
            ),
            CategorizedSuggestion(
                id="AI-REC-002",
                category=RecommendationCategory.OPTIMIZATION,
                title="Address high-cost job design patterns",
                priority="P2",
                summary="Reduce row-level custom code, nested loops, small commits, and heavy tMap usage.",
                rationale=(
                    f"{len(performance_findings)} performance findings were supplied for optimization guidance. "
                    f"Retrieved guidance: {optimization_context}"
                ),
                action_items=[
                    "Replace repeated tJava logic with native Talend components.",
                    "Push joins, filters, and aggregations closer to source systems.",
                    "Tune commit and batch sizes for bulk loads.",
                ],
                expected_impact="Improves throughput, maintainability, and runtime predictability.",
            ),
            CategorizedSuggestion(
                id="AI-REC-003",
                category=RecommendationCategory.BEST_PRACTICE,
                title="Standardize reusable Talend engineering patterns",
                priority="P3",
                summary="Create shared conventions for contexts, metadata connections, naming, logging, and error handling.",
                rationale=(
                    f"The parsed inventory includes {jobs_count} jobs that can benefit from consistent standards. "
                    f"Retrieved guidance: {best_practice_context}"
                ),
                action_items=[
                    "Define environment-specific context groups.",
                    "Centralize connection metadata.",
                    "Add common logging and reject-flow handling to critical jobs.",
                ],
                expected_impact="Improves operational consistency and reduces support effort.",
            ),
            CategorizedSuggestion(
                id="AI-REC-004",
                category=RecommendationCategory.MODERNIZATION,
                title="Modernize legacy Talend workloads incrementally",
                priority="P3",
                summary="Identify candidates for cloud-native orchestration, CI/CD, and managed data platform patterns.",
                rationale="Modernization should focus first on high-risk or high-change jobs.",
                action_items=[
                    "Rank jobs by business criticality, runtime cost, and defect history.",
                    "Introduce automated validation for exported Talend artifacts.",
                    "Evaluate migration of batch-heavy flows to scalable cloud execution patterns.",
                ],
                expected_impact="Creates a low-risk modernization roadmap with measurable migration value.",
            ),
        ]

        if disabled_components:
            suggestions.append(
                CategorizedSuggestion(
                    id="AI-REC-005",
                    category=RecommendationCategory.CLEANUP,
                    title="Remove unused disabled components from job designs",
                    priority="P3",
                    summary=(
                        f"{len(disabled_components)} disabled component(s) remain in the workspace. "
                        "These components serve no runtime function and add unnecessary complexity."
                    ),
                    rationale=(
                        f"Disabled components found: {', '.join(disabled_names[:8])}"
                        f"{' and more' if len(disabled_names) > 8 else ''}. "
                        f"Affected job(s): {', '.join(disabled_jobs[:5]) or 'various jobs'}. "
                        "Deleting obsolete components reduces maintenance overhead, "
                        "simplifies code reviews, and eliminates confusion during debugging."
                    ),
                    action_items=[
                        "Review each disabled component and confirm it is no longer needed.",
                        "Delete disabled components from the job design rather than keeping them disabled.",
                        "Document any intentionally retained disabled components with a comment or context variable.",
                        "Run a full job export and validate that removal does not break dependencies.",
                    ],
                    expected_impact="Cleaner job designs, reduced technical debt, and simpler ongoing maintenance.",
                )
            )

        return RecommendationSummary(
            executive_summary="The recommendation set prioritizes security remediation first, then runtime optimization, engineering best practices, incremental modernization, and cleanup of disabled components."
            if disabled_components
            else "The recommendation set prioritizes security remediation first, then runtime optimization, engineering best practices, and incremental modernization.",
            risk_posture=self._risk_posture(security_findings, performance_findings),
            suggestions=suggestions,
        )

    def _risk_posture(
        self,
        security_findings: list[dict[str, Any]],
        performance_findings: list[dict[str, Any]],
    ) -> str:
        critical_count = sum(
            1
            for finding in [*security_findings, *performance_findings]
            if str(finding.get("severity", "")).lower() in {"critical_risk", "risk"}
        )
        if critical_count:
            return "high"
        if security_findings or performance_findings:
            return "medium"
        return "low"

    def _prompt_variables(self, context_payload: dict[str, Any]) -> dict[str, str]:
        return {
            "project_name": str(context_payload.get("project_name", "Talend Health Analyzer")),
            "inventory_summary": self._compact_json(context_payload.get("talend_inventory", {})),
            "disabled_components": self._compact_json(context_payload.get("disabled_components", [])),
            "security_findings": self._compact_json(context_payload.get("security_findings", [])),
            "performance_findings": self._compact_json(context_payload.get("performance_findings", [])),
            "retrieved_guidance": self._format_retrieved_guidance(context_payload),
            "existing_recommendations": self._compact_json(
                context_payload.get("existing_recommendations", [])
            ),
        }

    def _compact_json(self, value: Any) -> str:
        return json.dumps(value, default=str, ensure_ascii=True)[:12000]

    def _format_retrieved_guidance(self, context_payload: dict[str, Any]) -> str:
        contexts = self._retrieval_contexts(context_payload)
        if not contexts:
            return "No retrieved guidance was supplied."

        return "\n\n".join(
            f"Query: {context.query}\n{context.context_text}"
            for context in contexts
            if context.context_text
        )[:12000]

    def _retrieval_contexts(self, context_payload: dict[str, Any]) -> list[RetrievalContext]:
        raw_contexts = context_payload.get("retrieval_contexts", [])
        contexts: list[RetrievalContext] = []
        for raw_context in raw_contexts:
            if isinstance(raw_context, RetrievalContext):
                contexts.append(raw_context)
                continue
            if isinstance(raw_context, dict):
                try:
                    contexts.append(RetrievalContext.model_validate(raw_context))
                except Exception:
                    continue
        return contexts

    def _context_excerpt(
        self,
        contexts: list[RetrievalContext],
        keyword: str,
    ) -> str:
        for context in contexts:
            if keyword.lower() in context.query.lower() and context.context_text:
                return context.context_text[:500]
        for context in contexts:
            if context.context_text:
                return context.context_text[:500]
        return "No matching guidance was retrieved."

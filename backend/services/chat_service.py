import asyncio
import json
import os
import re
from typing import Any, TypedDict

from backend.agents.dashboard_agent.scoring import get_scoring_config_data
from backend.rag import RagRetriever
from backend.rag.registry import lookup_rule, get_registered_rule_ids
from backend.schemas.chat import (
    ChatMessage,
    DashboardChatAction,
    DashboardChatRequest,
    DashboardChatResponse,
    DashboardChatSource,
)
from backend.services.dashboard_service import dashboard_service

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - exercised only when dependency is absent.
    END = START = None
    StateGraph = None

class ChatGraphState(TypedDict, total=False):
    request: DashboardChatRequest
    dashboard: dict[str, Any]
    query_terms: list[str]
    intent: str
    matches: dict[str, list[dict[str, Any]]]
    rag_context: Any
    rag_context_text: str
    rag_entries: list[dict[str, Any]]
    answer: str
    actions: list[DashboardChatAction]
    sources: list[DashboardChatSource]


class DashboardChatService:
    """Enterprise-grade chat agent over completed dashboard data and Talend RAG guidance."""

    def __init__(self, retriever: RagRetriever | None = None) -> None:
        self.retriever = retriever or RagRetriever()
        self._graph = self._build_graph()

    async def chat(self, request: DashboardChatRequest) -> DashboardChatResponse:
        state: ChatGraphState = {"request": request}
        if self._graph is not None:
            result = await self._graph.ainvoke(state)
        else:
            result = await self._run_direct(state)
        matches = result.get("matches", {})
        return DashboardChatResponse(
            analysis_id=request.analysis_id,
            answer=result.get("answer", ""),
            actions=result.get("actions", []),
            sources=result.get("sources", []),
            matched_counts={key: len(value) for key, value in matches.items()},
        )

    def _build_graph(self):
        if StateGraph is None:
            return None

        graph = StateGraph(ChatGraphState)
        graph.add_node("load_dashboard", self._load_dashboard)
        graph.add_node("understand_query", self._understand_query)
        graph.add_node("retrieve_guidance", self._retrieve_guidance)
        graph.add_node("answer", self._answer)
        graph.add_edge(START, "load_dashboard")
        graph.add_edge("load_dashboard", "understand_query")
        graph.add_edge("understand_query", "retrieve_guidance")
        graph.add_edge("retrieve_guidance", "answer")
        graph.add_edge("answer", END)
        return graph.compile()

    async def _run_direct(self, state: ChatGraphState) -> ChatGraphState:
        for step in (
            self._load_dashboard,
            self._understand_query,
            self._retrieve_guidance,
            self._answer,
        ):
            state = await step(state)
        return state

    async def _load_dashboard(self, state: ChatGraphState) -> ChatGraphState:
        request = state["request"]
        overview = await asyncio.to_thread(
            dashboard_service.get_dashboard_overview, request.analysis_id
        )
        state["dashboard"] = overview.model_dump(mode="json")
        return state


    async def _understand_query(self, state: ChatGraphState) -> ChatGraphState:
        message = state["request"].message
        dashboard = state["dashboard"]
        terms = self._query_terms(message)
        state["query_terms"] = terms
        state["intent"] = self._classify_intent(message)
        state["matches"] = {
            "findings": self._match_records(
                [
                    *dashboard["security_findings"]["items"],
                    *dashboard["performance_findings"]["items"],
                ],
                terms,
                message,
            ),
            "recommendations": self._match_records(
                dashboard["recommendations"]["items"],
                terms,
                message,
            ),
            "components": self._match_records(
                dashboard.get("component_drilldown", []),
                terms,
                message,
            ),
        }
        return state

    async def _retrieve_guidance(self, state: ChatGraphState) -> ChatGraphState:
        request = state["request"]
        rag_context = await asyncio.to_thread(
            self.retriever.retrieve_context, request.message, limit=5
        )
        state["rag_context"] = rag_context
        state["rag_context_text"] = rag_context.context_text
        state["sources"] = [
            DashboardChatSource(
                title=result.document.id,
                source=result.document.source,
                snippet=result.document.content,
            )
            for result in rag_context.results
        ]
        matched_rule_ids: set[str] = set()
        for category in ("findings", "recommendations"):
            for item in state.get("matches", {}).get(category, []):
                rid = str(item.get("rule_triggered") or item.get("evidence", {}).get("rule_id") or "")
                if rid:
                    matched_rule_ids.add(rid)
        state["rag_entries"] = [
            entry for rid in matched_rule_ids
            if (entry := lookup_rule(rid))
        ]
        return state

    async def _answer(self, state: ChatGraphState) -> ChatGraphState:
        if state.get("intent") == "unknown":
            state["answer"], state["actions"] = self._deterministic_answer(state)
            return state
        state["answer"], state["actions"] = await self._llm_answer(state)
        if not state["answer"]:
            fallback_answer, actions = self._deterministic_answer(state)
            state["answer"] = fallback_answer
            state["actions"] = actions
        return state

    async def _llm_answer(self, state: ChatGraphState) -> tuple[str, list[DashboardChatAction]]:
        if not os.getenv("GROQ_API_KEY"):
            return "", []

        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            return "", []

        dashboard = state["dashboard"]
        matches = state["matches"]
        intent = state["intent"]
        all_security = dashboard.get("security_findings", {}).get("items", [])
        all_performance = dashboard.get("performance_findings", {}).get("items", [])
        all_recommendations = dashboard.get("recommendations", {}).get("items", [])
        all_components = dashboard.get("component_drilldown", [])
        summary = dashboard["summary"]
        metrics = summary.get("metrics", [])

        def mv(label: str) -> int:
            for m in metrics:
                if m.get("label") == label:
                    return int(m.get("value", 0))
            return 0

        rule_id_refs = ""
        matched_rule_ids: set[str] = set()
        for item in [*matches["findings"], *matches["recommendations"]]:
            rid = str(item.get("rule_triggered") or item.get("evidence", {}).get("rule_id") or "")
            if rid:
                matched_rule_ids.add(rid)
        if matched_rule_ids:
            refs = []
            for rid in sorted(matched_rule_ids):
                entry = lookup_rule(rid)
                if entry:
                    refs.append(f"- **{rid}**: {entry.get('title', '')} — {entry.get('remediation', '')[:120]}")
            if refs:
                rule_id_refs = "\n\n**Matched RAG Rules & Remediation:**\n" + "\n".join(refs)

        compact_context = {
            "intent": intent,
            "project_name": summary.get("project_name", "Unknown"),
            "health_score": summary.get("health_score"),
            "health_grade": summary.get("health_grade") or summary.get("risk_level"),
            "metrics": {
                "total_jobs": mv("Total Jobs"),
                "active_components": mv("Total Components"),
                "disabled_components": mv("Disabled Components"),
                "critical_issues": mv("Critical Issues"),
            },
            "charts": {
                "active_component_distribution": dashboard.get("charts", {}).get("active_component_distribution", []),
                "disabled_component_distribution": dashboard.get("charts", {}).get("disabled_component_distribution", []),
                "source_target_systems": dashboard.get("charts", {}).get("source_target_systems", []),
            },
            "data_totals": {
                "total_security_findings": len(all_security),
                "total_performance_findings": len(all_performance),
                "total_recommendations": len(all_recommendations),
                "components_with_findings": len(all_components),
                "severity_breakdown": {
                    "security": self._severity_counts(all_security),
                    "performance": self._severity_counts(all_performance),
                },
            },
            "security_findings": all_security[:10],
            "performance_findings": all_performance[:10],
            "recommendations": all_recommendations[:10],
            "component_drilldown": [
                {
                    "job_name": c.get("job_name"),
                    "component_name": c.get("component_name"),
                    "component_type": c.get("component_type"),
                    "finding_count": len(c.get("findings", [])),
                }
                for c in all_components[:15]
            ],
            "matched_findings": matches["findings"][:5],
            "matched_recommendations": matches["recommendations"][:5],
            "rag_context": state.get("rag_context_text", ""),
        }
        history = "\n".join(
            f"{message.role}: {message.content}"
            for message in state["request"].history[-6:]
            if isinstance(message, ChatMessage)
        )
        prompt = (
            "You are Talend Health Analyzer, an enterprise AI assistant for Talend job health analysis.\n\n"
            "## RAG Knowledge Base\n"
            "You have access to a Talend RAG knowledge base containing best practices, findings rules, "
            "and remediation steps. Use this knowledge to:\n"
            "- Explain **why** each finding matters using Talend best practices.\n"
            "- Provide **specific remediation steps** from the knowledge base.\n"
            "- Reference **matching rule IDs** (e.g., RULE-SEC-001, RULE-PERF-002) in your explanations.\n\n"
            "## Guardrails\n"
            "- Answer ONLY using the dashboard data and RAG context provided below.\n"
            "- NEVER invent findings, recommendations, rule IDs, or remediation steps not present in the provided data.\n"
            "- NEVER generate severity explanations from your own knowledge. Use only the RAG classification and impact fields provided in the data.\n"
            "- NEVER generate unsupported recommendations. If the data doesn't contain the answer, say so.\n"
            "- If no matching RAG context is available for a topic, say \"I don't have specific guidance on that in my knowledge base.\"\n"
            "- PAY CLOSE ATTENTION to what the user specifically asked about. If they ask about "
            "'disabled components', check the disabled_components metric. If it is 0, say there are "
            "no disabled components — do NOT show unrelated recommendations. "
            "If they ask about 'security findings', only show security data. "
            "If they ask about 'performance findings', only show performance data.\n"
            "- If the data contains the answer, give a clear, structured response with metrics.\n"
            "- Use bullet points, bold numbers, and short paragraphs for readability.\n"
            "- Be conversational but professional — talk like a senior engineer.\n"
            "- When totals are mentioned, include a breakdown.\n"
            "- Keep responses concise but complete.\n\n"
            f"Conversation history:\n{history or 'None'}\n\n"
            f"User question:\n{state['request'].message}\n\n"
            f"Dashboard data:\n{json.dumps(compact_context, ensure_ascii=True)[:20000]}"
            f"{rule_id_refs}"
        )
        response = await ChatOpenAI(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0,
            base_url=os.getenv("GROQ_API_BASE_URL"),
        ).ainvoke(prompt)
        content = str(getattr(response, "content", "")).strip()
        if not content:
            return "", []
        actions = self._actions_for(state)
        return content, actions

    def _deterministic_answer(
        self,
        state: ChatGraphState,
    ) -> tuple[str, list[DashboardChatAction]]:
        dashboard = state["dashboard"]
        summary = dashboard["summary"]
        matches = state["matches"]
        intent = state["intent"]
        all_findings = [
            *dashboard["security_findings"]["items"],
            *dashboard["performance_findings"]["items"],
        ]
        message = state["request"].message.lower()
        has_filter = any(term in message for term in ("disabled", "critical_risk", "critical risk", "risk", "warning", "advisory", "informational", "security", "performance", "specific"))
        findings = matches["findings"] if matches["findings"] or has_filter else all_findings
        recommendations = matches["recommendations"] if matches["recommendations"] or has_filter else dashboard["recommendations"]["items"]
        components = matches["components"] if matches["components"] or has_filter else dashboard.get("component_drilldown", [])
        actions = self._actions_for(state)

        if intent == "greeting":
            return self._greeting_answer(dashboard), actions
        if intent == "formula":
            return self._formula_answer(dashboard, findings), actions
        if intent == "data_sources":
            return self._data_sources_answer(), actions
        if intent == "metrics_kpis":
            return self._metrics_kpis_answer(dashboard), actions
        if intent == "rule_engine":
            return self._rule_engine_answer(), actions
        if intent == "recommendation_engine":
            return self._recommendation_engine_answer(), actions
        if intent == "pipeline":
            return self._pipeline_answer(), actions
        if intent == "component_classification":
            return self._component_classification_answer(), actions
        if intent == "health_score":
            return self._compliance_answer(dashboard, findings), actions
        if intent == "risk_summary":
            return self._compliance_answer(dashboard, findings), actions
        if intent == "component_count":
            return self._component_count_answer(dashboard), actions
        if intent == "component_details":
            return self._component_answer(components), actions
        if intent == "job_names":
            return self._job_names_answer(dashboard), actions
        if intent == "recommendations":
            return self._recommendation_answer(recommendations), actions
        if intent == "risk_summary":
            return self._risk_answer(dashboard, findings), actions
        if intent == "filter":
            return self._filter_answer(findings, recommendations, components), actions
        if intent == "findings":
            return self._findings_answer(findings, state), actions
        if intent == "capabilities":
            return self._capabilities_answer(dashboard), actions
        if intent == "section_info":
            return self._section_answer(dashboard, state["request"].message), actions
        if intent == "sell_tool":
            return self._sell_tool_answer(), actions
        if intent == "tool_use":
            return self._tool_use_answer(), actions
        if intent == "unknown":
            return self._unknown_answer(), actions
        return self._overview_answer(dashboard), actions

    def _finding_rag_explanation(self, finding: dict[str, Any]) -> str:
        rule_id = str(finding.get("rule_triggered") or finding.get("evidence", {}).get("rule_id") or "")
        entry = lookup_rule(rule_id) if rule_id else None
        if not entry:
            return ""
        parts: list[str] = []
        detection = entry.get("detection_logic") or ""
        if detection:
            parts.append(f"Why: {detection[:200]}")
        impact = entry.get("impact") or ""
        if impact:
            parts.append(f"Impact: {impact[:200]}")
        remediation = entry.get("remediation") or ""
        if remediation:
            parts.append(f"Fix: {remediation[:200]}")
        if parts:
            return f" (Rule **{rule_id}** — {' | '.join(parts)})"
        return f" (See **{rule_id}** in the RAG knowledge base for details)"

    def _rag_best_practices_block(self, state: ChatGraphState) -> str:
        entries = state.get("rag_entries", [])
        if not entries:
            return ""
        parts = ["\n\n**RAG Knowledge Base Guidance:**"]
        for entry in entries:
            title = entry.get("title", entry.get("rule_id", "Guidance"))
            detection = entry.get("detection_logic") or entry.get("description", "")
            impact = entry.get("impact") or ""
            remediation = entry.get("remediation") or ""
            line = f"- **{title}**: Why: {detection[:120]} | Impact: {impact[:120]} | Fix: {remediation[:120]}"
            parts.append(line)
        return "\n".join(parts)

    def _metric_value(self, metrics: list[dict[str, Any]], label: str) -> int:
        for m in metrics:
            if m.get("label") == label:
                return int(m.get("value", 0))
        return 0

    def _severity_counts(self, items: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            sev = str(item.get("severity") or "informational").lower()
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def _greeting_answer(self, dashboard: dict[str, Any]) -> str:
        summary = dashboard["summary"]
        metrics = summary.get("metrics", [])
        project = summary.get("project_name", "your project")
        total_jobs = self._metric_value(metrics, "Total Jobs")
        total_components = self._metric_value(metrics, "Total Components")
        compliance_score = summary.get("compliance_score", 100)
        compliance_grade = summary.get("compliance_grade", "Optimized")
        return (
            f"Hi there! 👋 Welcome to the Talend Health Analyzer for **{project}**.\n\n"
            f"Right now I can see you have **{total_jobs} job(s)** with **{total_components} active components**.\n\n"
            f"**Compliance Score**: **{compliance_score}%** — **{compliance_grade}**\n\n"
            f"Here's what I can help you with:\n"
            f"- **Compliance Score** — detailed compliance breakdown by category\n"
            f"- **Components** — active vs disabled component inventory\n"
            f"- **Findings** — security and performance issues\n"
            f"- **Recommendations** — prioritized action items\n"
            f"- **Risks** — overall risk assessment\n\n"
            f"What would you like to explore?"
        )

    def _capabilities_answer(self, dashboard: dict[str, Any]) -> str:
        summary = dashboard["summary"]
        metrics = summary.get("metrics", [])
        project = summary.get("project_name", "your project")
        total_jobs = self._metric_value(metrics, "Total Jobs")
        total_components = self._metric_value(metrics, "Total Components")
        disabled_components = self._metric_value(metrics, "Disabled Components")
        sec_total = dashboard.get("security_findings", {}).get("total", 0)
        perf_total = dashboard.get("performance_findings", {}).get("total", 0)
        rec_total = dashboard.get("recommendations", {}).get("total", 0)
        drills = len(dashboard.get("component_drilldown", []))
        cscore = summary.get("compliance_score", 100)
        cgrade = summary.get("compliance_grade", "Optimized")
        return (
            f"Here's everything available in the **{project}** analysis:\n\n"
            f"**Project Stats**\n"
            f"- Jobs analyzed: **{total_jobs}**\n"
            f"- Active components: **{total_components}**\n"
            f"- Disabled components: **{disabled_components}**\n"
            f"- Compliance Score: **{cscore}%** ({cgrade})\n\n"
            f"**Findings ({sec_total + perf_total} total)**\n"
            f"- Security findings: **{sec_total}** — vulnerabilities, exposed secrets, hardcoded credentials\n"
            f"- Performance findings: **{perf_total}** — tMap usage, commit sizes, parallelization gaps\n\n"
            f"**Recommendations ({rec_total} total)**\n"
            f"- Component-level remediation actions sorted by severity\n"
            f"- Disabled component cleanup suggestions\n\n"
            f"**Components ({drills} with findings)**\n"
            f"- Drilldown views with per-component findings and recommendations\n\n"
            f"**Charts**\n"
            f"- Component distribution (active vs disabled by type)\n"
            f"- Risk severity donut chart\n"
            f"- Source vs target system flow diagram\n"
            f"- Findings trend / timeline\n"
            f"- AI insights summary panel\n\n"
            f"**What you can ask me:**\n"
            f"- *\"What's my compliance score?\"* — compliance breakdown by category\n"
            f"- *\"Show me findings\"* — findings filtered by severity\n"
            f"- *\"How is the score calculated?\"* — formula and deduction rules\n"
            f"- *\"Tell me about components\"* — active vs disabled breakdown\n"
            f"- *\"Give me recommendations\"* — prioritized remediation actions\n"
            f"- *\"What's the risk posture?\"* — risk assessment with severity distribution\n"
            f"- *\"Explain the pipeline\"* — how the analysis works end-to-end"
        )

    def _section_answer(self, dashboard: dict[str, Any], message: str) -> str:
        normalized = message.lower()
        summary = dashboard["summary"]
        metrics = summary.get("metrics", [])
        total_jobs = self._metric_value(metrics, "Total Jobs")

        if "security" in normalized or "security section" in normalized:
            items = dashboard.get("security_findings", {}).get("items", [])
            total = len(items)
            sev = self._severity_counts(items)
            rules = sorted({str(f.get("rule_triggered", "")) for f in items if f.get("rule_triggered")})
            rag_refs = ""
            if rules:
                refs = []
                for rid in rules[:6]:
                    entry = lookup_rule(rid)
                    if entry:
                        refs.append(f"  - **{rid}**: {entry.get('title', '')} — {entry.get('remediation', '')[:100]}")
                if refs:
                    rag_refs = "\n**Remediation from RAG Knowledge Base:**\n" + "\n".join(refs)
            return (
                f"**Security Section Overview**\n\n"
                f"This section contains all security-related findings from the analysis of **{total_jobs} job(s)**.\n\n"
                f"**Total Security Findings: {total}**\n"
                f"- Critical Risk: **{sev.get('critical_risk', 0)}**\n"
                f"- Risk: **{sev.get('risk', 0)}**\n"
                f"- Warning: **{sev.get('warning', 0)}**\n"
                f"- Advisory: **{sev.get('advisory', 0)}**\n"
                f"- Informational: **{sev.get('informational', 0)}**\n\n"
                f"**What's checked**\n"
                f"- Hardcoded credentials and secrets\n"
                f"- Inline JDBC URLs without encryption\n"
                f"- Missing encrypted context variables\n"
                f"- Exposed API keys and tokens\n"
                f"- Unsecured connection parameters\n\n"
                + (f"**Rules Applied**: {', '.join(rules[:8])}" if rules else "")
                + rag_refs
                + "\n\nYou can filter by severity or search for specific components to drill deeper."
            )

        if "performance" in normalized or "performance section" in normalized:
            items = dashboard.get("performance_findings", {}).get("items", [])
            total = len(items)
            sev = self._severity_counts(items)
            rules = sorted({str(f.get("rule_triggered", "")) for f in items if f.get("rule_triggered")})
            rag_refs = ""
            if rules:
                refs = []
                for rid in rules[:6]:
                    entry = lookup_rule(rid)
                    if entry:
                        refs.append(f"  - **{rid}**: {entry.get('title', '')} — {entry.get('remediation', '')[:100]}")
                if refs:
                    rag_refs = "\n**Remediation from RAG Knowledge Base:**\n" + "\n".join(refs)
            return (
                f"**Performance Section Overview**\n\n"
                f"This section highlights runtime efficiency issues identified across **{total_jobs} job(s)**.\n\n"
                f"**Total Performance Findings: {total}**\n"
                f"- Critical Risk: **{sev.get('critical_risk', 0)}**\n"
                f"- Risk: **{sev.get('risk', 0)}**\n"
                f"- Warning: **{sev.get('warning', 0)}**\n"
                f"- Advisory: **{sev.get('advisory', 0)}**\n"
                f"- Informational: **{sev.get('informational', 0)}**\n\n"
                f"**What's checked**\n"
                f"- Excessive tMap usage patterns\n"
                f"- Small or missing commit intervals\n"
                f"- Missing parallelization in loops\n"
                f"- Nested loop anti-patterns\n"
                f"- Row-level custom Java (tJava/tJavaRow) overuse\n"
                f"- Suboptimal batch and buffer sizes\n\n"
                + (f"**Rules Applied**: {', '.join(rules[:8])}" if rules else "")
                + rag_refs
                + "\n\nUse the search bar to find specific jobs or components with performance issues."
            )

        if "recommendation" in normalized or "recommendation section" in normalized:
            items = dashboard.get("recommendations", {}).get("items", [])
            total = len(items)
            by_priority: dict[str, int] = {}
            cats: dict[str, int] = {}
            for r in items:
                p = r.get("priority", "P3")
                by_priority[p] = by_priority.get(p, 0) + 1
                c = r.get("category", "general")
                cats[c] = cats.get(c, 0) + 1
            return (
                f"**Recommendations Section Overview**\n\n"
                f"Prioritized remediation actions generated from the analysis of **{total_jobs} job(s)**.\n\n"
                f"**Total Recommendations: {total}**\n"
                f"- P1 (Critical): **{by_priority.get('P1', 0)}**\n"
                f"- P2 (High): **{by_priority.get('P2', 0)}**\n"
                f"- P3 (Medium): **{by_priority.get('P3', 0)}**\n\n"
                f"**Categories**\n"
                + "\n".join(f"- {c.replace('_', ' ').title()}: **{count}**" for c, count in sorted(cats.items()))
                + "\n\nEach recommendation includes a suggestion, expected impact, and reference to the triggering finding. "
                "You can filter by priority or search for keywords to narrow down."
            )

        if "component" in normalized or "component section" in normalized:
            active = self._metric_value(metrics, "Total Components")
            disabled = self._metric_value(metrics, "Disabled Components")
            charts = dashboard.get("charts", {})
            active_dist = charts.get("active_component_distribution", [])
            disabled_dist = charts.get("disabled_component_distribution", [])
            drills = dashboard.get("component_drilldown", [])
            return (
                f"**Components Section Overview**\n\n"
                f"Complete inventory of all Talend components across **{total_jobs} job(s)**.\n\n"
                f"**Component Status**\n"
                f"- Active components: **{active}**\n"
                f"- Disabled components: **{disabled}**\n"
                f"- Total: **{active + disabled}**\n\n"
                f"**Active Components by Type**\n"
                + ("\n".join(f"- {p.get('name', 'Unknown')}: **{p.get('value', 0)}**" for p in active_dist[:10]) if active_dist else "- No distribution data available")
                + ("\n\n**Disabled Components by Type**\n" + "\n".join(f"- {p.get('name', 'Unknown')}: **{p.get('value', 0)}** disabled" for p in disabled_dist[:10]) if disabled_dist else "")
                + f"\n\n**Components with Findings**: {len(drills)}"
                + "\n\nYou can search by job name, component name, or type to find specific components."
            )

        if "report" in normalized or "report section" in normalized:
            return (
                f"**Reports Section Overview**\n\n"
                f"Export and review options for the current analysis.\n\n"
                f"**Available Exports**\n"
                f"- **Dashboard JSON** — full analysis payload including summary, findings, recommendations, "
                f"component drilldown, and chart data\n"
                f"- **Findings CSV** — all security and performance findings in a structured CSV format "
                f"with job, component, severity, and rule details\n\n"
                f"**Analysis Record**\n"
                f"- The current analysis is persisted as a JSON record and can be retrieved using the analysis ID.\n"
                f"- Analysis history is available across server restarts.\n\n"
                f"Use the export buttons in the Reports section to download the data."
            )

        return self._capabilities_answer(dashboard)

    def _formula_answer(self, dashboard: dict[str, Any], findings: list[dict[str, Any]]) -> str:
        summary = dashboard["summary"]
        config = get_scoring_config_data()
        compliance = config.get("compliance", {})
        comp_thresholds = compliance.get("maturity_levels", {}).get(
            compliance.get("default_maturity", "standard"), {}
        ).get("grade_thresholds", [])
        comp_grade_lines = []
        for i, t in enumerate(comp_thresholds):
            if i == len(comp_thresholds) - 1:
                prev = comp_thresholds[i - 1]["min_score"]
                comp_grade_lines.append(f"- **<{prev}**: {t['grade']}")
            else:
                comp_grade_lines.append(f"- **≥{t['min_score']}**: {t['grade']}")

        cscore = summary.get("compliance_score", 100)
        cgrade = summary.get("compliance_grade", "Optimized")
        cmaturity = summary.get("compliance_maturity", "standard")
        breakdown = summary.get("compliance_breakdown") or {}

        parts = [
            "Here's how the **scores** are calculated, with your current dashboard values:\n",
            "**Compliance Score** (rule-based)",
            "Formula: (Passed Rules / Total Applicable Rules) * 100 per category → Average across categories",
            f"Your score: **{cscore}%** — **{cgrade}** (Maturity: {cmaturity})",
        ]

        if breakdown.get("category_scores"):
            parts.append("")
            parts.append("**Your Compliance Breakdown:**")
            parts.append(f"Rules: {breakdown.get('total_passed', 0)} passed / {breakdown.get('total_rules_evaluated', 0)} total | {breakdown.get('total_failed', 0)} failed")
            for cs in breakdown["category_scores"]:
                status = "✅" if cs["score"] >= 80 else "⚠️" if cs["score"] >= 60 else "❌"
                parts.append(f"  {status} **{cs['label']}**: {cs['score']}% ({cs['passed_rules']}/{cs['total_rules']} passed)")

        parts.append("")
        parts.append("**Maturity Levels**")
        parts.extend(comp_grade_lines)
        parts.append("")
        parts.append("Findings for **disabled components** are excluded from scoring.")

        return "\n".join(parts)

    def _data_sources_answer(self) -> str:
        return (
            "Here's where the dashboard data comes from:\n\n"
            "**Analysis Agents** (run concurrently)\n"
            "- **XML Parser** — reads uploaded ZIP files, extracts job designs, components, connections, and context variables\n"
            "- **Security Agent** — scans for security vulnerabilities like exposed secrets, inline JDBC URLs, missing encrypted contexts, and hardcoded credentials\n"
            "- **Performance Agent** — analyzes runtime and efficiency issues such as excessive tMap usage, small commit intervals, missing parallelization, and nested loop patterns\n"
            "- **Component Agent** — validates component configurations and classifies them as active or disabled\n"
            "- **Recommendation Agent** — generates prioritized remediation suggestions using AI with RAG guidance\n\n"
            "**Dashboard Aggregator**\n"
            "Collects all agent outputs, filters findings for active components, computes the health score using the scoring engine, and produces the unified dashboard payload with summary metrics, findings, recommendations, component drilldown, and chart data.\n\n"
            "All data is scoped to a single analysis run identified by a unique analysis ID."
        )

    def _metrics_kpis_answer(self, dashboard: dict[str, Any]) -> str:
        summary = dashboard["summary"]
        metrics = summary.get("metrics", [])
        def mv(label: str) -> int:
            for m in metrics:
                if m.get("label") == label:
                    return int(m.get("value", 0))
            return 0
        jobs = mv("Total Jobs")
        active = mv("Total Components")
        disabled = mv("Disabled Components")
        critical = mv("Critical Issues")
        sec_total = dashboard.get("security_findings", {}).get("total", 0)
        perf_total = dashboard.get("performance_findings", {}).get("total", 0)
        rec_total = dashboard.get("recommendations", {}).get("total", 0)
        cscore = summary.get("compliance_score", 100)
        cgrade = summary.get("compliance_grade", "Optimized")
        return (
            f"Here's what each KPI on the dashboard means:\n\n"
            f"**Compliance Score** — rule-based compliance: **{cscore}%** (Grade: **{cgrade}**). "
            f"Computed as (Passed Rules / Total Applicable Rules) per category.\n"
            f"**Critical Issues** — findings with critical_risk severity requiring immediate attention: **{critical}**.\n"
            f"**Total Jobs** — number of Talend jobs parsed: **{jobs}**.\n"
            f"**Active Components** — enabled/activated component instances across all jobs: **{active}**.\n"
            f"**Disabled Components** — deactivated instances not executing at runtime: **{disabled}**.\n"
            f"**Total Findings** — sum of security and performance findings: **{sec_total + perf_total}** (Security: {sec_total}, Performance: {perf_total}).\n"
            f"**Recommendations** — AI-generated remediation suggestions sorted by priority: **{rec_total}**.\n\n"
            f"**Charts**\n"
            f"- Component Distribution — active components by type\n"
            f"- Risk Severity Donut — findings broken down by severity (critical_risk, risk, warning, advisory)\n"
            f"- Source vs Target Flow — data source and target system distribution\n"
            f"- Findings Trend — findings by category\n"
            f"- AI Insights Panel — quick-glance summary of all key metrics"
        )

    def _rule_engine_answer(self) -> str:
        return (
            "Here's how findings are generated:\n\n"
            "**Rule Engine**\n"
            "After the XML parser extracts all components from Talend jobs, the rule engine scans "
            "each component's properties, configurations, and job design patterns against a set of "
            "predefined rules. Each rule has:\n"
            "- A unique rule ID (e.g., RULE-SEC-001, RULE-PERF-002)\n"
            "- A category: Security, Performance, Maintainability, or Architecture\n"
            "- A severity level: Critical Risk, Risk, Warning, Advisory, or Informational\n\n"
            "When a rule matches a component, a finding is created with the component name, job name, "
            "rule ID, severity, and a recommendation description.\n\n"
            "**Security findings** include exposed secrets, inline JDBC URLs, missing encrypted contexts, hardcoded credentials.\n"
            "**Performance findings** include excessive tMap usage, small commit intervals, missing parallelization, nested loops.\n\n"
            "Findings for **disabled components** are excluded from the health score calculation "
            "but remain visible in the findings list for review."
        )

    def _recommendation_engine_answer(self) -> str:
        return (
            "Here's how recommendations are generated:\n\n"
            "**Recommendation Agent**\n"
            "The AI recommendation agent analyzes all findings and component data using a LangGraph pipeline "
            "with Retrieval-Augmented Generation (RAG). It produces context-aware remediation suggestions "
            "using Talend best practices from the knowledge base as guidance.\n\n"
            "Each recommendation includes:\n"
            "- **Priority level**: P1 (Critical), P2 (High), P3 (Medium)\n"
            "- **Title** and **suggestion** text with actionable steps\n"
            "- **Expected impact** of implementing the recommendation\n"
            "- **Reference** to the triggering finding or rule\n\n"
            "The engine also generates **cleanup suggestions (AI-REC-005)** for disabled components "
            "that should be removed from job designs. Recommendations are sorted by priority and grouped in the dashboard."
        )

    def _pipeline_answer(self) -> str:
        return (
            "The analysis pipeline processes Talend workspace exports end-to-end:\n\n"
            "**1. Upload** — user uploads a ZIP file containing Talend workspace exports\n"
            "**2. Parse** — XML parser extracts job designs, components, connections, contexts, and metadata\n"
            "**3. Classify** — components are classified as active or disabled via XML attributes (activated, enabled) and parameters (ACTIVATE, ENABLED)\n"
            "**4. Execute Agents** — four LangGraph agents run in parallel: Security Scanner, Performance Analyzer, Component Validator, Recommendation Generator\n"
            "**5. Aggregate** — Dashboard Aggregator collects all outputs, filters findings for active components, computes the compliance score\n"
            "**6. Persist** — analysis record is saved to a JSON file for retrieval across restarts\n"
            "**7. Serve** — dashboard service exposes the payload via REST API endpoints\n\n"
            "All agents run asynchronously to avoid blocking the event loop."
        )

    def _component_classification_answer(self) -> str:
        return (
            "Components in Talend jobs are classified as active or disabled based on:\n\n"
            "- **XML attributes**: the parser checks 'activated' and 'enabled' attributes on component elements\n"
            "- **Parameters**: checks component parameters named 'ACTIVATE' and 'ENABLED' for false/true values\n\n"
            "If any of these indicate the component is deactivated, it is marked as **disabled**.\n"
            "**Active components** are fully enabled and execute in the job flow.\n"
            "**Disabled components** are deactivated and do not execute at runtime.\n\n"
            "Findings for disabled components are excluded from scoring. "
            "The dashboard shows both active and disabled component "
            "distribution charts, and disabled components are flagged with cleanup recommendation AI-REC-005."
        )

    def _compliance_answer(self, dashboard: dict[str, Any], findings: list[dict[str, Any]]) -> str:
        summary = dashboard["summary"]
        metrics = summary.get("metrics", [])
        total_jobs = self._metric_value(metrics, "Total Jobs")
        total_components = self._metric_value(metrics, "Total Components")
        disabled = self._metric_value(metrics, "Disabled Components")
        security_count = dashboard.get("security_findings", {}).get("total", 0)
        performance_count = dashboard.get("performance_findings", {}).get("total", 0)
        compliance = summary.get("compliance_breakdown") or {}

        parts = [
            f"Here's your **Compliance Score** breakdown:",
            f"",
            f"Overall Compliance: **{compliance.get('overall_score', 100)}%** — **{compliance.get('grade', 'Optimized')}** (Maturity: {compliance.get('maturity', 'standard')})",
            f"",
            f"**Scope**",
            f"- Jobs analyzed: {total_jobs}",
            f"- Active components: {total_components}",
            f"- Disabled components: {disabled}",
            f"- Total findings: {security_count + performance_count}",
        ]

        if compliance:
            parts.append("")
            parts.append("**Compliance by Category**")
            parts.append(f"Rules: {compliance.get('total_passed', 0)} passed / {compliance.get('total_rules_evaluated', 0)} total | {compliance.get('total_failed', 0)} failed")
            for cs in compliance.get("category_scores", []):
                status = "✅" if cs["score"] >= 80 else "⚠️" if cs["score"] >= 60 else "❌"
                parts.append(f"  {status} **{cs['label']}**: {cs['score']}% ({cs['passed_rules']}/{cs['total_rules']} passed)")
                if cs.get("failed_rule_ids"):
                    for rid in cs["failed_rule_ids"][:3]:
                        entry = lookup_rule(rid)
                        sev = entry.get("classification", "") if entry else ""
                        title = entry.get("title", "") if entry else ""
                        parts.append(f"    - ❌ {rid}: {title[:80]} ({sev[:40]})")

        return "\n".join(parts)

    def _component_count_answer(self, dashboard: dict[str, Any]) -> str:
        summary = dashboard["summary"]
        metrics = summary.get("metrics", [])
        charts = dashboard.get("charts", {})
        total_components = self._metric_value(metrics, "Total Components")
        disabled_components = self._metric_value(metrics, "Disabled Components")
        total_jobs = self._metric_value(metrics, "Total Jobs")
        active_dist = charts.get("active_component_distribution", [])
        disabled_dist = charts.get("disabled_component_distribution", [])

        parts = [
            f"Here's what I found for your **component inventory**:",
            f"",
            f"Across {total_jobs} job(s), your workspace has:",
            f"- **Active components**: {total_components}",
            f"- **Disabled components**: {disabled_components}",
            f"- **Total**: {total_components + disabled_components}",
        ]

        if active_dist:
            parts.append("")
            parts.append("**Active Components Breakdown**")
            for entry in active_dist:
                name = entry.get("name", "unknown")
                value = entry.get("value", 0)
                parts.append(f"- {name}: {value}")

        if disabled_dist:
            parts.append("")
            parts.append("**Disabled Components** (worth reviewing for cleanup)")
            for entry in disabled_dist:
                name = entry.get("name", "unknown")
                value = entry.get("value", 0)
                parts.append(f"- {name}: {value} disabled")

        return "\n".join(parts)

    def _component_answer(self, components: list[dict[str, Any]]) -> str:
        if not components:
            return "No components matched your query — try asking about a specific component or job name."
        if len(components) == 1:
            comp = components[0]
            findings = comp.get("findings", [])
            recs = comp.get("recommendations", [])
            parts = [
                f"Let me pull up **{comp.get('component_name', 'Unknown')}**:",
                f"- Type: {comp.get('component_type', 'N/A')}",
                f"- Job: {comp.get('job_name', 'N/A')}",
                f"- Findings: {len(findings)}",
                f"- Recommendations: {len(recs)}",
            ]
            if findings:
                parts.append("")
                parts.append("**Findings**")
                for f in findings[:5]:
                    sev = f.get("severity", "informational").upper()
                    name = f.get("name", "Issue")
                    rec = f.get("recommendation", "")
                    parts.append(f"- [{sev}] {name}: {rec}")
            if recs:
                parts.append("")
                parts.append("**Recommendations**")
                for r in recs[:3]:
                    parts.append(f"- {r.get('suggestion', r.get('title', ''))}")
            return "\n".join(parts)

        parts = [
            f"I found **{len(components)} components** matching your query:",
            "",
        ]
        for comp in components:
            f_count = len(comp.get("findings", []))
            parts.append(
                f"- {comp.get('component_name', 'Unknown')} ({comp.get('component_type', 'N/A')}) "
                f"in {comp.get('job_name', 'N/A')} — {f_count} finding(s)"
            )
        return "\n".join(parts)

    def _job_names_answer(self, dashboard: dict[str, Any]) -> str:
        job_names: set[str] = set()
        for section in ("security_findings", "performance_findings"):
            for item in dashboard.get(section, {}).get("items", []):
                jn = item.get("job_name")
                if jn:
                    job_names.add(jn)
        for comp in dashboard.get("component_drilldown", []):
            jn = comp.get("job_name")
            if jn:
                job_names.add(jn)
        if not job_names:
            return "No job names found in the current analysis."
        sorted_names = sorted(job_names)
        return (
            f"**Jobs in the current analysis ({len(sorted_names)} total):**\n"
            + "\n".join(f"- {name}" for name in sorted_names)
        )

    def _recommendation_answer(self, recommendations: list[dict[str, Any]]) -> str:
        if not recommendations:
            return "No recommendations available for the current query — you're in good shape there!"
        by_priority: dict[str, list[dict[str, Any]]] = {}
        for rec in recommendations:
            priority = rec.get("priority", "P3")
            by_priority.setdefault(priority, []).append(rec)

        parts = [
            f"I've got **{len(recommendations)} recommendation(s)** to share:",
            "",
        ]
        for priority in ("P1", "P2", "P3"):
            grouped = by_priority.get(priority, [])
            if not grouped:
                continue
            label = {"P1": "Critical", "P2": "High", "P3": "Medium"}.get(priority, priority)
            parts.append(f"**{label} Priority ({len(grouped)})**")
            for rec in grouped:
                title = rec.get("title", "Recommendation")
                suggestion = rec.get("suggestion", "")
                parts.append(f"- {title}: {suggestion[:120]}")
            parts.append("")
        if parts[-1] == "":
            parts.pop()
        return "\n".join(parts)

    def _risk_answer(self, dashboard: dict[str, Any], findings: list[dict[str, Any]]) -> str:
        summary = dashboard["summary"]
        severity_counts: dict[str, int] = {}
        for finding in findings:
            severity = str(finding.get("severity") or "informational").lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        critical_high = [
            finding for finding in findings
            if str(finding.get("severity", "")).lower() in {"critical_risk", "risk"}
        ]
        compliance = summary.get("compliance_breakdown") or {}

        parts = [
            f"Here's your **Risk Assessment**:",
            f"",
            f"- Compliance Score: **{compliance.get('overall_score', 100)}%** — **{compliance.get('grade', 'Optimized')}**",
            f"- Total findings in scope: {len(findings)}",
            f"- Critical Risk / Risk findings: {len(critical_high)}",
        ]

        if severity_counts:
            parts.append("")
            parts.append("**Severity Breakdown**")
            for sev in ("critical_risk", "risk", "warning", "advisory", "informational"):
                if sev in severity_counts:
                    label = sev.replace("_", " ").title()
                    parts.append(f"- {label}: {severity_counts[sev]}")

        if critical_high:
            parts.append("")
            parts.append("**Top Critical Risks**")
            for finding in critical_high[:5]:
                sev = finding.get("severity", "info").upper()
                name = finding.get("name", "Finding")
                comp = finding.get("component_name", "unknown")
                job = finding.get("job_name", "unknown")
                parts.append(f"- [{sev}] {name} on {comp} in {job}")
        return "\n".join(parts)

    def _filter_answer(
        self,
        findings: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
        components: list[dict[str, Any]],
    ) -> str:
        return (
            f"Sure, here's what matched your filter:\n\n"
            f"- Findings: {len(findings)}\n"
            f"- Recommendations: {len(recommendations)}\n"
            f"- Components: {len(components)}\n\n"
            f"Use the suggested action below to apply this filter on the dashboard."
        )

    def _findings_answer(self, findings: list[dict[str, Any]], state: ChatGraphState | None = None) -> str:
        if not findings:
            return "No findings matched your query — looks like that area is clean!"
        by_severity: dict[str, list[dict[str, Any]]] = {}
        for f in findings:
            sev = str(f.get("severity") or "info").lower()
            by_severity.setdefault(sev, []).append(f)

        parts = [
            f"I found **{len(findings)} finding(s)** for you:",
            "",
        ]
        explained_rule_ids: set[str] = set()
        for sev in ("critical_risk", "risk", "warning", "advisory", "informational"):
            grouped = by_severity.get(sev, [])
            if not grouped:
                continue
            parts.append(f"**{sev.capitalize()} ({len(grouped)})**")
            for f in grouped:
                name = f.get("name", "Finding")
                comp = f.get("component_name", "unknown")
                job = f.get("job_name", "unknown")
                rec = f.get("recommendation", "")
                rag_info = self._finding_rag_explanation(f)
                parts.append(f"- {name} on {comp} in {job}: {rec[:100]}{rag_info}")
                rid = str(f.get("rule_triggered") or f.get("evidence", {}).get("rule_id") or "")
                if rid:
                    explained_rule_ids.add(rid)
            parts.append("")
        if explained_rule_ids:
            parts.append("**Referenced RAG Rules:** " + ", ".join(sorted(explained_rule_ids)))
            parts.append("Use the rule IDs above to look up detailed remediation steps in the knowledge base.")
        if parts[-1] == "":
            parts.pop()
        return "\n".join(parts)

    def _overview_answer(self, dashboard: dict[str, Any]) -> str:
        summary = dashboard["summary"]
        metrics = summary.get("metrics", [])
        project = summary.get("project_name", "your project")
        total_jobs = self._metric_value(metrics, "Total Jobs")
        total_components = self._metric_value(metrics, "Total Components")
        disabled_components = self._metric_value(metrics, "Disabled Components")
        cscore = summary.get("compliance_score", 100)
        cgrade = summary.get("compliance_grade", "Optimized")
        security_count = dashboard.get("security_findings", {}).get("total", 0)
        performance_count = dashboard.get("performance_findings", {}).get("total", 0)
        rec_count = dashboard.get("recommendations", {}).get("total", 0)
        critical = self._metric_value(metrics, "Critical Issues")

        return (
            f"Here's a quick snapshot of **{project}**:\n\n"
            f"**Project Stats**\n"
            f"- Jobs: **{total_jobs}**\n"
            f"- Active components: **{total_components}**\n"
            f"- Disabled components: **{disabled_components}**\n\n"
            f"**Scores**\n"
            f"- Compliance Score: **{cscore}%** — **{cgrade}**\n"
            f"- Critical issues: **{critical}**\n\n"
            f"**Findings & Recommendations**\n"
            f"- Security findings: **{security_count}**\n"
            f"- Performance findings: **{performance_count}**\n"
            f"- Recommendations: **{rec_count}**\n\n"
            f"**What would you like to explore?**\n"
            f"- Compliance score breakdown or formula\n"
            f"- Specific findings by category or severity\n"
            f"- Component inventory and status\n"
            f"- Prioritized recommendations"
        )

    def _sell_tool_answer(self) -> str:
        return (
            "Here's how you can position the **Talend Health Audit Tool** to business stakeholders:\n\n"
            "**Problem Statement**\n"
            "- Manual Talend job review is time-consuming.\n"
            "- Security issues like hardcoded credentials are difficult to identify across large projects.\n"
            "- Performance bottlenecks and unused components often go unnoticed.\n"
            "- Lack of centralized visibility into project health.\n"
            "- Architecture and coding standards are not consistently enforced.\n\n"
            "**Solution**\n"
            "- Upload a Talend project ZIP file.\n"
            "- Automatically analyze all jobs and components.\n"
            "- Detect security, performance, and architecture issues.\n"
            "- Generate an enterprise health score.\n"
            "- Provide AI-driven recommendations and remediation steps.\n"
            "- Visualize findings through an interactive dashboard.\n\n"
            "**Key Features**\n"
            "- Automated Talend project analysis.\n"
            "- Security audit (hardcoded usernames, passwords, tokens).\n"
            "- Performance assessment.\n"
            "- Component inventory and usage analysis.\n"
            "- Health score calculation.\n"
            "- Rule engine-based validation.\n"
            "- AI-powered recommendations.\n"
            "- AI Chat Assistant for dashboard queries.\n"
            "- Executive-level reporting and dashboards.\n\n"
            "**Business Benefits**\n"
            "- Reduce manual review effort by 80–90%.\n"
            "- Identify risks before production deployment.\n"
            "- Improve security compliance.\n"
            "- Accelerate modernization and migration projects.\n"
            "- Reduce technical debt.\n"
            "- Standardize Talend development practices.\n"
            "- Improve project maintainability.\n\n"
            "**Target Audience**\n"
            "- Data Engineering Teams\n"
            "- Enterprise Architects\n"
            "- Delivery Managers\n"
            "- Security Teams\n"
            "- Data Governance Teams\n"
            "- CTOs and Technology Leaders\n\n"
            "**Future Roadmap**\n"
            "- Talend to Databricks migration assessment.\n"
            "- Talend modernization insights.\n"
            "- Multi-tool support (Informatica, SSIS, DataStage, ADF, DBT).\n"
            "- Trend analysis and historical comparisons.\n"
            "- Automated remediation generation.\n\n"
            "**30-Second Elevator Pitch**\n\n"
            "Talend Health Audit Tool is an AI-powered platform that automatically analyzes "
            "Talend projects, identifies security risks, performance bottlenecks, architectural "
            "issues, and technical debt, then generates actionable recommendations and executive "
            "dashboards within minutes, significantly reducing manual review effort and improving "
            "project quality. 🚀"
        )

    def _tool_use_answer(self) -> str:
        return (
            "The **Talend Health Audit Tool** is an AI-powered platform designed to automatically "
            "analyze Talend projects and provide deep insights into their health, security, and performance.\n\n"
            "**Problem Statement**\n"
            "- Manual Talend job review is time-consuming.\n"
            "- Security issues like hardcoded credentials are difficult to identify across large projects.\n"
            "- Performance bottlenecks and unused components often go unnoticed.\n"
            "- Lack of centralized visibility into project health.\n"
            "- Architecture and coding standards are not consistently enforced.\n\n"
            "**Solution**\n"
            "- Upload a Talend project ZIP file.\n"
            "- Automatically analyze all jobs and components.\n"
            "- Detect security, performance, and architecture issues.\n"
            "- Generate an enterprise health score.\n"
            "- Provide AI-driven recommendations and remediation steps.\n"
            "- Visualize findings through an interactive dashboard.\n\n"
            "**Key Features**\n"
            "- Automated Talend project analysis.\n"
            "- Security audit (hardcoded usernames, passwords, tokens).\n"
            "- Performance assessment.\n"
            "- Component inventory and usage analysis.\n"
            "- Health score calculation.\n"
            "- Rule engine-based validation.\n"
            "- AI-powered recommendations.\n"
            "- AI Chat Assistant for dashboard queries.\n"
            "- Executive-level reporting and dashboards.\n\n"
            "**Business Benefits**\n"
            "- Reduce manual review effort by 80–90%.\n"
            "- Identify risks before production deployment.\n"
            "- Improve security compliance.\n"
            "- Accelerate modernization and migration projects.\n"
            "- Reduce technical debt.\n"
            "- Standardize Talend development practices.\n"
            "- Improve project maintainability.\n\n"
            "**Target Audience**\n"
            "- Data Engineering Teams\n"
            "- Enterprise Architects\n"
            "- Delivery Managers\n"
            "- Security Teams\n"
            "- Data Governance Teams\n"
            "- CTOs and Technology Leaders\n\n"
            "**Future Roadmap**\n"
            "- Talend to Databricks migration assessment.\n"
            "- Talend modernization insights.\n"
            "- Multi-tool support (Informatica, SSIS, DataStage, ADF, DBT).\n"
            "- Trend analysis and historical comparisons.\n"
            "- Automated remediation generation.\n\n"
            "**30-Second Elevator Pitch**\n\n"
            "Talend Health Audit Tool is an AI-powered platform that automatically analyzes "
            "Talend projects, identifies security risks, performance bottlenecks, architectural "
            "issues, and technical debt, then generates actionable recommendations and executive "
            "dashboards within minutes, significantly reducing manual review effort and improving "
            "project quality. 🚀"
        )

    def _unknown_answer(self) -> str:
        return (
            "I'm sorry, but that question is outside my area of expertise. 😊\n\n"
            "I specialize in analyzing Talend job health based on your uploaded workspace data "
            "and a comprehensive Talend knowledge base. I can help you with things like:\n"
            "- **Health score** breakdown and formula\n"
            "- **Security and performance findings** with best practices and remediation\n"
            "- **Component inventory** (active vs disabled)\n"
            "- **Prioritized recommendations** with rule ID references\n"
            "- **Risk assessment**\n"
            "- **Talend best practices** and anti-pattern explanations\n\n"
            "I draw from a knowledge base of Talend security, performance, maintainability, "
            "and architecture best practices. Feel free to ask me something about your Talend analysis! 🚀"
        )

    def _actions_for(self, state: ChatGraphState) -> list[DashboardChatAction]:
        message = state["request"].message.lower()
        intent = state["intent"]
        actions: list[DashboardChatAction] = []
        severity = self._severity_filter(message)

        if intent in ("health_score", "overview"):
            actions.append(DashboardChatAction(type="navigate", label="Open Dashboard", target="Dashboard"))
        if intent == "capabilities":
            for section in ("Dashboard", "Security", "Performance", "Components", "Recommendations"):
                actions.append(DashboardChatAction(type="navigate", label=f"View {section}", target=section))
        if intent == "component_count":
            actions.append(DashboardChatAction(type="navigate", label="View Components", target="Components"))
        if intent == "section_info":
            for s_name, s_target in (("security", "Security"), ("performance", "Performance"), ("recommendation", "Recommendations"), ("component", "Components"), ("report", "Reports")):
                if s_name in message:
                    actions.append(DashboardChatAction(type="navigate", label=f"Open {s_target}", target=s_target))
                    break
        if "security" in message:
            actions.append(
                DashboardChatAction(
                    type="filter",
                    label="Filter Security Findings",
                    target="Security",
                    filters={"severity": severity, "query": state["request"].message},
                )
            )
        if "performance" in message:
            actions.append(
                DashboardChatAction(
                    type="filter",
                    label="Filter Performance Findings",
                    target="Performance",
                    filters={"severity": severity, "query": state["request"].message},
                )
            )
        if intent == "recommendations":
            actions.append(
                DashboardChatAction(
                    type="filter",
                    label="Open Matching Recommendations",
                    target="Recommendations",
                    filters={"severity": severity, "query": state["request"].message},
                )
            )
        component = next(iter(state["matches"].get("components", [])), None)
        if component:
            actions.append(
                DashboardChatAction(
                    type="open_component",
                    label=f"Open {component.get('component_name')}",
                    target="Components",
                    filters={
                        "job_name": component.get("job_name"),
                        "component_name": component.get("component_name"),
                        "component_type": component.get("component_type"),
                    },
                )
            )
        if not actions:
            actions.append(DashboardChatAction(type="navigate", label="Review Dashboard", target="Dashboard"))
        return actions

    def _classify_intent(self, message: str) -> str:
        normalized = message.lower().strip()
        greeting_words = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings"}
        if normalized in greeting_words or any(normalized.startswith(g) for g in greeting_words):
            if not any(term in normalized for term in ("health", "score", "component", "finding", "risk", "recommend")):
                return "greeting"
        if any(term in normalized for term in ("formula", "calculate", "calculated", "calculation", "derived", "computed", "determined", "basis", "how does", "how is", "how was", "explain")) and any(
            term in normalized for term in ("health", "score", "grade", "work", "works")
        ):
            return "formula"
        if "sources" in normalized or "data source" in normalized or "where does" in normalized or "dashboard data" in normalized:
            if not any(term in normalized for term in ("filter", "list", "show", "finding", "issue", "target", "flow")):
                return "data_sources"
        if any(term in normalized for term in ("job name", "job names", "jobs are", "jobs in", "list jobs", "what jobs", "tell me the job")):
            return "job_names"
        if any(term in normalized for term in ("kpi", "what does", "what is", "meaning", "mean")) and any(
            term in normalized for term in ("health", "score", "grade", "component", "finding", "metric", "kpi")
        ):
            return "metrics_kpis"
        if any(term in normalized for term in ("rule engine", "rules checked", "rules applied", "how.*finding", "how.*rule", "findings generated", "findings created", "how.*detect")):
            return "rule_engine"
        if any(term in normalized for term in ("recommendation engine", "how.*recommendation generated", "how.*recommendation created", "recommendation generation", "how.*recommendation work")):
            return "recommendation_engine"
        if any(term in normalized for term in ("pipeline", "analysis flow", "analysis process", "how.*analysis work", "end to end", "analysis pipeline")):
            return "pipeline"
        if any(term in normalized for term in ("recommend", "remediate", "fix", "action")):
            return "recommendations"
        if any(term in normalized for term in ("active component", "disabled component", "component classification", "component status", "component type", "component state")):
            return "component_classification"
        if any(term in normalized for term in ("sell", "business people", "pitch", "stakeholder", "buy", "customer", "client")) and any(
            term in normalized for term in ("tool", "this", "product", "solution")
        ):
            return "sell_tool"
        if any(term in normalized for term in ("use of this tool", "purpose of this tool", "what does this tool do", "what is the use", "why would i use", "benefits of this tool", "what problem")):
            return "tool_use"
        if any(term in normalized for term in ("what information", "what data", "available", "related information", "tell me about this", "what can you tell", "what do you know", "capabilities", "what does this tool")):
            return "capabilities"
        sections = {"security", "performance", "recommendation", "component", "report"}
        if any(
            (f"{s} section" in normalized or f"about the {s}" in normalized or f"in the {s}" in normalized or f"{s} information" in normalized)
            for s in sections
        ):
            return "section_info"
        if any(term in normalized for term in ("health score", "compliance score", "score", "grade")):
            return "health_score"
        if any(term in normalized for term in ("risk", "risks", "posture")):
            return "risk_summary"
        if any(term in normalized for term in ("total", "count", "how many")) and any(
            term in normalized for term in ("component", "job")
        ):
            return "component_count"
        if any(term in normalized for term in ("component", "detail")):
            return "component_details"
        if any(term in normalized for term in ("filter", "only", "list", "show me")):
            return "filter"
        if any(term in normalized for term in ("finding", "issue", "explain", "why")):
            return "findings"
        if any(term in normalized for term in ("overview", "summary", "snapshot", "quick look", "tell me about this project", "what's here", "what do you have")):
            return "overview"
        return "unknown"

    def _match_records(
        self,
        records: list[dict[str, Any]],
        terms: list[str],
        message: str,
    ) -> list[dict[str, Any]]:
        severity = self._severity_filter(message)
        domain = self._domain_filter(message)
        matched = []
        for record in records:
            haystack = json.dumps(record, default=str).lower()
            if severity and severity not in haystack:
                continue
            if domain and domain not in haystack:
                continue
            if not terms or any(term in haystack for term in terms):
                matched.append(record)
        return matched

    def _query_terms(self, message: str) -> list[str]:
        stop_words = {
            "what", "show", "list", "give", "tell", "about", "with", "from",
            "that", "this", "only", "please", "dashboard", "analysis",
            "finding", "findings",
        }
        return [
            term
            for term in re.findall(r"[a-zA-Z0-9_.$-]+", message.lower())
            if len(term) > 2 and term not in stop_words
        ]

    def _severity_filter(self, message: str) -> str | None:
        normalized = message.lower()
        for severity in ("critical_risk", "critical risk", "risk", "warning", "advisory", "informational"):
            if severity in normalized:
                return severity
        return None

    def _domain_filter(self, message: str) -> str | None:
        normalized = message.lower()
        if "security" in normalized:
            return "security"
        if "performance" in normalized:
            return "performance"
        return None


dashboard_chat_service = DashboardChatService()

from backend.agents.security_agent.rules import DEFAULT_SECURITY_RULES, SecurityRule
from backend.rag.registry import lookup_rule, resolve_rag_fields, resolve_severity
from backend.shared.models import AgentFinding, AgentRecommendation, FindingSeverity

SCANNER_TO_RAG_RULE_MAP: dict[str, str] = {
    "SEC-PASSWORD-001": "RULE-SEC-001",
    "SEC-USERNAME-001": "RULE-SEC-008",
    "SEC-APIKEY-001": "RULE-SEC-005",
    "SEC-TOKEN-001": "RULE-SEC-005",
    "SEC-JDBC-001": "RULE-SEC-002",
}


class SecurityScanner:
    def __init__(self, rules: list[SecurityRule] | None = None) -> None:
        self.rules = rules or DEFAULT_SECURITY_RULES

    def scan(
        self,
        workspace_path: str | None = None,
        inventory: dict | None = None,
    ) -> tuple[list[AgentFinding], list[AgentRecommendation], dict]:
        findings = self._scan_inventory(inventory or {})

        deduped_findings = self._dedupe_findings(findings)
        recommendations = self._build_recommendations(deduped_findings)
        metrics = self._build_metrics(deduped_findings)
        return deduped_findings, recommendations, metrics

    def _scan_inventory(self, inventory: dict) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for job in inventory.get("jobs", []):
            job_name = job.get("name", "unknown")
            xml_file = str(job.get("path") or "")
            if not xml_file:
                continue
            for component in job.get("components", []):
                if component.get("disabled"):
                    continue
                parameters = component.get("parameters", {})
                component_name = str(component.get("name") or "")
                component_type = str(component.get("component_name") or "")
                if not component_name or not component_type:
                    continue
                for name, value in parameters.items():
                    target = f"{name}={value}"
                    findings.extend(
                        self._scan_text(
                            text=target,
                            xml_file=xml_file,
                            xml_path=(
                                f"/job[@name='{job_name}']"
                                f"/component[@name='{component_name}']"
                                f"/parameter[@name='{name}']"
                            ),
                            job_name=job_name,
                            component_name=component_name,
                            component_type=component_type,
                            parameter_name=str(name),
                            matched_value=str(value),
                        )
                    )
        return findings

    def _scan_text(
        self,
        text: str,
        xml_file: str,
        xml_path: str,
        job_name: str,
        component_name: str,
        component_type: str,
        parameter_name: str,
        matched_value: str,
    ) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for rule in self.rules:
            rag_rule_id = SCANNER_TO_RAG_RULE_MAP.get(rule.id, rule.id)
            rag_fields = resolve_rag_fields(rag_rule_id)
            rag_entry = lookup_rule(rag_rule_id)
            try:
                severity = FindingSeverity(rag_fields["severity"])
            except ValueError:
                severity = FindingSeverity.INFORMATIONAL
            category = rag_fields["category"]
            for match_index, match in enumerate(rule.pattern.finditer(text), start=1):
                findings.append(
                    AgentFinding(
                        id=f"{rule.id}-{abs(hash((xml_file, xml_path, match.start(), match.group(0)))) % 100000}",
                        title=rule.title,
                        job_name=job_name,
                        component_name=component_name,
                        component_type=component_type,
                        category=category,
                        severity=severity,
                        rule_triggered=rag_rule_id,
                        description=rule.description,
                        impact=rag_fields["impact"],
                        recommendation=rag_fields["remediation"] or rule.description,
                        source=rag_fields["source"],
                        evidence={
                            "rule_id": rag_rule_id,
                            "rule_triggered": rag_rule_id,
                            "scanner_rule_id": rule.id,
                            "rule_title": rule.title,
                            "component_name": component_name,
                            "component_type": component_type,
                            "job_name": job_name,
                            "xml_file": xml_file,
                            "xml_path": xml_path,
                            "parameter_name": parameter_name,
                            "matched_value": self._redact(matched_value),
                            "matched_value_redacted": True,
                            "match_index": match_index,
                            "snippet": self._redact(match.group(0)),
                            "remediation": rag_fields["remediation"] or rule.description,
                        },
                    )
                )
        return findings

    def _build_recommendations(
        self,
        findings: list[AgentFinding],
    ) -> list[AgentRecommendation]:
        rule_ids = {finding.rule_triggered for finding in findings}
        recommendations: list[AgentRecommendation] = []

        if {"RULE-SEC-001", "RULE-SEC-005"} & rule_ids:
            rag_severity = resolve_severity("RULE-SEC-001")
            recommendations.append(
                AgentRecommendation(
                    id="SEC-REC-001",
                    title="Externalize secrets into a managed vault",
                    category="security",
                    severity=rag_severity,
                    priority="P1",
                    rule_triggered="RULE-SEC-001",
                    rationale="Hardcoded secrets increase exposure risk and complicate rotation.",
                    action="Move passwords, API keys, and tokens to vault-backed Talend contexts.",
                    expected_impact="Reduces credential exposure and supports controlled rotation.",
                )
            )

        if "RULE-SEC-002" in rule_ids:
            rag_severity = resolve_severity("RULE-SEC-002")
            recommendations.append(
                AgentRecommendation(
                    id="SEC-REC-002",
                    title="Remove inline JDBC connection strings",
                    category="security",
                    severity=rag_severity,
                    priority="P2",
                    rule_triggered="RULE-SEC-002",
                    rationale="Inline JDBC URLs often expose hosts, schemas, usernames, or credentials.",
                    action="Use centralized metadata connections and secure context variables.",
                    expected_impact="Improves connection governance and environment portability.",
                )
            )

        if "RULE-SEC-008" in rule_ids:
            rag_severity = resolve_severity("RULE-SEC-008")
            recommendations.append(
                AgentRecommendation(
                    id="SEC-REC-003",
                    title="Parameterize usernames per environment",
                    category="security",
                    severity=rag_severity,
                    priority="P3",
                    rule_triggered="RULE-SEC-008",
                    rationale="Static usernames reduce deployment portability and auditability.",
                    action="Replace literal usernames with context variables resolved at runtime.",
                    expected_impact="Improves environment separation and access review traceability.",
                )
            )

        return recommendations

    def _build_metrics(self, findings: list[AgentFinding]) -> dict:
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for finding in findings:
            by_severity[finding.severity.value] = by_severity.get(finding.severity.value, 0) + 1
            by_category[finding.category] = by_category.get(finding.category, 0) + 1

        return {
            "security_findings": len(findings),
            "security_findings_by_severity": by_severity,
            "security_findings_by_category": by_category,
        }

    def _dedupe_findings(self, findings: list[AgentFinding]) -> list[AgentFinding]:
        deduped: list[AgentFinding] = []
        seen: set[tuple] = set()
        for finding in findings:
            evidence = finding.evidence
            key = (
                evidence.get("rule_id"),
                evidence.get("xml_file"),
                evidence.get("xml_path"),
                evidence.get("matched_value"),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(finding)
        return deduped

    def _redact(self, value: str) -> str:
        if len(value) <= 12:
            return "***"
        return f"{value[:6]}***{value[-3:]}"

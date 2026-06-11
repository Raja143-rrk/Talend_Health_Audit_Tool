from backend.rule_engine.models import (
    RuleCategory,
    RuleDefinition,
    RuleScope,
    RuleThreshold,
)


def has_sensitive_parameter(component: dict, keywords: set[str]) -> bool:
    parameters = component.get("parameters") or {}
    for name, value in parameters.items():
        normalized_name = str(name).lower()
        normalized_value = str(value).lower()
        if any(keyword in normalized_name for keyword in keywords) and normalized_value:
            return True
    return False


SECURITY_RULES = [
    RuleDefinition(
        id="RULE-SEC-001",
        title="Hardcoded credential parameter",
        category=RuleCategory.SECURITY,
        scope=RuleScope.COMPONENT,
        description="A component contains a credential-like parameter value.",
        remediation="Move credentials to vault-backed or encrypted Talend context variables.",
        predicate=lambda component, _: has_sensitive_parameter(
            component,
            {"password", "passwd", "pwd", "secret", "token", "api_key", "apikey"},
        ),
    ),
    RuleDefinition(
        id="RULE-SEC-002",
        title="Inline JDBC URL",
        category=RuleCategory.SECURITY,
        scope=RuleScope.COMPONENT,
        description="A component contains an inline JDBC URL.",
        remediation="Use governed metadata connections and context variables instead of inline JDBC strings.",
        predicate=lambda component, _: any(
            str(value).lower().startswith("jdbc:")
            for value in (component.get("parameters") or {}).values()
        ),
    ),
    RuleDefinition(
        id="RULE-SEC-003",
        title="High number of security findings",
        category=RuleCategory.SECURITY,
        scope=RuleScope.INVENTORY,
        description="The analysis contains more security findings than the configured threshold.",
        remediation="Prioritize risk and critical risk security findings before release.",
        thresholds=[RuleThreshold(field="security_findings_count", operator=">", value=5)],
        predicate=lambda inventory, _: len(inventory.get("security_findings", [])) > 5,
    ),
    RuleDefinition(
        id="RULE-SEC-004",
        title="Missing or unencrypted credential context variables",
        category=RuleCategory.SECURITY,
        scope=RuleScope.INVENTORY,
        description="The project uses credential values but has no corresponding encrypted context variables.",
        remediation="Audit context definitions for missing variables and enable encryption on sensitive ones.",
        predicate=lambda inventory, _: len(inventory.get("contexts", [])) == 0,
    ),
    RuleDefinition(
        id="RULE-SEC-005",
        title="API key or token exposed in component",
        category=RuleCategory.SECURITY,
        scope=RuleScope.COMPONENT,
        description="An API key, bearer token, or OAuth secret is embedded in a component parameter.",
        remediation="Revoke and rotate the exposed key immediately. Store new credentials in encrypted context variables.",
        predicate=lambda component, _: has_sensitive_parameter(
            component,
            {"api_key", "apikey", "bearer", "token", "oauth", "client_secret", "access_key", "auth_token"},
        ),
    ),
    RuleDefinition(
        id="RULE-SEC-006",
        title="Insecure database connection configuration",
        category=RuleCategory.SECURITY,
        scope=RuleScope.COMPONENT,
        description="A database connection is configured without TLS/SSL or with security-weakening settings.",
        remediation="Enable TLS/SSL per database type. Set useSSL=true, sslmode=verify-full, or encrypt=true as appropriate.",
        predicate=lambda component, _: any(
            str(value).lower() in {"false", "disable", "allow", "prefer"}
            for key, value in (component.get("parameters") or {}).items()
            if str(key).lower() in {"usessl", "ssl", "sslmode", "encrypt", "trustallcertificates", "allowpublickeyretrieval"}
        ),
    ),
    RuleDefinition(
        id="RULE-SEC-007",
        title="Cross-environment context exposure",
        category=RuleCategory.SECURITY,
        scope=RuleScope.INVENTORY,
        description="Production-like values detected in context variable defaults or non-production context files.",
        remediation="Create distinct context groups per environment. Move production values out of defaults.",
        predicate=lambda inventory, _: False,
    ),
]

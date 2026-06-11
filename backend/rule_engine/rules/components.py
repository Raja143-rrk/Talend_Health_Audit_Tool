import re

from backend.rule_engine.models import RuleCategory, RuleDefinition, RuleScope, RuleThreshold

DEFAULT_NAME_PATTERN = re.compile(r"^[\w]+_\d+$")

COMPONENT_RULES = [
    RuleDefinition(
        id="RULE-COMP-001",
        title="Disabled component present",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.COMPONENT,
        description="A disabled component remains in the job design.",
        remediation="Remove obsolete disabled components or document why they are intentionally retained.",
        predicate=lambda component, _: bool(component.get("disabled")),
    ),
    RuleDefinition(
        id="RULE-COMP-002",
        title="Large job component count",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job contains more components than the configured maintainability threshold.",
        remediation="Split large jobs into reusable subjobs or simplify orchestration boundaries.",
        thresholds=[RuleThreshold(field="component_count", operator=">", value=50)],
        predicate=lambda job, _: len(job.get("components", [])) > 50,
    ),
    RuleDefinition(
        id="RULE-COMP-003",
        title="Naming convention violation",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job contains components using default Talend-generated names instead of purpose-revealing names.",
        remediation="Establish a team-wide naming convention and rename default-named components.",
        predicate=lambda job, _: any(
            bool(DEFAULT_NAME_PATTERN.match(str(c.get("name") or "")))
            for c in job.get("components", [])
            if not c.get("disabled")
        ),
    ),
    RuleDefinition(
        id="RULE-COMP-004",
        title="Missing component documentation",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.COMPONENT,
        description="A complex component lacks documentation notes explaining its transformation logic or business rules.",
        remediation="Identify all undocumented complex components and add documentation explaining the business rule.",
        predicate=lambda component, _: False,
    ),
    RuleDefinition(
        id="RULE-COMP-005",
        title="Inconsistent error handling",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job with tMap components does not implement reject flows for mapping operations.",
        remediation="Add reject flows to all tMap components. Wrap critical write operations with tTryCatch.",
        predicate=lambda job, _: any(
            str(c.get("component_name", "")).lower() == "tmap"
            for c in job.get("components", [])
        ),
    ),
    RuleDefinition(
        id="RULE-COMP-006",
        title="Duplicate component configuration",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job contains multiple components with identical or near-identical configuration.",
        remediation="Identify duplicate configurations. Extract into tMetadataConnection or reusable routines.",
        predicate=lambda job, _: False,
    ),
    RuleDefinition(
        id="RULE-COMP-007",
        title="Missing reusable component extraction",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.INVENTORY,
        description="Patterns appear repeatedly across the project that have not been extracted into shared routines.",
        remediation="Identify repeated patterns and extract them into Talend routines or subjobs.",
        predicate=lambda inventory, _: False,
    ),
    RuleDefinition(
        id="RULE-COMP-008",
        title="Missing metadata reuse",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job uses inline connection configuration instead of referencing governed metadata connections.",
        remediation="Create governed metadata connections for each distinct database and file schema.",
        predicate=lambda job, _: False,
    ),
    RuleDefinition(
        id="RULE-COMP-009",
        title="Missing context standardization",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job hardcodes environment-specific values instead of using context variables.",
        remediation="Scan all component parameters for hardcoded environment values and replace with context variable references.",
        predicate=lambda job, _: False,
    ),
    RuleDefinition(
        id="RULE-COMP-010",
        title="Unused components and context variables",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job contains active components not connected downstream or context variables never referenced.",
        remediation="Inspect and remove unused components and context variables. Schedule quarterly audits.",
        predicate=lambda job, _: False,
    ),
]

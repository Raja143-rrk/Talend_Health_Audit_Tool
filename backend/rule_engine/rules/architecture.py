from backend.rule_engine.models import RuleCategory, RuleDefinition, RuleScope, RuleThreshold

ARCHITECTURE_RULES = [
    RuleDefinition(
        id="RULE-ARCH-001",
        title="No contexts detected",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="No Talend contexts were detected in the parsed inventory.",
        remediation="Introduce environment-specific contexts for configuration, credentials, and runtime portability.",
        predicate=lambda inventory, _: len(inventory.get("contexts", [])) == 0,
    ),
    RuleDefinition(
        id="RULE-ARCH-002",
        title="High source/target system spread",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project integrates with many source and target system types.",
        remediation="Review architecture boundaries and standardize connection governance for high-spread integrations.",
        thresholds=[RuleThreshold(field="system_count", operator=">", value=8)],
        predicate=lambda inventory, _: len(
            set(inventory.get("source_systems", [])) | set(inventory.get("target_systems", []))
        )
        > 8,
    ),
    RuleDefinition(
        id="RULE-ARCH-003",
        title="Missing error handling",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.JOB,
        description="A job performs write operations without error handling — no tTryCatch, reject flows, or error triggers.",
        remediation="Add tTryCatch around critical write sections. Add reject flows to upstream tMap components.",
        predicate=lambda job, _: any(
            "output" in str(c.get("component_name", "")).lower()
            for c in job.get("components", [])
        ),
    ),
    RuleDefinition(
        id="RULE-ARCH-004",
        title="No CI/CD pipeline detected",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project workspace does not contain any CI/CD configuration files.",
        remediation="Choose a CI/CD platform and create the pipeline configuration file for automated builds.",
        predicate=lambda inventory, _: False,
    ),
    RuleDefinition(
        id="RULE-ARCH-005",
        title="Inconsistent logging across jobs",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="Jobs within the same project use different logging approaches or have no logging at all.",
        remediation="Define a standard logging approach and create a reusable logging subjob.",
        predicate=lambda inventory, _: False,
    ),
    RuleDefinition(
        id="RULE-ARCH-006",
        title="Missing governed metadata connections",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project uses components with inline connection parameters instead of governed tMetadataConnection.",
        remediation="Create governed metadata connections and replace inline components with metadata-referencing versions.",
        predicate=lambda inventory, _: False,
    ),
    RuleDefinition(
        id="RULE-ARCH-007",
        title="Missing parent/child job decomposition",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.JOB,
        description="A job exceeds 50 components and does not use tRunJob to delegate processing to child jobs.",
        remediation="Analyze the monolithic job, identify distinct stages, and extract each into a focused child job.",
        predicate=lambda job, _: (
            len(job.get("components", [])) > 50
            and not any(
                str(c.get("component_name", "")).lower() == "trunjob"
                for c in job.get("components", [])
            )
        ),
    ),
    RuleDefinition(
        id="RULE-ARCH-008",
        title="Missing joblet usage for reusable logic",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project contains no joblets despite having many jobs with repeatable patterns.",
        remediation="Identify repeatable patterns and create joblets for each candidate.",
        predicate=lambda inventory, _: False,
    ),
    RuleDefinition(
        id="RULE-ARCH-009",
        title="Missing standardized error framework",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project has no consistent error framework across jobs.",
        remediation="Design a shared error record schema and create a reusable error handler subjob.",
        predicate=lambda inventory, _: False,
    ),
    RuleDefinition(
        id="RULE-ARCH-010",
        title="Missing monitoring and alerting",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project does not implement monitoring infrastructure — no metrics, health checks, or alerting.",
        remediation="Create a shared metrics table and reusable metrics subjob. Configure monitoring dashboards.",
        predicate=lambda inventory, _: False,
    ),
    RuleDefinition(
        id="RULE-ARCH-011",
        title="Missing exception classification and framework",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project has no structured exception handling framework or retry logic.",
        remediation="Create exception classification, implement retry logic with backoff, and create a global exception handler subjob.",
        predicate=lambda inventory, _: False,
    ),
]

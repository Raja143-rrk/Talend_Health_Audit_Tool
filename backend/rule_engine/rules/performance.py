from backend.rule_engine.models import (
    RuleCategory,
    RuleDefinition,
    RuleScope,
    RuleThreshold,
)

def count_components(job: dict, component_names: set[str]) -> int:
    return sum(
        1
        for component in job.get("components", [])
        if str(component.get("component_name", "")).lower() in component_names
        and not component.get("disabled", False)
    )

def has_small_commit(component: dict, threshold: int) -> bool:
    parameters = component.get("parameters") or {}
    raw_value = (
        parameters.get("COMMIT_EVERY")
        or parameters.get("COMMIT_SIZE")
        or parameters.get("BATCH_SIZE")
    )
    if raw_value is None:
        return False
    try:
        return int(str(raw_value).strip('"')) <= threshold
    except ValueError:
        return False

PERFORMANCE_RULES = [
    RuleDefinition(
        id="RULE-PERF-001",
        title="Excessive custom Java components",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.JOB,
        description="A job uses more custom Java components than the configured threshold.",
        remediation="Replace repeated custom Java logic with native Talend components or reusable routines.",
        thresholds=[RuleThreshold(field="tjava_count", operator=">=", value=3)],
        predicate=lambda job, _: count_components(job, {"tjava", "tjavarow", "tjavaflex"}) >= 3,
    ),
    RuleDefinition(
        id="RULE-PERF-002",
        title="Heavy tMap usage",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.JOB,
        description="A job has multiple active tMap components.",
        remediation="Split complex mappings and push joins or filters to source systems when possible.",
        thresholds=[RuleThreshold(field="tmap_count", operator=">=", value=3)],
        predicate=lambda job, _: count_components(job, {"tmap"}) >= 3,
    ),
    RuleDefinition(
        id="RULE-PERF-003",
        title="Small commit interval",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.COMPONENT,
        description="A target component uses a small commit or batch interval.",
        remediation="Tune commit size for bulk loads after validating rollback and recovery requirements.",
        thresholds=[RuleThreshold(field="commit_size", operator="<=", value=100)],
        predicate=lambda component, _: "output" in str(component.get("component_name", "")).lower()
        and has_small_commit(component, 100),
    ),
    RuleDefinition(
        id="RULE-PERF-004",
        title="Missing source pushdown",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.JOB,
        description="A job reads a database table without filtering, then filters downstream in Talend components.",
        remediation="Replace table-level tDBInput with custom SQL incorporating WHERE filters and column selection.",
        predicate=lambda job, _: False,
    ),
    RuleDefinition(
        id="RULE-PERF-005",
        title="Inefficient lookup configuration",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.COMPONENT,
        description="A tMap lookup uses an inefficient match model or loads a lookup table unnecessarily.",
        remediation="Audit lookup patterns. Eliminate duplicated lookups. Optimize match models based on selectivity.",
        predicate=lambda component, _: False,
    ),
    RuleDefinition(
        id="RULE-PERF-006",
        title="Missing parallelization in loops",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.JOB,
        description="A job uses tLoop or tForEach without parallel processing for independent iterations.",
        remediation="Add tParallelize after the looping component. Set Max parallel jobs based on available CPU cores.",
        predicate=lambda job, _: any(
            str(c.get("component_name", "")).lower() in {"tloop", "tforeach", "tfilelist"}
            and not any(
                str(o.get("component_name", "")).lower() == "tparallelize"
                for o in job.get("components", [])
            )
            for c in job.get("components", [])
        ),
    ),
    RuleDefinition(
        id="RULE-PERF-007",
        title="Excessive memory allocation",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.JOB,
        description="A job is configured with suboptimal memory settings or uses in-memory operations for large datasets.",
        remediation="Right-size JVM heap based on data volume. Use disk-spilling alternatives for large lookups.",
        predicate=lambda job, _: False,
    ),
    RuleDefinition(
        id="RULE-PERF-008",
        title="Excessive component redundancy",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.JOB,
        description="A job contains redundant components that add processing overhead without business value.",
        remediation="Identify redundant components and merge, simplify, or remove them.",
        predicate=lambda job, _: False,
    ),
    RuleDefinition(
        id="RULE-PERF-009",
        title="Monolithic subjob structure",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.JOB,
        description="A single job combines extract, transform, and load operations without subjob decomposition.",
        remediation="Decompose into focused subjobs using tRunJob in a parent orchestrator.",
        predicate=lambda job, _: (
            len(job.get("components", [])) > 30
            and not any(
                str(c.get("component_name", "")).lower() == "trunjob"
                for c in job.get("components", [])
            )
        ),
    ),
]

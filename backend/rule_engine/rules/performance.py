from backend.rule_engine.models import (
    RuleCategory,
    RuleDefinition,
    RuleScope,
    RuleThreshold,
)

_DB_INPUT_TYPES = {
    "tdbinput", "tdbinputodbc",
    "tmysqlinput", "toracleinput", "tpostgresqlinput",
    "tmssqlinput", "tsnowflakeinput", "tredshiftinput",
    "tgreenpluminput", "tteradatainput",
}

_LARGE_BUFFER_COMPS = {"tbufferoutput", "tadvancedfileoutputxml", "tfileoutputdelimited"}


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


def _is_table_mode_db_input(component: dict) -> bool:
    name = str(component.get("component_name", "")).lower()
    if name not in _DB_INPUT_TYPES:
        return False
    params = component.get("parameters") or {}
    use_query = str(params.get("USE_QUERY") or "").lower()
    sql = str(params.get("SQL_QUERY") or "").strip()
    return use_query != "true" or not sql


def _has_inefficient_lookup(component: dict) -> bool:
    if str(component.get("component_name", "")).lower() != "tmap":
        return False
    params = component.get("parameters") or {}
    return str(params.get("LOOKUP_MATCH_MODEL") or "").upper() == "ALL_ROWS"


def _has_large_buffer_allocation(component: dict) -> bool:
    name = str(component.get("component_name", "")).lower()
    if name not in _LARGE_BUFFER_COMPS:
        return False
    params = component.get("parameters") or {}
    raw = params.get("BUFFER_SIZE") or params.get("NB_LINE") or ""
    try:
        return int(raw.strip('"')) > 10000
    except (ValueError, AttributeError):
        return False


def _component_config_signature(component: dict) -> str:
    params = component.get("parameters", {})
    skip = {"UNIQUE_NAME", "NAME", "LABEL", "SUPPORT_CONTEXT"}
    sorted_items = sorted(
        (k, v) for k, v in params.items() if k not in skip
    )
    import json
    return json.dumps(sorted_items, sort_keys=True)


def _has_duplicate_configs(job: dict) -> bool:
    seen: dict[str, list[str]] = {}
    for comp in job.get("components", []):
        if comp.get("disabled"):
            continue
        sig = _component_config_signature(comp)
        seen.setdefault(sig, []).append(str(comp.get("name", "")))
    return any(len(names) >= 2 for names in seen.values())

PERFORMANCE_RULES = [
    RuleDefinition(
        id="RULE-PERF-010",
        title="Missing execution runtime monitoring",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.INVENTORY,
        description="The project has no tFlowMeter components to capture component-level execution times and row counts.",
        remediation="Add tFlowMeter components at key stages in each job to identify high-latency bottlenecks during execution.",
        predicate=lambda inventory, _: not any(
            str(c.get("component_name", "")).lower() == "tflowmeter"
            for job in inventory.get("jobs", [])
            for c in job.get("components", [])
            if not c.get("disabled")
        ),
    ),
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
        predicate=lambda job, _: any(
            _is_table_mode_db_input(c)
            for c in job.get("components", [])
            if not c.get("disabled")
        ),
    ),
    RuleDefinition(
        id="RULE-PERF-005",
        title="Inefficient lookup configuration",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.COMPONENT,
        description="A tMap lookup uses an inefficient match model or loads a lookup table unnecessarily.",
        remediation="Audit lookup patterns. Eliminate duplicated lookups. Optimize match models based on selectivity.",
        predicate=lambda component, _: _has_inefficient_lookup(component),
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
        predicate=lambda job, _: any(
            _has_large_buffer_allocation(c)
            for c in job.get("components", [])
            if not c.get("disabled")
        ),
    ),
    RuleDefinition(
        id="RULE-PERF-008",
        title="Excessive component redundancy",
        category=RuleCategory.PERFORMANCE,
        scope=RuleScope.JOB,
        description="A job contains redundant components that add processing overhead without business value.",
        remediation="Identify redundant components and merge, simplify, or remove them.",
        predicate=lambda job, _: _has_duplicate_configs(job),
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

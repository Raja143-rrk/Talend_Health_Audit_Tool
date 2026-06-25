import json
import re
from collections import Counter
from contextlib import suppress

from backend.rule_engine.models import RuleCategory, RuleDefinition, RuleScope, RuleThreshold

DEFAULT_NAME_PATTERN = re.compile(r"^[\w]+_\d+$")


def _component_config_signature(component: dict) -> str:
    params = component.get("parameters", {})
    skip = {"UNIQUE_NAME", "NAME", "LABEL", "SUPPORT_CONTEXT"}
    sorted_items = sorted(
        (k, v) for k, v in params.items() if k not in skip
    )
    return json.dumps(sorted_items, sort_keys=True)


def _has_duplicate_configs(job: dict) -> bool:
    seen: dict[str, list[str]] = {}
    for comp in job.get("components", []):
        if comp.get("disabled"):
            continue
        sig = _component_config_signature(comp)
        seen.setdefault(sig, []).append(str(comp.get("name", "")))
    return any(len(names) >= 2 for names in seen.values())


def _normalized_job_sequence(job: dict) -> tuple[str, ...]:
    return tuple(
        str(c.get("component_name", "")).lower()
        for c in job.get("components", [])
        if not c.get("disabled")
    )


def _has_repeated_pattern(inventory: dict) -> bool:
    windows: Counter[tuple[str, ...]] = Counter()
    for job in inventory.get("jobs", []):
        seq = _normalized_job_sequence(job)
        windows.update(zip(seq, seq[1:], strict=False))
    return any(count >= 3 for count in windows.values())


def _has_hardcoded_env_values(job: dict) -> bool:
    env_pattern = re.compile(
        r"(?:localhost|127\.0\.0\.1|[\\/]data[\\/]|:5432|:3306|:1433|/var/|C:\\\\)",
        re.IGNORECASE,
    )
    for comp in job.get("components", []):
        if comp.get("disabled"):
            continue
        for value in comp.get("parameters", {}).values():
            sv = str(value)
            if sv.startswith("context."):
                continue
            if env_pattern.search(sv):
                return True
    return False


_LEFTOVER_KEYWORDS = {"unused", "disabled_copy", "test", "debug", "temp", "temp_", "_temp", "dump", "backup", "old", "deprecated", "remove", "delete_", "zz_", "_zz", "sandbox", "wip", "scratch"}


def _has_orphan_components(job: dict) -> bool:
    connections = job.get("connections", [])
    if connections:
        connected_ids: set[str] = set()
        for conn in connections:
            sid = conn.get("source_id")
            tid = conn.get("target_id")
            if sid:
                connected_ids.add(sid)
            if tid:
                connected_ids.add(tid)
        for comp in job.get("components", []):
            if comp.get("disabled"):
                continue
            comp_id = str(comp.get("id", "") or "")
            if comp_id and comp_id not in connected_ids:
                return True
        return False
    return any(
        any(kw in str(c.get("name", "")).lower() for kw in _LEFTOVER_KEYWORDS)
        for c in job.get("components", [])
        if not c.get("disabled")
    )


def _has_cross_job_duplicates(inventory: dict) -> bool:
    lookup_sigs: dict[str, list[str]] = {}
    for job in inventory.get("jobs", []):
        for comp in job.get("components", []):
            if comp.get("disabled"):
                continue
            if str(comp.get("component_name", "")).lower() != "tmap":
                continue
            params = comp.get("parameters", {})
            lookup_params = {
                k: v for k, v in params.items()
                if "LOOKUP" in k.upper() or k in ("TABLE", "SQL_QUERY")
            }
            if not lookup_params:
                continue
            sig = json.dumps(sorted(lookup_params.items()), sort_keys=True)
            label = f"{job.get('name', '?')}/{comp.get('name', '?')}"
            lookup_sigs.setdefault(sig, []).append(label)
    return any(len(locations) >= 3 for locations in lookup_sigs.values())


_TMAP_LOOKUP_RE = re.compile(r"LOOKUP_\d+_TABLE", re.IGNORECASE)
_TMAP_EXPR_PARAM_RE = re.compile(r"OUTPUT_\d+_EXPRESSION_\d+|OUTPUT_EXPRESSION_\d+", re.IGNORECASE)


def _has_overly_complex_tmap(component: dict) -> bool:
    if str(component.get("component_name", "")).lower() != "tmap":
        return False
    params = component.get("parameters", {})
    lookup_count = sum(1 for k in params if _TMAP_LOOKUP_RE.match(k))
    nb_lines: list[int] = []
    for k, v in params.items():
        if k.upper().startswith("NB_LINE"):
            with suppress(ValueError):
                nb_lines.append(int(str(v).strip('"')))
    total_expr = sum(nb_lines) if nb_lines else sum(1 for k in params if _TMAP_EXPR_PARAM_RE.match(k))
    return lookup_count >= 5 or total_expr >= 50


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
        predicate=lambda component, _: (
            str(component.get("component_name", "")).lower()
            in {"tmap", "tjava", "tjavarow", "txmlmap", "tfileinputdelimited", "tfileinputpositional"}
            and not any(
                str(key).lower() in {"notes", "note", "documentation", "comment", "description"}
                and str(value).strip()
                for key, value in (component.get("parameters") or {}).items()
            )
        ),
    ),
    RuleDefinition(
        id="RULE-COMP-005",
        title="Duplicate component configuration",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job contains multiple components with identical or near-identical configuration.",
        remediation="Identify duplicate configurations. Extract into tMetadataConnection or reusable routines.",
        predicate=lambda job, _: _has_duplicate_configs(job),
    ),
    RuleDefinition(
        id="RULE-COMP-006",
        title="Missing reusable component extraction",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.INVENTORY,
        description="Patterns appear repeatedly across the project that have not been extracted into shared routines.",
        remediation="Identify repeated patterns and extract them into Talend routines or subjobs.",
        predicate=lambda inventory, _: _has_repeated_pattern(inventory),
    ),
    RuleDefinition(
        id="RULE-COMP-007",
        title="Missing context standardization",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job hardcodes environment-specific values instead of using context variables.",
        remediation="Scan all component parameters for hardcoded environment values and replace with context variable references.",
        predicate=lambda job, _: _has_hardcoded_env_values(job),
    ),
    RuleDefinition(
        id="RULE-COMP-008",
        title="Orphaned or leftover components",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.JOB,
        description="A job contains active components that are disconnected from the flow graph or appear to be leftover test artifacts.",
        remediation="Inspect and remove orphaned components. Schedule quarterly audits to keep job designs clean.",
        predicate=lambda job, _: _has_orphan_components(job),
    ),
    RuleDefinition(
        id="RULE-COMP-009",
        title="Cross-job duplicate component configuration",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.INVENTORY,
        description="Identical component configurations appear in three or more jobs, indicating missed reuse opportunities for lookup datasets and transformation logic.",
        remediation="Extract duplicate configurations into shared routines, tMetadataConnection, or reusable subjobs.",
        predicate=lambda inventory, _: _has_cross_job_duplicates(inventory),
    ),
    RuleDefinition(
        id="RULE-COMP-010",
        title="Overly complex tMap mapping",
        category=RuleCategory.COMPONENT,
        scope=RuleScope.COMPONENT,
        description="A tMap component has excessive lookup tables (≥5) or expression output lines (≥50), indicating a monolithic mapping that should be decomposed.",
        remediation="Split the tMap into multiple simpler tMap stages or extract reusable lookups into dedicated subjobs.",
        predicate=lambda component, _: _has_overly_complex_tmap(component),
    ),
]

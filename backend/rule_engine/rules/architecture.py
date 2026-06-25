import re
from pathlib import Path

from backend.rule_engine.models import RuleCategory, RuleDefinition, RuleScope, RuleThreshold

_CONTEXT_REF_RE = re.compile(r"context\.(\w+)", re.IGNORECASE)

_CI_CD_PATTERNS = (
    ".github/workflows/",
    "Jenkinsfile",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    ".drone.yml",
    "buildspec.yml",
)


def _has_untracked_context_vars(inventory: dict) -> bool:
    defined_names: set[str] = set()
    for group in inventory.get("context_groups", []):
        for param in group.get("parameters", []):
            pn = str(param.get("name", "")).strip()
            if pn:
                defined_names.add(pn.lower())

    referenced_names: set[str] = set()
    for job in inventory.get("jobs", []):
        for comp in job.get("components", []):
            if comp.get("disabled"):
                continue
            for value in comp.get("parameters", {}).values():
                for match in _CONTEXT_REF_RE.finditer(str(value)):
                    referenced_names.add(match.group(1).lower())

    untracked = referenced_names - defined_names
    return bool(untracked)


def _has_cicd_config(inventory: dict) -> bool:
    for key in ("item_files", "property_files", "project_files"):
        for fp in inventory.get(key, []):
            lower_fp = str(fp).lower()
            if any(pattern.lower() in lower_fp for pattern in _CI_CD_PATTERNS):
                return True
    workspace = inventory.get("workspace_path")
    if workspace:
        ws = Path(workspace)
        if ws.is_dir():
            for pattern in ("*.github/workflows/*.yml", "Jenkinsfile", ".gitlab-ci.yml"):
                matching = list(ws.glob(pattern)) if "*" in pattern else [ws / pattern]
                if any(p.is_file() for p in matching):
                    return True
    return False


def _has_joblet_files(inventory: dict) -> bool:
    for fp in inventory.get("item_files", []):
        if ".joblet" in str(fp).lower():
            return True
    for job in inventory.get("jobs", []):
        for comp in job.get("components", []):
            if str(comp.get("component_name", "")).lower() == "tjoblet":
                return True
    return False


def _log_coverage(inventory: dict) -> float:
    jobs = inventory.get("jobs", [])
    if not jobs:
        return 0.0
    logged = sum(
        1 for job in jobs
        if any(
            str(c.get("component_name", "")).lower() in {"tlogrow", "tlogcatcher", "tstatscatcher", "tflowmeter"}
            for c in job.get("components", [])
            if not c.get("disabled")
        )
    )
    return logged / len(jobs)


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
        predicate=lambda inventory, _: not _has_cicd_config(inventory),
    ),
    RuleDefinition(
        id="RULE-ARCH-005",
        title="Inconsistent logging across jobs",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="Jobs within the same project use different logging approaches or have no logging at all.",
        remediation="Define a standard logging approach and create a reusable logging subjob.",
        predicate=lambda inventory, _: _log_coverage(inventory) < 0.8,
    ),
    RuleDefinition(
        id="RULE-ARCH-006",
        title="Missing governed metadata connections",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project uses components with inline connection parameters instead of governed tMetadataConnection.",
        remediation="Create governed metadata connections and replace inline components with metadata-referencing versions.",
        predicate=lambda inventory, _: any(
            str(c.get("component_name", "")).lower()
            in {"tjdbcconnection", "tmysqlconnection", "toracleconnection", "tpostgresqlconnection",
                "tmssqlconnection", "tsnowflakeconnection", "tredshiftconnection", "tdbconnection"}
            for job in inventory.get("jobs", [])
            for c in job.get("components", [])
            if not c.get("disabled")
        ) and not any(
            str(c.get("component_name", "")).lower() == "tmetadataconnection"
            for job in inventory.get("jobs", [])
            for c in job.get("components", [])
        ),
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
        predicate=lambda inventory, _: not _has_joblet_files(inventory),
    ),
    RuleDefinition(
        id="RULE-ARCH-009",
        title="Missing standardized error framework",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project has no consistent error framework across jobs.",
        remediation="Design a shared error record schema and create a reusable error handler subjob.",
        predicate=lambda inventory, _: not any(
            str(c.get("component_name", "")).lower() == "ttrycatch"
            for job in inventory.get("jobs", [])
            for c in job.get("components", [])
        ),
    ),
    RuleDefinition(
        id="RULE-ARCH-010",
        title="Missing monitoring and alerting",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project does not implement monitoring infrastructure — no metrics, health checks, or alerting.",
        remediation="Create a shared metrics table and reusable metrics subjob. Configure monitoring dashboards.",
        predicate=lambda inventory, _: not any(
            str(c.get("component_name", "")).lower()
            in {"tlogrow", "tstatscatcher", "tflowmeter", "taggregaterow"}
            for job in inventory.get("jobs", [])
            for c in job.get("components", [])
            if not c.get("disabled")
        ),
    ),
    RuleDefinition(
        id="RULE-ARCH-011",
        title="Missing exception classification and framework",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="The project has no structured exception handling framework or retry logic.",
        remediation="Create exception classification, implement retry logic with backoff, and create a global exception handler subjob.",
        predicate=lambda inventory, _: not any(
            str(c.get("component_name", "")).lower()
            in {"ttrycatch", "terrorhandler", "tlogcatcher", "twarn", "tdie"}
            for job in inventory.get("jobs", [])
            for c in job.get("components", [])
        ),
    ),
    RuleDefinition(
        id="RULE-ARCH-012",
        title="Untracked context variable references",
        category=RuleCategory.ARCHITECTURE,
        scope=RuleScope.INVENTORY,
        description="Component parameters reference context variables that are not defined in any context group.",
        remediation="Define all referenced context variables in the appropriate context group. Remove unused context references.",
        predicate=lambda inventory, _: _has_untracked_context_vars(inventory),
    ),
]

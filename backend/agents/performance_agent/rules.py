from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceRule:
    id: str
    title: str
    category: str
    recommendation: str
    optimization_suggestion: str
    predicate: Callable[[dict], bool]


def component_name(component: dict) -> str:
    return str(component.get("component_name") or "").lower()


def parameter_value(component: dict, *keys: str) -> str | None:
    parameters = component.get("parameters") or {}
    normalized = {str(key).upper(): str(value) for key, value in parameters.items()}
    for key in keys:
        value = normalized.get(key.upper())
        if value not in {None, ""}:
            return value
    return None


def is_enabled(component: dict) -> bool:
    return not bool(component.get("disabled"))


def is_tjava(component: dict) -> bool:
    return component_name(component) in {"tjava", "tjavarow", "tjavaflex"}


def is_row_processing(component: dict) -> bool:
    name = component_name(component)
    return name in {"tjavarow", "tflowtoiterate", "titeratetoflow"} or "row" in name


def is_loop(component: dict) -> bool:
    name = component_name(component)
    return "loop" in name or name in {"tforeach", "tfilelist", "tloop"}


def is_parallel_component(component: dict) -> bool:
    name = component_name(component)
    return name in {"tparallelize", "tpartitioner", "tcollector"}


def is_input_or_output(component: dict) -> bool:
    name = component_name(component)
    return "input" in name or "output" in name


def is_tmap(component: dict) -> bool:
    return component_name(component) == "tmap"


def commit_size(component: dict) -> int | None:
    raw_value = parameter_value(
        component,
        "COMMIT_EVERY",
        "COMMIT_SIZE",
        "BATCH_SIZE",
        "NB_LINE",
    )
    if raw_value is None:
        return None

    try:
        return int(raw_value.strip('"'))
    except ValueError:
        return None


DEFAULT_PERFORMANCE_RULES = [
    PerformanceRule(
        id="PERF-TJAVA-001",
        title="Excessive tJava usage",
        category="excessive_tjava",
        recommendation="Reduce custom Java components in favor of native Talend components.",
        optimization_suggestion="Replace repeated tJava/tJavaRow/tJavaFlex logic with tMap, tFilterRow, tNormalize, reusable routines, or database pushdown where appropriate.",
        predicate=lambda job: sum(
            1 for component in job.get("components", []) if is_enabled(component) and is_tjava(component)
        )
        >= 3,
    ),
    PerformanceRule(
        id="PERF-LOOP-001",
        title="Nested or repeated loop processing detected",
        category="nested_loops",
        recommendation="Avoid nested iteration over row data in Talend jobs.",
        optimization_suggestion="Replace nested loops with joins, lookups, tMap joins, database-side SQL, or pre-aggregated datasets.",
        predicate=lambda job: sum(
            1 for component in job.get("components", []) if is_enabled(component) and is_loop(component)
        )
        >= 2,
    ),
    PerformanceRule(
        id="PERF-ROW-001",
        title="Row-by-row processing pattern detected",
        category="row_processing",
        recommendation="Minimize row-by-row operations for high-volume flows.",
        optimization_suggestion="Use set-based database operations, bulk components, tMap expressions, or batch-oriented processing instead of per-row Java/iterate flows.",
        predicate=lambda job: any(
            is_enabled(component) and is_row_processing(component)
            for component in job.get("components", [])
        ),
    ),
    PerformanceRule(
        id="PERF-PARALLEL-001",
        title="Missing parallelization opportunity",
        category="missing_parallelization",
        recommendation="Evaluate parallel execution for independent source/target branches.",
        optimization_suggestion="Use tParallelize, partitioning, or multi-thread execution only where branches are independent and target systems can handle concurrency.",
        predicate=lambda job: (
            sum(
                1
                for component in job.get("components", [])
                if is_enabled(component) and is_input_or_output(component)
            )
            >= 4
            and not any(
                is_enabled(component) and is_parallel_component(component)
                for component in job.get("components", [])
            )
        ),
    ),
    PerformanceRule(
        id="PERF-COMMIT-001",
        title="Commit size issue detected",
        category="commit_size_issues",
        recommendation="Tune commit and batch sizes for database output components.",
        optimization_suggestion="Use larger commit intervals for bulk loads after validating rollback tolerance, logging requirements, and target database capacity.",
        predicate=lambda job: any(
            is_enabled(component)
            and "output" in component_name(component)
            and commit_size(component) is not None
            and commit_size(component) <= 100
            for component in job.get("components", [])
        ),
    ),
    PerformanceRule(
        id="PERF-TMAP-001",
        title="Heavy tMap usage",
        category="heavy_tmap_usage",
        recommendation="Review complex tMap-heavy flows for maintainability and runtime cost.",
        optimization_suggestion="Split very large mappings, push joins/filters to the source database, and reuse lookup datasets where possible.",
        predicate=lambda job: sum(
            1 for component in job.get("components", []) if is_enabled(component) and is_tmap(component)
        )
        >= 3,
    ),
]

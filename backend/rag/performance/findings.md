# Performance Findings

---

## RULE-PERF-001: Excessive Custom Java Components

**rule_id:** RULE-PERF-001
**category:** performance
**title:** Excessive custom Java components
**description:** A job uses 3 or more custom Java components (tJava, tJavaRow, tJavaFlex). Custom Java code bypasses Talend's optimized code generation and forced-optimization engine, resulting in less efficient bytecode. Each component creates a separate class instance, increasing compilation overhead and memory footprint.

**detection_logic:** Parse all components within a job. Count instances of tJava, tJavaRow, and tJavaFlex where `activated` or `enabled` is true (active components only). If the count is 3 or greater, flag the job.

**impact:** Custom Java components execute as user-written code that cannot be optimized by Talend's engine. They increase job compilation time, reduce runtime performance, complicate migration to other platforms, and create maintainability challenges. Excessive tJava usage prevents Talend from applying built-in performance optimizations such as automatic parallelization and memory management. This is an active job-level performance finding with a 5-point deduction.

**classification:** Risk — Significant performance impact; represents a memory bottleneck.
**remediation:** Audit custom Java components and classify each by purpose. Replace standard transformations with native Talend components (tMap expressions, routines). Extract remaining custom logic into reusable Talend routines. Consider splitting the job to isolate custom logic in a dedicated subjob. See Performance Remediation → Fixing Excessive Custom Java (RULE-PERF-001) for detailed steps.

**source:** Talend Health Analyzer performance rule engine

---

## RULE-PERF-002: Heavy tMap Usage

**rule_id:** RULE-PERF-002
**category:** performance
**title:** Heavy tMap usage
**description:** A job has 3 or more active tMap components. Multiple tMap components indicate complex mapping logic that could be simplified, consolidated, or pushed to the source database. Each tMap adds per-row processing overhead and increases memory consumption for lookup data structures.

**detection_logic:** Parse all components within a job. Count instances of tMap where `activated` or `enabled` is true. If the count is 3 or greater, flag the job. Exclude tMap components used exclusively for simple pass-through (no expression or lookup configured).

**impact:** Each additional tMap adds processing latency per row. Multiple tMaps loading the same lookup tables waste memory and initialization time. Complex multi-tMap jobs are harder to tune, debug, and migrate. In high-volume jobs (millions of rows), even small per-row overhead compounds into significant runtime increases. This is an active job-level performance finding with a 2-point deduction.

**classification:** Warning — Moderate performance impact; excessive tMap chain.
**remediation:** Analyze tMap dependencies: identify duplicated lookups and filters that could be pushed to SQL. Consolidate consecutive tMap components. Push filtering and aggregation to source database queries. See Performance Remediation → Fixing Heavy tMap Usage (RULE-PERF-002) for detailed steps.

**source:** Talend Health Analyzer performance rule engine

---

## RULE-PERF-003: Small Commit Interval

**rule_id:** RULE-PERF-003
**category:** performance
**title:** Small commit interval
**description:** A target output component has a commit or batch interval of 100 or less. This is determined by checking the COMMIT_EVERY, COMMIT_SIZE, or BATCH_SIZE parameter on output-capable components (tDBOutput, tMysqlOutput, tOracleOutput, tFileOutputDelimited, etc.).

**detection_logic:** For each output component, read the COMMIT_EVERY, COMMIT_SIZE, or BATCH_SIZE parameter value. If the value is 100 or less and the component is active, flag the component. Only output-oriented components are checked; input-only components are excluded.

**impact:** Very small commit intervals create excessive transaction overhead, especially on databases that enforce ACID compliance. Each commit triggers a disk flush, log write, and lock release cycle. For bulk load operations processing millions of rows, commit-every-100 can result in tens of thousands of separate transactions, slowing throughput by 10x or more compared to optimized batch sizes. This is an active component-level performance finding with a 2-point deduction.

**classification:** Warning — Moderate performance impact.
**remediation:** Identify target components and classify the workload (bulk, batch, streaming). Benchmark commit sizes against production-scale data volumes. Apply optimal settings per database type. See Performance Remediation → Fixing Small Commit Intervals (RULE-PERF-003) for detailed steps.

**source:** Talend Health Analyzer performance rule engine

---

## RULE-PERF-004: Missing Source Pushdown

**rule_id:** RULE-PERF-004
**category:** performance
**title:** Missing source pushdown
**description:** A job reads a database table without applying any filter, then uses Talend components (tMap, tFilterRow) to filter or aggregate rows downstream. This pattern moves data processing from the database (where it is most efficient) to the Talend runtime (where it consumes license compute and network bandwidth).

**detection_logic:** Identify jobs where a tDBInput (or equivalent) reads from a table or uses SELECT * FROM table without a WHERE clause, followed within 3 component hops by a tMap with filter expressions, tFilterRow, or tAggregateRow. Both the database input and downstream filter must be active. If the source database and filter operation are compatible with SQL pushdown, flag the job.

**impact:** Pulling all rows from a database only to filter or aggregate in Talend wastes network bandwidth, database I/O, and Talend runtime resources. For large tables (millions of rows), this pattern can increase job runtime by 5-10x and consume unnecessary database CPU for full table scans. This is an active job-level performance finding with a 2-point deduction.

**classification:** Warning — Moderate performance impact.
**remediation:** Identify pushdown opportunities by tracing data flow from source input to first transformation. Replace table-level tDBInput with custom SQL incorporating WHERE filters, column selection, and joins. See Performance Remediation → Fixing Missing Source Pushdown (RULE-PERF-004) for detailed steps.

**source:** Talend Health Analyzer performance rule engine

---

## RULE-PERF-005: Inefficient Lookup Configuration

**rule_id:** RULE-PERF-005
**category:** performance
**title:** Inefficient lookup configuration
**description:** A tMap component loads a lookup table using the Load once model but the lookup is referenced by only a small fraction of incoming rows, or the lookup table is loaded multiple times across different tMap components within the same job.

**detection_logic:** Scan tMap components for: lookup tables using Load once model where the join key matches fewer than 10% of incoming rows; identical lookup tables loaded in multiple tMap components; lookups without a key matching model configured (defaults to full scan per row); tAdvancedHash used where the lookup table contains fewer than 1000 rows.

**impact:** Loading a large lookup table for every row when only a few rows match wastes memory and initialization time. Loading the same lookup table N times across N tMap components multiplies memory consumption by N. Incorrect match models can degrade tMap performance from O(1) to O(n) per row. This is an active component-level performance finding with a 2-point deduction.

**classification:** Warning — Moderate performance impact.
**remediation:** Audit lookup patterns: document each lookup table and match model. Eliminate duplicated lookups by extracting to tAdvancedHash. Optimize match models based on selectivity. Use disk spilling for large lookups exceeding 100K rows. See Performance Remediation → Fixing Inefficient Lookup Configuration (RULE-PERF-005) for detailed steps.

**source:** Talend Health Analyzer performance rule engine

---

## RULE-PERF-006: Missing Parallelization in Loops

**rule_id:** RULE-PERF-006
**category:** performance
**title:** Missing parallelization in loops
**description:** A job uses tLoop, tForEach, or tFileList to iterate over independent items (files, database partitions, API pages) but does not enable parallel processing. Each iteration executes sequentially when the work could run concurrently.

**detection_logic:** Identify jobs containing tLoop, tForEach, or tFileList where the loop body contains no tParallelize component, loop iterations are independent (no shared mutable state), and the number of iterations is 3 or more (parallelization has meaningful benefit).

**impact:** Sequential processing of independent iterations multiplies job runtime by the number of iterations. For example, processing 10 files sequentially at 5 minutes each takes 50 minutes, while parallel execution could complete in 5-10 minutes depending on available resources. This is an active job-level performance finding with a 1-point deduction.

**classification:** Advisory — Minor performance impact.
**remediation:** Identify loops with independent iterations. Add tParallelize after the looping component. Set Max parallel jobs based on available CPU cores and database connection pool limits. Handle shared resources carefully. See Performance Remediation → Fixing Missing Parallelization (RULE-PERF-006) for detailed steps.

**source:** Talend Health Analyzer performance rule engine

---

## RULE-PERF-007: Excessive Memory Allocation

**rule_id:** RULE-PERF-007
**category:** performance
**title:** Excessive memory allocation
**description:** A job is configured with a JVM heap size (Xmx) that exceeds recommended limits for the expected data volume, or the job uses tAdvancedHash for small datasets where simpler lookups would suffice, or multiple large lookups are loaded simultaneously without disk-spilling alternatives.

**detection_logic:** Evaluate job characteristics: tAdvancedHash components with lookup tables under 1000 rows (overkill); multiple large lookups (each over 100K rows) loaded simultaneously without tHashOutput/tHashInput disk spilling; sort operations (tSortRow) without an explicit tmp directory; tFileInputXML or tFileInputJSON using DOM-based parsing instead of streaming for large files.

**impact:** Over-allocated memory wastes JVM resources and can cause excessive GC pauses. Under-allocated memory causes OutOfMemoryErrors. In-memory sort without disk spill for large datasets crashes the job. DOM-based XML/JSON parsing loads the entire document into memory, causing OOM for multi-GB files. This is an active job-level performance finding with a 1-point deduction.

**classification:** Advisory — Minor performance impact.
**remediation:** Right-size JVM heap based on data volume. Replace tAdvancedHash with tHashOutput/Input for lookups over 100K rows. Configure temp directories for tSortRow. Use streaming parsers for XML/JSON files over 100 MB. See Performance Remediation → Fixing Excessive Memory Allocation (RULE-PERF-007) for detailed steps.

**source:** Talend Health Analyzer performance rule engine

---

## RULE-PERF-008: Excessive Component Redundancy

**rule_id:** RULE-PERF-008
**category:** performance
**title:** Excessive component redundancy
**description:** A job contains redundant or unnecessary components that add processing overhead without business value. This includes consecutive tMap components that could be merged, tFilterRow followed by tMap with no additional filtering, debug tLogRow components left in production jobs, and disabled components that are compiled but never executed.

**detection_logic:** Scan job designs for: consecutive tMap components where the first outputs flow directly into the second without any transformation between them; tFilterRow immediately followed by tMap; tLogRow components with a row count of 0 or with debug-level settings in production jobs; tConvertType components where source and target types are identical; disabled components left in the job design.

**impact:** Redundant components increase job compilation time, memory footprint, and per-row processing latency. Debug components in production jobs waste I/O and storage and can inadvertently expose sensitive data. Each unnecessary component adds to job complexity, making maintenance and migration harder. This is an active job-level performance finding with a 1-point deduction.

**classification:** Advisory — Minor performance impact.
**remediation:** Identify redundant components: consecutive tMaps, tFilterRow followed by tMap, debug tLogRow, redundant tConvertType. Merge and simplify. Remove disabled components. Implement design standards to prevent regressions. See Performance Remediation → Fixing Excessive Component Redundancy (RULE-PERF-008) for detailed steps.

**source:** Talend Health Analyzer performance rule engine

---

## RULE-PERF-009: Monolithic SubJob Structure

**rule_id:** RULE-PERF-009
**category:** performance
**title:** Monolithic subjob structure
**description:** A single job combines extract, transform, and load operations without using subjob decomposition via tRunJob. Monolithic jobs cannot scale horizontally, cannot be partially retried on failure, and make parallel execution impossible.

**detection_logic:** Evaluate jobs that contain more than 3 distinct processing stages, have a component count exceeding 30 AND perform multiple unrelated processing stages, do not use tRunJob to delegate any processing to subjobs, or contain tMap components operating on data from completely unrelated source systems within the same job flow.

**impact:** Monolithic jobs cannot be partially restarted on failure — the entire job must rerun. They cannot be parallelized across processing stages. A failure in the final load stage means the entire extraction and transformation must repeat. Testing and debugging are more difficult because the entire job must execute to validate any single stage. This is an active job-level performance finding with a 1-point deduction.

**classification:** Advisory — Minor performance impact.
**remediation:** Analyze job structure to identify distinct processing stages. Decompose into focused subjobs: extract, transform, load. Use tRunJob in a parent orchestrator. Implement error handling and parallel execution at the orchestrator level. See Performance Remediation → Fixing Monolithic SubJob Structure (RULE-PERF-009) for detailed steps.

**source:** Talend Health Analyzer performance rule engine

---

## Severity Classification Guide

| Severity | Criteria | Examples |
|----------|----------|---------|
| **Risk** | Significant performance impact — can cause order-of-magnitude slowdowns | Memory bottleneck, large unoptimized lookups, no pushdown |
| **Warning** | Moderate performance impact — reduces throughput or increases resource usage | Excessive tMap chain, large subjob chain, small commit intervals |
| **Advisory** | Minor performance impact — marginal improvement from remediation | Unused components, redundant components, missing parallelization, excessive memory |

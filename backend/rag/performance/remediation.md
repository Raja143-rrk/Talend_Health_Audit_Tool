# Performance Remediation

---

## RM-PERF-001: Fixing Excessive Custom Java

**rule_id:** RM-PERF-001
**category:** performance
**title:** Fixing excessive custom Java components
**description:** Step-by-step guidance for resolving RULE-PERF-001 by replacing or consolidating custom Java components with native Talend alternatives.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-PERF-001 for detection logic.

**impact:** Resolving RULE-PERF-001 reduces job compilation time, improves runtime performance, and enables Talend's optimizer to apply automatic parallelization and memory management.

**classification:** Remediation — HIGH severity
**remediation:**
1. Review each tJava, tJavaRow, and tJavaFlex component in the flagged job. Classify each component's purpose: data transformation, control flow, external API call, logging, or other. Note which components contain logic that can be replaced by native Talend components.
2. Replace standard transformations with tMap expression functions: StringHandling.UPCASE(), StringHandling.LEFT(), Math.round(), etc. Replace arithmetic operations with tMap math functions. Replace type conversions with tMap type casting or tConvertType. Replace conditional logic with tMap's Filter function on output ports.
3. For repeated code patterns, create a Talend routine (Code → Routines in Repository). Move common functions (date formatting, ID generation, data validation) into routines with documented parameters and return types.
4. For logic that cannot be replaced by native components: extract into a single routine rather than multiple tJava components. Minimize row-level processing — batch operations where possible. Move initialization code to tPrejob to avoid repeated setup. Consider splitting the job so custom logic is isolated in a dedicated subjob.

**source:** Talend Health Analyzer remediation documentation

---

## RM-PERF-002: Fixing Heavy tMap Usage

**rule_id:** RM-PERF-002
**category:** performance
**title:** Fixing heavy tMap usage
**description:** Step-by-step guidance for resolving RULE-PERF-002 by consolidating excessive tMap components.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-PERF-002 for detection logic.

**impact:** Resolving RULE-PERF-002 reduces per-row processing latency, eliminates redundant lookup memory consumption, and simplifies job debugging and migration.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. List all tMap components and their purposes: source-to-target mapping, lookup enrichment, aggregation, filtering. Identify lookups loaded identically across multiple tMap components. Note filters and expressions that could be pushed to source SQL.
2. Merge consecutive tMap components: if tMap_1 outputs to tMap_2, combine their expressions into one. Consolidate lookups: load a shared lookup once using tAdvancedHash, reference it from multiple tMaps. For tMap components with different source tables from the same database, push the join to SQL.
3. Replace tDBInput (no filter) → tMap (with filter) with a single `SELECT * FROM table WHERE condition`. Replace tDBInput (all columns) → tMap (select columns) with column-specific SELECT. Replace tDBInput → tMap (aggregation) with SQL GROUP BY.
4. Remove unused input and output columns from each tMap. Set appropriate lookup match models: All rows for inner joins, First row for existence checks. Enable Temporary data for large lookups that should spill to disk. Review expression complexity: split very complex expressions into multiple simpler tMap passes.

**source:** Talend Health Analyzer remediation documentation

---

## RM-PERF-003: Fixing Small Commit Intervals

**rule_id:** RM-PERF-003
**category:** performance
**title:** Fixing small commit intervals
**description:** Step-by-step guidance for resolving RULE-PERF-003 by optimizing commit and batch sizes.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-PERF-003 for detection logic.

**impact:** Resolving RULE-PERF-003 reduces transaction overhead and improves database write throughput by orders of magnitude for bulk operations.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. List all output components flagged for small commit intervals. Note the target database type and the current commit setting. Classify the workload: bulk load, real-time streaming, or batch processing.
2. For each target database type, test commit sizes against production-scale data volumes: OLTP databases (Oracle, SQL Server, PostgreSQL) test 100, 500, 1000, 5000, 10000; cloud warehouses (Snowflake, Redshift) test 1000, 5000, 10000, 50000; file outputs test 10000, 50000, 100000. Record throughput (rows/second) and resource usage for each setting.
3. Set COMMIT_EVERY or BATCH_SIZE to the optimal value. For bulk load scenarios, use larger commit sizes (5000-10000). For near-real-time flows, balance commit size against latency SLAs. Consider using tBatchRow for very high-volume database loads.
4. Ensure jobs are designed for idempotent execution in case of failure mid-batch. For very large commits, implement checkpoint logic to track processed rows. Document the rollback strategy: full batch rollback, partial rollback, or transactional resume.

**source:** Talend Health Analyzer remediation documentation

---

## RM-PERF-004: Fixing Missing Source Pushdown

**rule_id:** RM-PERF-004
**category:** performance
**title:** Fixing missing source pushdown
**description:** Step-by-step guidance for resolving RULE-PERF-004 by pushing filters, aggregations, and joins to the source database.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-PERF-004 for detection logic.

**impact:** Resolving RULE-PERF-004 reduces data transfer between database and Talend runtime, cutting network bandwidth and processing time by up to 10x for large tables.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. For each flagged job, trace data flow from source database input to first transformation. Identify WHERE filters in tMap, tFilterRow, or tJavaRow that can be expressed in SQL. Identify columns selected by the source input but not used downstream.
2. Replace table-level tDBInput with custom SQL: build a SELECT statement that includes filters, column selection, and joins. Example: Replace `tDBInput(Table: orders) → tMap(filter: status='COMPLETED')` with `tDBInput(SQL: SELECT * FROM orders WHERE status = 'COMPLETED')`. Push aggregations and joins.
3. Use database-specific features: for Oracle use WHERE ROWNUM and FETCH FIRST; for Snowflake/Redshift use clustered tables and materialized views; for SQL Server use indexed views; for PostgreSQL use EXPLAIN ANALYZE to verify query plan.
4. Compare job runtime before and after pushdown to quantify improvement. Verify that pushed queries return equivalent results. Document the SQL pushdown decision for future maintenance.

**source:** Talend Health Analyzer remediation documentation

---

## RM-PERF-005: Fixing Inefficient Lookup Configuration

**rule_id:** RM-PERF-005
**category:** performance
**title:** Fixing inefficient lookup configuration
**description:** Step-by-step guidance for resolving RULE-PERF-005 by optimizing lookup configurations in tMap components.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-PERF-005 for detection logic.

**impact:** Resolving RULE-PERF-005 reduces memory consumption for lookup data structures, eliminates redundant data loading, and improves per-row tMap performance.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. For each tMap, document every lookup table and its match model. Identify duplicated lookups: the same table or file loaded in multiple tMap components. Measure lookup selectivity: what percentage of incoming rows actually match a lookup key?
2. Extract the shared lookup into a tAdvancedHash component connected before the first tMap. Reference the tAdvancedHash output from all downstream tMap components. This loads the lookup once into memory, shared across all consumers.
3. For low-selectivity lookups (few incoming rows match), use Load once with a smaller cache. For high-selectivity lookups (most rows match), use Load once with full cache. For sorted inputs, use the Sorted model to avoid loading the entire lookup into memory. For small reference tables (under 1000 rows), use Load once — the memory cost is negligible.
4. For lookups exceeding 100K rows, use tHashOutput to write the lookup to disk and tHashInput to read it. Replace tAdvancedHash with tHashOutput/Input for very large reference data. Monitor temporary disk space for hash files.

**source:** Talend Health Analyzer remediation documentation

---

## RM-PERF-006: Fixing Missing Parallelization

**rule_id:** RM-PERF-006
**category:** performance
**title:** Fixing missing parallelization in loops
**description:** Step-by-step guidance for resolving RULE-PERF-006 by adding parallel execution to independent loop iterations.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-PERF-006 for detection logic.

**impact:** Resolving RULE-PERF-006 reduces sequential iteration runtime by a factor equal to the number of parallel branches, transforming linear scaling into near-constant execution time.

**classification:** Remediation — LOW severity
**remediation:**
1. Review jobs with tLoop, tForEach, or tFileList for independent iterations. Check if loop iterations modify shared resources (same database table, same file). Verify that parallel execution would not exceed database connection pool limits.
2. Add tParallelize after the looping component (tLoop, tForEach, tFileList). Connect the loop body to the Parallel port of tParallelize. Set the Max parallel jobs parameter: start with the number of CPU cores available, reduce for I/O-bound workloads, increase for CPU-bound processing.
3. Ensure each parallel branch uses its own database connection (use connection pooling). Write parallel branch outputs to separate files or database partitions to avoid conflicts. After parallel processing, use a tWaitFor component to synchronize before continuing.
4. Measure runtime before and after parallelization. Monitor CPU, memory, and database connection usage during parallel execution. Adjust parallel degree to find the optimal throughput without resource contention.

**source:** Talend Health Analyzer remediation documentation

---

## RM-PERF-007: Fixing Excessive Memory Allocation

**rule_id:** RM-PERF-007
**category:** performance
**title:** Fixing excessive memory allocation
**description:** Step-by-step guidance for resolving RULE-PERF-007 by optimizing memory configuration and usage patterns.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-PERF-007 for detection logic.

**impact:** Resolving RULE-PERF-007 prevents OutOfMemoryErrors, reduces GC pause times, and ensures predictable job execution for large data volumes.

**classification:** Remediation — LOW severity
**remediation:**
1. Monitor job memory usage using JVM monitoring tools (JConsole, VisualVM, GC logs). Set -Xms and -Xmx to the same value to avoid heap resizing overhead. For moderate jobs: start with -Xms2g -Xmx2g. For large data volumes: use -Xms8g -Xmx8g and monitor GC behavior. Do not exceed available physical memory.
2. Replace tAdvancedHash with tHashOutput/Input for lookups over 100K rows. For small lookups (under 1000 rows), use tMap's built-in lookup without tAdvancedHash. Set the Temporary data option on tMap lookups that exceed expected row counts.
3. For tSortRow, configure a Temp directory path on a volume with sufficient disk space. Use external sorting (disk-based) for datasets exceeding 500K rows. If the source database can sort output, use ORDER BY in the source query instead.
4. For large XML files, use tFileInputXML with XPath expressions (streaming mode). For large JSON files, use tFileInputJSON with Read by set to element path (streaming). Avoid tFileInputXML and tFileInputJSON in default DOM mode for files over 100 MB.

**source:** Talend Health Analyzer remediation documentation

---

## RM-PERF-008: Fixing Excessive Component Redundancy

**rule_id:** RM-PERF-008
**category:** performance
**title:** Fixing excessive component redundancy
**description:** Step-by-step guidance for resolving RULE-PERF-008 by removing redundant components from job designs.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-PERF-008 for detection logic.

**impact:** Resolving RULE-PERF-008 reduces compilation time, memory footprint, per-row latency, and job complexity.

**classification:** Remediation — LOW severity
**remediation:**
1. Review the flagged job for consecutive tMap components that can be merged. Check for tFilterRow immediately followed by tMap — move the filter into the tMap expression. Locate tLogRow components not actively monitored (remove from production). Identify tConvertType where input and output types match.
2. Combine consecutive tMaps: copy expressions from the second into the first and remove the second. Move tFilterRow conditions into the upstream tMap's output filter expression. Remove tLogRow components that serve debugging purposes only. Remove tConvertType doing redundant conversions.
3. Identify disabled components. For each: if obsolete, delete it; if intentionally retained, document the reason. Run the analyzer again after cleanup.
4. Create a job design checklist: no redundant components, no debug components in production, no disabled dead code. Add a CI/CD pipeline step that flags jobs with unnecessary components.

**source:** Talend Health Analyzer remediation documentation

---

## RM-PERF-009: Fixing Monolithic SubJob Structure

**rule_id:** RM-PERF-009
**category:** performance
**title:** Fixing monolithic subjob structure
**description:** Step-by-step guidance for resolving RULE-PERF-009 by decomposing monolithic jobs into focused parent-child subjob structures.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-PERF-009 for detection logic.

**impact:** Resolving RULE-PERF-009 enables partial job restart on failure, horizontal scaling via parallel subjobs, and independent testing of each processing stage.

**classification:** Remediation — LOW severity
**remediation:**
1. Map the flagged job's processing stages: identify distinct extract, transform, load, and reporting phases. Identify data flows that could be split at natural boundaries. Note which stages could run in parallel versus sequentially.
2. Create a new subjob for each distinct stage: Job_Extract reads from sources, writes to staging; Job_Transform reads from staging, applies business logic; Job_Load reads from transformed staging, writes to targets. Use tRunJob in the parent orchestrator. Use Transmit entire flow for large datasets, Transmit context for parameters.
3. In the parent orchestrator, define error handling per subjob: on failure, stop all, skip to next, or retry. Use tRunJob's On component error trigger to capture subjob failures. Log subjob start, end, and status at the orchestrator level.
4. For independent subjobs, use tParallelize at the orchestrator level with appropriate resource limits. Use tWaitFor to synchronize parallel branches before the next sequential stage.
5. Test each subjob independently. Test the full orchestrator. Implement retry logic: a failed subjob should restart only that stage, not the entire pipeline.

**source:** Talend Health Analyzer remediation documentation

# Performance Best Practices

---

## BP-PERF-001: tMap Optimization

**rule_id:** BP-PERF-001
**category:** performance
**title:** tMap Optimization
**description:**
Push filters, joins, and aggregations to source databases whenever possible. Split complex tMap expressions into multiple lookup-based mappings. Reuse lookup datasets across multiple tMap components instead of reloading. Avoid row-by-row calculations in tMap expressions; use database-level aggregation. Use tMap's built-in lookup models (load once, reload if needed) appropriately. Configure tMap buffer size based on expected row volume — larger buffers reduce GC pressure. Disable unused tMap columns (both input and output) to reduce memory footprint. Use tMap's Match Model settings to choose the correct model for each lookup. For large lookups, use tHashOutput/tHashInput with tMap instead of in-memory lookups.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Performance Findings RULE-PERF-002 and RULE-PERF-005.

**impact:**
Optimized tMap configurations reduce per-row processing latency, minimize memory consumption for lookup data structures, and prevent unnecessary data movement between the database and Talend runtime.

**classification:** Best Practice
**remediation:**
Review each tMap component for unnecessary columns, incorrect match models, and expressions that could be pushed to SQL. Merge consecutive tMaps. Consolidate duplicated lookups into shared tAdvancedHash references.

**source:** Talend performance best practices

---

## BP-PERF-002: Pushdown Processing

**rule_id:** BP-PERF-002
**category:** performance
**title:** Pushdown Processing
**description:**
Push filters (WHERE clauses) to the source database to reduce rows entering the Talend runtime. Push aggregations (GROUP BY, SUM, COUNT, AVG) to the source to reduce data volume. Push joins between source tables to the database; use SQL queries instead of tMap joins when both tables come from the same database. Use tDBInput with custom SQL rather than table-level tDBInput plus tMap filter for filtered data. For cloud data warehouses (Snowflake, Redshift, BigQuery), maximize SQL pushdown — these engines are optimized for large-scale data processing. Push sorting (ORDER BY) to the source database when the job requires ordered data. Use database-specific bulk unload features for large exports. Consider ELT (Extract-Load-Transform) over ETL for data warehouse targets.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Performance Finding RULE-PERF-004.

**impact:**
Pushdown processing reduces the data volume entering the Talend runtime, minimizing network bandwidth consumption, database I/O, and Talend processing time. For large tables, pushdown can improve job runtime by 5-10x.

**classification:** Best Practice
**remediation:**
Identify tDBInput components that read without filters followed by tMap or tFilterRow. Replace with custom SQL incorporating WHERE, JOIN, GROUP BY, and ORDER BY clauses directly in the source query.

**source:** Talend performance best practices, database optimization guides

---

## BP-PERF-003: Lookup Optimization

**rule_id:** BP-PERF-003
**category:** performance
**title:** Lookup Optimization
**description:**
Use tAdvancedHash for large lookup datasets that are reused across multiple tMap components. Prefer database lookups (via tDBInput) over file-based lookups (tFileInput) for dynamic reference data. For sorted input data, use the Sorted lookup model in tMap to avoid full in-memory loading. For small static reference tables, load once at job startup using tPrejob plus tHashOutput. Avoid lookups inside tJavaRow — they execute row-by-row and bypass Talend's optimization. Use tMap's Lookup mode with Load once when the lookup table does not change per row. Split large lookup tables into partitioned lookups if the data can be sharded by a key. Monitor lookup cardinality.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Performance Finding RULE-PERF-005.

**impact:**
Inefficient lookup configurations waste memory, increase initialization time, and degrade per-row processing speed. Correctly configured lookups reduce memory consumption by sharing data across components and using appropriate match models.

**classification:** Best Practice
**remediation:**
Audit all lookup configurations for duplicate loading, incorrect match models, and unnecessary tAdvancedHash usage. Consolidate shared lookups. Use disk-spilling (tHashOutput/Input) for lookups exceeding 100K rows.

**source:** Talend performance best practices

---

## BP-PERF-004: Parallel Processing

**rule_id:** BP-PERF-004
**category:** performance
**title:** Parallel Processing
**description:**
Use tParallelize to execute independent job branches concurrently. Enable Parallelize in tLoop and tForEach components when iterations are independent. For file-based processing, use tFileList with parallel execution to process multiple files simultaneously. Partition large datasets by a distribution key and process each partition in a separate parallel branch. Set appropriate Max parallel jobs limits based on available CPU cores and database connection pool size. Avoid parallel execution when branches share mutable resources. Monitor thread contention — too many parallel threads can degrade performance due to context switching. Use tPartition to split data into chunks for parallel downstream processing.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Performance Finding RULE-PERF-006.

**impact:**
Parallel processing can reduce job runtime by a factor equal to the number of parallel branches (up to available CPU cores). Sequential processing of independent iterations multiplies runtime by the number of iterations.

**classification:** Best Practice
**remediation:**
Identify loops and sequential branches that process independent data. Add tParallelize components. Set thread counts based on available resources. Ensure shared resources (database connections, file handles) are not contention points.

**source:** Talend performance best practices

---

## BP-PERF-005: Memory Usage

**rule_id:** BP-PERF-005
**category:** performance
**title:** Memory Usage
**description:**
Configure JVM heap size (-Xms, -Xmx) based on expected data volume. Start with 2-4 GB for moderate jobs, 8-16 GB for large data volumes. Set tMap buffer size per component: larger for high-row-count flows, smaller for low-volume lookups. Use tHashOutput/tHashInput for spilling large intermediate datasets to disk instead of holding them in memory. Avoid collecting all rows in tJavaRow or tJavaFlex — these run in-memory and can cause OOM errors. For tSortRow, configure a tmp directory with sufficient disk space for external sorting. Enable GC logging (-verbose:gc) during development. Monitor top/Task Manager during job runs to identify memory leaks. For very large XML/JSON processing, use streaming parsers instead of DOM-based loading.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Performance Finding RULE-PERF-007.

**impact:**
Proper memory configuration prevents OutOfMemoryErrors, reduces GC pause times, and ensures predictable job execution. Over-allocated memory wastes JVM resources; under-allocated memory causes job failures.

**classification:** Best Practice
**remediation:**
Monitor memory usage with JVM tools. Set -Xms and -Xmx to the same value. Use disk-spilling for large datasets. Configure streaming for XML/JSON. Set appropriate tMap buffer sizes.

**source:** Talend performance best practices, JVM tuning guides

---

## BP-PERF-006: Large Data Volumes

**rule_id:** BP-PERF-006
**category:** performance
**title:** Large Data Volumes
**description:**
Process data in chunks or batches rather than loading all rows into memory at once. Use database cursors (set fetch size in tDBInput) to stream rows instead of fetching all at once. For file-based sources, split large files into smaller chunks and process in parallel. Use tFileInputDelimited with Header and Footer options to skip non-data lines. Enable Trim empty rows and Skip empty rows in file input components to reduce processing overhead. For database targets, use bulk load components: tDBOutput with batch size enabled, tRedshiftBulk, tSnowflakeOutputBulk. For cloud storage, use native bulk operations. Implement checkpointing so large jobs can resume from failure. Monitor disk space for temporary files. Consider splitting a single large job into a sequence of smaller jobs.

**detection_logic:** Not applicable — this is a best practice guidance document.

**impact:**
Processing large data volumes without proper batching and streaming leads to OutOfMemoryErrors, excessive GC overhead, and job failures. Bulk operations can improve throughput by 10-100x compared to row-by-row processing.

**classification:** Best Practice
**remediation:**
Configure fetch sizes for streaming reads. Use bulk load components for database targets. Implement checkpointing for restartability. Split monolithic jobs into sequenced subjobs with intermediate staging.

**source:** Talend performance best practices

---

## BP-PERF-007: Component Reduction

**rule_id:** BP-PERF-007
**category:** performance
**title:** Component Reduction
**description:**
Remove redundant components: two consecutive tMap components can often be merged into one. Replace tFilterRow plus tMap with a single tMap that includes the filter condition. Eliminate unnecessary type conversion components (tConvertType) by setting correct types in source components. Replace tDenormalize plus tMap with a single SQL query on the source database. Remove tLogRow components used for debugging in production jobs. Consolidate multiple tFileOutputDelimited components into a single component with conditional routing. Replace sequences of tMap-to-tSortRow-to-tMap with a single tMap using sorted input. Use conditional output ports in tMap (Filter function) instead of separate tFilterRow components. Remove disabled components.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Performance Finding RULE-PERF-008.

**impact:**
Redundant components increase compilation time, memory footprint, and per-row processing latency. Each unnecessary component adds to job complexity, making maintenance and migration harder.

**classification:** Best Practice
**remediation:**
Review jobs for consecutive tMaps, tFilterRow followed by tMap, and debug tLogRow components. Merge, consolidate, and remove redundant components. Use tMap Filter function instead of separate filter components.

**source:** Talend performance best practices

---

## BP-PERF-008: SubJob Optimization

**rule_id:** BP-PERF-008
**category:** performance
**title:** SubJob Optimization
**description:**
Split monolithic jobs into focused subjobs connected by tRunJob. Each subjob should have a single responsibility: extract, transform, or load — not all three. Use tRunJob with Transmit entire flow for passing large datasets between subjobs. Use tRunJob with Transmit context for small parameter passing. Design subjobs to be independently testable and reusable across parent orchestrators. Set appropriate timeout values in tRunJob to detect hung subjobs. Implement error handling at the orchestrator level. Use global variables (tGlobal) sparingly. For time-critical processing, use tParallelize at the orchestrator level to run independent subjobs concurrently. Document subjob interfaces.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Performance Finding RULE-PERF-009.

**impact:**
Monolithic jobs cannot be partially restarted on failure, cannot scale horizontally, and are harder to test and debug. Split into focused subjobs enables partial retry, parallel execution, and independent testing.

**classification:** Best Practice
**remediation:**
Analyze monolithic jobs to identify distinct processing stages. Extract each stage into a focused subjob. Create a parent orchestrator using tRunJob. Implement error handling and retry at the orchestrator level.

**source:** Talend performance best practices

---

## BP-PERF-009: Commit and Batch Size Tuning

**rule_id:** BP-PERF-009
**category:** performance
**title:** Commit and Batch Size Tuning
**description:**
Tune commit and batch sizes based on target database throughput, rollback requirements, and recovery objectives. Large commits improve throughput but increase data loss risk on failure. Small commits reduce data loss but create transaction overhead. Test different commit sizes against production-scale data volumes. For cloud warehouses (Snowflake, Redshift), use micro-batches of 5000-10000 rows. For OLTP databases (Oracle, SQL Server), use smaller commits (500-1000) to avoid blocking concurrent transactions.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Performance Finding RULE-PERF-003.

**impact:**
Very small commit intervals create excessive transaction overhead, slowing throughput by 10x or more. Very large commits increase data loss risk on failure. Optimal commit sizes balance throughput with recovery objectives.

**classification:** Best Practice
**remediation:**
Benchmark commit sizes against production-scale data volumes. Apply optimal settings based on database type: larger commits for bulk loads, smaller commits for OLTP. Test and document the rollback strategy.

**source:** Talend performance best practices

---

## BP-PERF-010: Component Efficiency

**rule_id:** BP-PERF-010
**category:** performance
**title:** Component Efficiency
**description:**
Avoid excessive custom Java components (tJava, tJavaRow, tJavaFlex) in a single job. Replace repeated custom Java logic with reusable Talend routines. Use native Talend components for standard transformations instead of custom code. Minimize row-level processing — use set-based operations where possible. Configure appropriate buffer sizes for tMap and tSortRow components. Use tFlowToIterate and tIterateToFlow for row-to-iteration conversion instead of tJavaRow loops.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Performance Finding RULE-PERF-001.

**impact:**
Custom Java components bypass Talend's optimized code generation, preventing compile-time optimizations. Each tJava component creates a separate class instance, increasing compilation overhead and memory footprint.

**classification:** Best Practice
**remediation:**
Replace tJava/tJavaRow logic with native Talend components wherever possible. Extract remaining custom logic into reusable routines. Limit each job to a maximum of 2 custom Java components.

**source:** Talend performance best practices

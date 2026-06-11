# Architecture Best Practices

---

## BP-ARCH-001: Parent/Child Jobs

**rule_id:** BP-ARCH-001
**category:** architecture
**title:** Parent/Child Jobs
**description:**
Design parent jobs as lightweight orchestrators that coordinate subjob execution without performing data transformation. Use tRunJob to call child jobs with explicit data flow or context-based parameter passing. Implement parent-level error handling: on child job failure, decide whether to stop all, retry, or skip to the next. Use row-based passing (Transmit entire flow) for small datasets, file-based handoff for large datasets, table-based handoff for resilience, and context-based passing for scalar values. Each child job must be independently runnable with correct context variables. Design child jobs idempotently. Limit parent/child nesting to 3 levels maximum.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Architecture Finding RULE-ARCH-007.

**impact:**
Parent/child decomposition enables partial job restart on failure, horizontal scaling through parallel subjob execution, and independent testing of each processing stage.

**classification:** Best Practice
**remediation:**
Identify monolithic jobs and decompose them into parent orchestrator plus focused child jobs. Implement proper data passing, error handling, and retry logic at the orchestrator level.

**source:** Talend architecture best practices

---

## BP-ARCH-002: Joblets

**rule_id:** BP-ARCH-002
**category:** architecture
**title:** Joblets
**description:**
Joblets encapsulate a reusable fragment of a job design that can be shared across multiple jobs. Unlike tRunJob, joblets are linked components that appear as a single component in the parent job. Use joblets for: connection management, error logging, file archiving, data validation, and notification. Keep joblets focused on a single responsibility. Expose only the minimum number of input/output ports. Use context variables within joblets for all configurable parameters. Version joblets in the same repository as jobs. Prefer joblets for small reusable logic fragments (5-15 components) and tRunJob for full jobs with independent lifecycles.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Architecture Finding RULE-ARCH-008.

**impact:**
Joblets eliminate duplication of small reusable logic fragments without the overhead of full subjob invocation. They enforce consistent behavior for common patterns across all jobs.

**classification:** Best Practice
**remediation:**
Identify repeatable patterns (connection setup, error logging, file archiving). Create joblets for each pattern. Replace duplicated component sequences with joblet references.

**source:** Talend architecture best practices

---

## BP-ARCH-003: Modular Design

**rule_id:** BP-ARCH-003
**category:** architecture
**title:** Modular Design
**description:**
Split data pipelines into three distinct layers: extraction (reads from sources, writes to staging), transformation (reads from staging, applies business logic), and loading (reads from transformed staging, writes to targets). Each layer should be replaceable without affecting the others. A module (subjob) should have no more than 30 components and a single clearly defined responsibility. Define clear interfaces between modules: expected input schema, expected output schema, required context variables. Use staging tables or files at module boundaries so the output of one module is persisted before the next starts.

**detection_logic:** Not applicable — this is a best practice guidance document.

**impact:**
Modular design enables partial restart, parallel execution, independent testing, and replacement of individual modules without affecting the rest of the pipeline.

**classification:** Best Practice
**remediation:**
Analyze existing pipelines for separation of extract/transform/load stages. Create staging layers at module boundaries. Define module contracts. Design each module for independent testability.

**source:** Talend architecture best practices

---

## BP-ARCH-004: Error Handling Architecture

**rule_id:** BP-ARCH-004
**category:** architecture
**title:** Error Handling Architecture
**description:**
Implement a three-tier error handling strategy. Tier 1 (Component): reject flows on every tMap, tTryCatch around database writes and API calls. Tier 2 (Job): onComponentError and onSubjobError triggers with accumulation logic for non-fatal errors. Tier 3 (Orchestrator): parent job monitors tRunJob exit codes with per-child retry policies and circuit breaker pattern. Standardize error records with fields: ERROR_ID, JOB_NAME, COMPONENT_NAME, ERROR_TIMESTAMP, ERROR_CODE, ERROR_MESSAGE, SEVERITY, SOURCE_DATA, BATCH_ID.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Architecture Finding RULE-ARCH-003.

**impact:**
A three-tier error architecture ensures no failure goes unhandled, transient errors are retried automatically, and fatal errors are escalated immediately with full diagnostic information.

**classification:** Best Practice
**remediation:**
Implement component-level reject flows and tTryCatch. Add job-level onComponentError triggers. Implement orchestrator-level error monitoring and retry. Create a reusable error handler subjob.

**source:** Talend architecture best practices

---

## BP-ARCH-005: Logging

**rule_id:** BP-ARCH-005
**category:** architecture
**title:** Logging
**description:**
Define standard log levels across all jobs: FATAL (unrecoverable), ERROR (recoverable), WARN (handled condition), INFO (milestones), DEBUG (development detail). Every production job must log at INFO level: job start (name, run ID, batch ID, timestamp), job end (status, duration), row counts per source/target, error summary. Choose a logging approach: Talend log4j (built-in, simple jobs), tLogRow to file (debugging), database log table (production, centralized), structured JSON file (cloud deployments), or API-based logging (enterprise platforms). Create a reusable logging subjob called via tRunJob.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Architecture Finding RULE-ARCH-005.

**impact:**
Consistent logging enables centralized monitoring, rapid troubleshooting, and audit compliance. Inconsistent logging means critical failures may go undetected.

**classification:** Best Practice
**remediation:**
Define a standard logging approach for the project. Create a reusable logging subjob. Retrofit existing jobs to use it. Define minimum logging requirements per job.

**source:** Talend architecture best practices

---

## BP-ARCH-006: Monitoring

**rule_id:** BP-ARCH-006
**category:** architecture
**title:** Monitoring
**description:**
Capture key metrics per job: duration, rows read, rows written, rows rejected, error count, CPU usage, memory usage, disk I/O. Implement a tPrejob health check that validates context variables, system reachability, temp directory space, and staging table schemas before execution. Create monitoring dashboards per environment showing job health heatmap, throughput trends, error rate trends, duration trends, and SLA compliance. Implement alerting rules: immediate page for job failures and data quality violations, within 15 minutes for duration anomalies, daily digest for error trends.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Architecture Finding RULE-ARCH-010.

**impact:**
Without monitoring, production issues are discovered by user reports rather than proactive alerts. Performance degradation goes unnoticed until SLAs are breached.

**classification:** Best Practice
**remediation:**
Create a shared metrics table. Implement a reusable metrics subjob for start/end logging. Add tPrejob health checks to production jobs. Configure monitoring dashboards and alerting rules.

**source:** Talend architecture best practices

---

## BP-ARCH-007: Exception Frameworks

**rule_id:** BP-ARCH-007
**category:** architecture
**title:** Exception Frameworks
**description:**
Use tTryCatch as the foundation of runtime exception handling. Classify exceptions into five classes: Transient (connection timeout, deadlock — retry with backoff up to 3 times), Data (constraint violation, type mismatch — log reject, continue), Configuration (missing context variable, invalid path — stop, alert immediately), System (OutOfMemoryError, disk full — stop, escalate), Security (auth failure, permission denied — stop, escalate to security team). Create a global exception handler subjob that all jobs call when an exception occurs, providing consistent logging, alerting, and escalation.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Architecture Finding RULE-ARCH-011.

**impact:**
Without an exception framework, all errors are treated the same — transient timeouts cause unnecessary job failures, and fatal errors may not receive sufficient escalation.

**classification:** Best Practice
**remediation:**
Create a global exception handler subjob. Implement retry logic with exponential backoff for transient failures. Classify exceptions and route to appropriate response. Add try-catch to all tJava/tJavaRow components.

**source:** Talend architecture best practices

---

## BP-ARCH-008: Reusability Patterns

**rule_id:** BP-ARCH-008
**category:** architecture
**title:** Reusability Patterns
**description:**
Build a catalog of reusable components: Error Handler (standard error logging and alerting via tRunJob subjob), Connection Provider (governed database connection with retry via joblet), Schema Validator (validate rows against schema via joblet with tSchemaComplianceCheck), File Archiver (move processed files with naming convention via tRunJob subjob), Notifier (email/Slack alerts with standard template via tRunJob), Context Validator (verify context variables at startup via tPrejob subjob), Batch Tracker (batch start/end records via tRunJob), Data Quality Checker (standard quality rules via joblet). Prioritize building reusable components for patterns used in 5+ jobs, with complex or frequently modified logic.

**detection_logic:** Not applicable — this is a best practice guidance document.

**impact:**
Reusable patterns eliminate duplication, enforce consistent behavior, and reduce maintenance effort. A well-maintained reuse catalog ensures that all jobs follow the same standards.

**classification:** Best Practice
**remediation:**
Identify the same 5+ component sequence appearing in 3+ jobs. Design the reusable unit (joblet or subjob). Build, test, and document it. Migrate consumers one by one. Establish a change management process for shared components.

**source:** Talend architecture best practices

# Architecture Remediation

---

## RM-ARCH-001: Fixing Missing Contexts

**rule_id:** RM-ARCH-001
**category:** architecture
**title:** Fixing missing contexts
**description:** Step-by-step guidance for resolving RULE-ARCH-001 by creating context groups and migrating hardcoded values.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-001 for detection logic.

**impact:** Resolving RULE-ARCH-001 enables environment-agnostic job designs and makes environment promotion predictable and auditable.

**classification:** Remediation — HIGH severity
**remediation:**
1. Create context groups for each environment (DEV, TEST, UAT, PROD) in Talend Studio.
2. Define context variables for all environment-specific values: database connections (host, port, database name, username, password); file paths (input, output, temp, archive); API endpoints (base URLs, credentials, timeouts); runtime parameters (batch sizes, parallelism, retry counts, log levels).
3. Map context variables to component parameters throughout all jobs.
4. Create `.properties` files for each environment with the actual values and store them in version control.
5. Train the team on context variable usage for all new job development.
6. After migration, remove all remaining hardcoded values from job designs.
7. Implement context validation: add a tPrejob step that checks required context variables are defined and non-empty before executing the main job.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-002: Fixing High System Spread

**rule_id:** RM-ARCH-002
**category:** architecture
**title:** Fixing high system spread
**description:** Step-by-step guidance for resolving RULE-ARCH-002 by consolidating and governing system integrations.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-002 for detection logic.

**impact:** Resolving RULE-ARCH-002 reduces integration complexity and simplifies connection management.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. Inventory all source and target system types used across the project.
2. Identify systems that serve similar purposes and can be consolidated.
3. For each distinct system type, create governed metadata connections with standardized configuration.
4. Standardize connection parameters across each system type: timeouts, batch sizes, fetch sizes, retry policies.
5. Document the purpose, business owner, and lifecycle status of each integration.
6. For new integrations, establish an architecture review process.
7. Consider creating abstraction layers (views, APIs, staging tables) to decouple jobs from underlying systems.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-003: Fixing Missing Error Handling

**rule_id:** RM-ARCH-003
**category:** architecture
**title:** Fixing missing error handling
**description:** Step-by-step guidance for resolving RULE-ARCH-003 by adding tTryCatch, reject flows, and error triggers.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-003 for detection logic.

**impact:** Resolving RULE-ARCH-003 prevents silent data loss and ensures predictable behavior on error conditions.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. For each flagged job, identify all write operations (database outputs, file outputs, API calls).
2. Add tTryCatch around each critical write section: Try block contains the write component; Catch block logs error details, rolls back partial operations, sends alert.
3. Add reject flows to all upstream tMap components: right-click tMap → Row reject → connect to tLogRow writing to a standardized error table with schema: job_name, component_name, timestamp, error_message, rejected_row_data.
4. Implement onComponentError triggers: connect to error-handling logic that logs and determines stop/continue.
5. Implement onSubjobError triggers: for jobs with subjobs, retry N times, then fail with escalation.
6. Test error scenarios: null values, connection timeouts, constraint violations, malformed files.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-004: Fixing Missing CI/CD Pipeline

**rule_id:** RM-ARCH-004
**category:** architecture
**title:** Fixing missing CI/CD pipeline
**description:** Step-by-step guidance for resolving RULE-ARCH-004 by implementing automated build and deployment.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-004 for detection logic.

**impact:** Resolving RULE-ARCH-004 enables consistent, auditable deployments with automated testing and rollback capability.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. Choose a CI/CD platform compatible with Talend: Jenkins with CI Builder, GitLab CI with CLI, GitHub Actions, or Azure DevOps.
2. Create the pipeline configuration file: build stage (compile, unit test, publish), test stage (deploy, integration test, validate), deploy stage (promote with approval gates).
3. Script the Talend build process using command-line tools: `mvn clean install -Dtalend.environment=TEST`.
4. Integrate automated testing: routine unit tests, integration tests with validation queries, row count comparisons.
5. Configure deployment environments in Talend Administration Center.
6. Set up notification channels for build success/failure.
7. Document the CI/CD process and train the team.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-005: Fixing Inconsistent Logging

**rule_id:** RM-ARCH-005
**category:** architecture
**title:** Fixing inconsistent logging
**description:** Step-by-step guidance for resolving RULE-ARCH-005 by implementing a standardized logging framework.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-005 for detection logic.

**impact:** Resolving RULE-ARCH-005 enables centralized monitoring, rapid troubleshooting, and audit compliance.

**classification:** Remediation — LOW severity
**remediation:**
1. Define a standard logging approach for the entire project. Recommended: centralized database logging with a shared log table. Alternative: structured JSON file logging with log shipper forwarding to ELK/Splunk.
2. Create a reusable logging subjob called with tRunJob: inputs include JOB_NAME, BATCH_ID, STATUS, ROWS_READ, ROWS_WRITTEN, ROWS_REJECTED, ERROR_COUNT, ERROR_MESSAGE. All jobs call this at start (STATUS='STARTED') and at end (STATUS='SUCCESS' or 'FAILURE').
3. Retrofit existing jobs: add logging to jobs with none, replace ad-hoc approaches with the standard, remove debug-level logging from production.
4. Define minimum logging requirements per job: job name, run ID, start timestamp, end timestamp, rows read, rows written, rows rejected, exit status.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-006: Fixing Missing Governed Metadata

**rule_id:** RM-ARCH-006
**category:** architecture
**title:** Fixing missing governed metadata
**description:** Step-by-step guidance for resolving RULE-ARCH-006 by migrating inline connections to governed metadata.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-006 for detection logic.

**impact:** Resolving RULE-ARCH-006 centralizes connection management so a single update propagates to all referencing jobs.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. Inventory all inline database and file connections currently used across the project.
2. For each distinct connection, create a governed metadata connection in the Repository. Use context variables for environment-specific values. Store passwords in context variables, not in the metadata connection.
3. Replace inline tDBInput/tDBOutput components with metadata-referencing versions. Verify component parameters resolve correctly.
4. For file connections, create metadata file connections with schema, delimiter, and encoding defined.
5. Remove hardcoded credentials. Replace inline usernames/passwords with context variable references. Store credentials in environment-specific `.properties` files. Apply secrets management in the CI/CD pipeline.
6. Validate jobs function correctly after migration. Establish a standard: no new jobs should use inline connections.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-007: Fixing Missing Parent/Child Job Decomposition

**rule_id:** RM-ARCH-007
**category:** architecture
**title:** Fixing missing parent/child job decomposition
**description:** Step-by-step guidance for resolving RULE-ARCH-007 by decomposing monolithic jobs into parent-child subjob structures.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-007 for detection logic.

**impact:** Resolving RULE-ARCH-007 enables partial restart on failure, parallel execution, and independent testing of each processing stage.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. Analyze the monolithic job to identify distinct processing stages (extract, transform, load, validate, archive, notify).
2. Create a parent orchestrator job. Extract each stage into a focused child job that is independently runnable with idempotent semantics.
3. Configure tRunJob in the parent for each child: set data passing strategy (row, file, or table), error handling (stop/continue/retry), and retry policy (up to 3 retries with exponential backoff).
4. Pass batch metadata to all children: batch ID, run ID, execution timestamp.
5. Add a tPrejob health check in the parent that verifies all required systems are reachable before any child runs.
6. Verify the orchestrated pipeline produces equivalent output to the original monolithic job.
7. Test partial restart: simulate a child failure and verify the parent correctly reports and allows selective re-execution.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-008: Fixing Missing Joblet Usage

**rule_id:** RM-ARCH-008
**category:** architecture
**title:** Fixing missing joblet usage
**description:** Step-by-step guidance for resolving RULE-ARCH-008 by creating joblets for reusable logic fragments.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-008 for detection logic.

**impact:** Resolving RULE-ARCH-008 eliminates duplication of small reusable patterns and enforces consistent behavior.

**classification:** Remediation — LOW severity
**remediation:**
1. Identify repeatable patterns across the project: connection setup, error logging, file archiving, notification, data validation.
2. For each candidate, create a new joblet in the Repository. Move the reusable component sequence into the joblet. Expose input/output ports and context variables as the interface. Test the joblet independently.
3. Replace duplicated component sequences in existing jobs with the new joblet.
4. For small reusable fragments (under 15 components) currently using tRunJob, consider migrating to joblets for simpler integration.
5. Store joblets in a dedicated project folder (Reusable/Joblets/) and version them alongside jobs.
6. Establish a standard: any component sequence appearing in 3+ jobs is a candidate for joblet extraction.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-009: Fixing Missing Standardized Error Framework

**rule_id:** RM-ARCH-009
**category:** architecture
**title:** Fixing missing standardized error framework
**description:** Step-by-step guidance for resolving RULE-ARCH-009 by designing and implementing a shared error framework.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-009 for detection logic.

**impact:** Resolving RULE-ARCH-009 enables cross-job error analysis and unified error dashboards.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. Design a shared error record schema: ERROR_ID (auto-generated), JOB_NAME, COMPONENT_NAME, ERROR_TIMESTAMP, ERROR_CODE, ERROR_MESSAGE, SEVERITY (FATAL/ERROR/WARNING/INFO), SOURCE_DATA (JSON), BATCH_ID.
2. Create a shared error log table in the project's metadata database with the above schema.
3. Create a reusable error handler subjob: inputs include JOB_NAME, COMPONENT_NAME, ERROR_CODE, ERROR_MESSAGE, SEVERITY, SOURCE_DATA, BATCH_ID. Behavior: inserts a record into the shared error log table.
4. Create a reusable tRunJob error handler subjob for parent orchestrators.
5. Migrate existing error handling: replace ad-hoc tLogRow error outputs with calls to the error handler. Standardize severity levels. Ensure all tTryCatch catch blocks call the error handler.
6. Create a monitoring query on the error log table: top error codes, error trend over time, jobs with highest error counts.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-010: Fixing Missing Monitoring and Alerting

**rule_id:** RM-ARCH-010
**category:** architecture
**title:** Fixing missing monitoring and alerting
**description:** Step-by-step guidance for resolving RULE-ARCH-010 by implementing metrics collection and monitoring infrastructure.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-010 for detection logic.

**impact:** Resolving RULE-ARCH-010 enables proactive alerting and operational visibility into pipeline health.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. Create a shared metrics table: METRIC_ID, JOB_NAME, BATCH_ID, RUN_ID, STATUS (STARTED/SUCCESS/FAILURE), START_TIME, END_TIME, DURATION_SECONDS, ROWS_READ, ROWS_WRITTEN, ROWS_REJECTED, ERROR_COUNT.
2. Create a reusable metrics subjob: at start, insert record with STATUS='STARTED'; at end, update with STATUS, duration, row counts, error count. All jobs call this subjob.
3. Add tPrejob health check to each production job: verify context variables are defined, source/target systems reachable, temp directories exist with free space. Exit with clear error message on failure.
4. Implement alerting: configure email notification in TAC for job failures; add tSendMail in error handler for high-severity errors; create dashboard queries on the metrics table for job health, duration trends, error rates, and anomaly detection.
5. Define SLAs for critical jobs and create dashboard alerts when thresholds are breached.

**source:** Talend Health Analyzer remediation documentation

---

## RM-ARCH-011: Fixing Missing Exception Classification and Framework

**rule_id:** RM-ARCH-011
**category:** architecture
**title:** Fixing missing exception classification and framework
**description:** Step-by-step guidance for resolving RULE-ARCH-011 by implementing exception classification and a global exception handler.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-ARCH-011 for detection logic.

**impact:** Resolving RULE-ARCH-011 ensures appropriate responses for different exception types and eliminates unnecessary job failures from transient errors.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. Create exception classification logic: Transient (timeout, deadlock — retry 3x with backoff); Data (constraint violation, type mismatch — log, continue); Configuration (missing context — stop, alert); System (OOM, disk full — stop, escalate); Security (auth failure — stop, escalate to security).
2. Implement retry logic with exponential backoff: create a parent orchestrator pattern with tLoop and tWaitFor. On transient failure: wait 30s, retry; second: wait 60s; third: wait 120s, then fail. Pass attempt number as context variable.
3. Create a global exception handler subjob: inputs include JOB_NAME, COMPONENT_NAME, ERROR_MESSAGE, STACK_TRACE, BATCH_ID, SEVERITY, EXCEPTION_CLASS. Behavior: insert error record into shared error log; if FATAL or CRITICAL severity, send immediate alert; if Configuration/System/Security class, send immediate alert; if Transient and retry exhausted, send alert; update metrics table to FAILURE.
4. Add try-catch blocks to all tJava/tJavaRow components. In the catch block, call the global exception handler via context variable, then re-throw as RuntimeException to propagate to Talend.
5. Migrate existing tTryCatch components: inspect error message to determine exception class, call global exception handler, implement retry for transient exceptions.

**source:** Talend Health Analyzer remediation documentation

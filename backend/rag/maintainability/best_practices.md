# Maintainability Best Practices

---

## BP-MAIN-001: Naming Standards

**rule_id:** BP-MAIN-001
**category:** maintainability
**title:** Naming Standards
**description:**
Follow a consistent job naming pattern: `{Domain}_{Process}_{Frequency}` — `Finance_AR_Processing_Daily`, `Sales_OrderImport_Hourly`. Follow component naming pattern: `{ComponentType}_{BusinessPurpose}` — `tDBInput_Orders`, `tMap_OrderEnrich`, `tFileOutput_Report`. Avoid default auto-generated names (`tMap_1`, `tJava_2`). Follow context variable naming: `{ENVIRONMENT}_{SCOPE}_{NAME}` — `DEV_DB_ORDERS_URL`, `PROD_FILE_STAGING_PATH`. Follow routine naming: `{Category}_{Function}` — `DateUtils_Format`, `Validation_EmailCheck`. Use environment names for context groups: DEV, TEST, UAT, PROD.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Maintainability Finding RULE-COMP-003.

**impact:**
Consistent naming makes job logic understandable across the team, reduces onboarding time for new developers, and enables automated searches and reporting across the project.

**classification:** Best Practice
**remediation:**
Establish a team-wide naming convention document. Audit existing jobs for violations. Rename components in production jobs. Add naming convention checks to the code review process.

**source:** Talend maintainability best practices

---

## BP-MAIN-002: Reusable Components

**rule_id:** BP-MAIN-002
**category:** maintainability
**title:** Reusable Components
**description:**
Break monolithic jobs into focused subjobs with single responsibility. Use tRunJob to call subjobs from a parent orchestrator. Design subjobs to be independently testable. Maintain a catalog of reusable subjob templates: file ingestion, database load, data validation, notification. Extract repeated transformation logic into Talend routines. Use tLibraryLoad to manage external JAR dependencies. Create template jobs for common integration patterns stored in a dedicated Templates folder.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Maintainability Finding RULE-COMP-007.

**impact:**
Reusable components eliminate code duplication, reduce maintenance effort (one fix propagates everywhere), and enforce consistent patterns across the project.

**classification:** Best Practice
**remediation:**
Identify repeated patterns across jobs (identical tJava code, identical tMap configurations, identical SQL queries). Extract into routines, metadata connections, or reusable subjobs. Store templates in a shared project folder.

**source:** Talend maintainability best practices

---

## BP-MAIN-003: Metadata Reuse

**rule_id:** BP-MAIN-003
**category:** maintainability
**title:** Metadata Reuse
**description:**
Use Talend Repository Metadata (Db Connections) for all database connections. Define the connection once — all jobs reference the same governed connection. Use context variables inside metadata connections for environment-specific values. Define file schemas once using Metadata → File Delimited or File XML. Drag metadata connections directly onto the job designer to auto-create correctly configured components. Use tSchemaComplianceCheck to validate incoming data against metadata schemas. Maintain a change log for metadata schema versions.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Architecture Finding RULE-ARCH-006.

**impact:**
Governed metadata centralizes connection management — a single change propagates to all referencing jobs. Inline connections require updating every job individually, creating maintenance overhead and inconsistency risk.

**classification:** Best Practice
**remediation:**
Create governed metadata connections for every database and file schema used in the project. Replace inline components with metadata-referencing versions. Remove hardcoded credentials from inline connections.

**source:** Talend maintainability best practices

---

## BP-MAIN-004: Context Standardization

**rule_id:** BP-MAIN-004
**category:** maintainability
**title:** Context Standardization
**description:**
Create context groups per environment: DEV, TEST, UAT, PROD. Define the same set of context variables in every group — values differ, not names. Organize variables by prefix: DB_ for databases, FILE_ for paths, API_ for endpoints, SFTP_ for connections, EMAIL_ for notifications, JOB_ for parameters, LOG_ for logging. Every component parameter that differs between environments must use a context variable. Validate required context variables at job startup using tPrejob. Use `.properties` files versioned in Git with production values injected via CI/CD.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Maintainability Finding RULE-COMP-009.

**impact:**
Standardized contexts make environment promotion predictable and auditable. Hardcoded environment values make deployment error-prone and violate security best practices.

**classification:** Best Practice
**remediation:**
Scan all component parameters for hardcoded environment-specific values. Migrate to context variables following the project naming convention. Create `.properties` files per environment. Add tPrejob context validation.

**source:** Talend maintainability best practices

---

## BP-MAIN-005: Job Documentation

**rule_id:** BP-MAIN-005
**category:** maintainability
**title:** Job Documentation
**description:**
Document the following in each job: purpose (what business process does this support?), inputs (source systems, tables, files), outputs (target systems, tables, files), dependencies (predecessor and successor jobs), frequency (run schedule and expected window), owner (business and technical owners), runbook (steps on failure). Add notes to every tMap with more than 5 expression lines and every tJava/tJavaRow/tJavaFlex. Document edge cases: null handling, empty files, duplicate keys. Maintain data lineage documentation for critical pipelines. Keep a changelog of significant modifications.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Maintainability Finding RULE-COMP-004.

**impact:**
Undocumented transformation logic creates knowledge silos. When the original developer leaves, business rules and edge cases are lost, leading to slower troubleshooting and higher defect rates.

**classification:** Best Practice
**remediation:**
Add documentation to all complex components (tMap with 5+ expressions, all tJava). Document job-level metadata: purpose, inputs, outputs, dependencies. Maintain a changelog. Create data lineage documentation for critical pipelines.

**source:** Talend maintainability best practices

---

## BP-MAIN-006: Disabled Components

**rule_id:** BP-MAIN-006
**category:** maintainability
**title:** Disabled Components
**description:**
Disabled components in production jobs are not allowed — remove them. Disabled components in development jobs are tolerated short-term but should be removed before promotion. Never leave a component disabled for more than one sprint (2 weeks). If code is needed later, version control is the correct mechanism. Disabled components are still compiled into the job, adding to build time and memory footprint. They confuse team members who cannot distinguish dead code from conditionally needed logic.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Maintainability Finding RULE-COMP-001.

**impact:**
Disabled components create clutter, increase compilation time, and risk accidental re-enabling of obsolete logic. Each disabled component is dead code that obscures the job's actual functionality.

**classification:** Best Practice
**remediation:**
Review each disabled component. If obsolete, remove it. If intentionally retained, document the reason. Components inactive for more than 90 days should be removed. Run the analyzer after cleanup.

**source:** Talend maintainability best practices

---

## BP-MAIN-007: Unused Components and Variables

**rule_id:** BP-MAIN-007
**category:** maintainability
**title:** Unused Components and Variables
**description:**
Remove all unused components before promoting a job to test or production. Unused components are active but not connected to any downstream component. Remove unused context variables from context groups to avoid confusion. Remove unused routines after verifying no job references them. Schedule a quarterly project-wide cleanup to identify and remove orphaned artifacts. Use the Talend Studio Dependency Viewer to find unused routines.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Maintainability Finding RULE-COMP-010.

**impact:**
Unused components inflate job size and suggest incomplete cleanup. Unused context variables create confusion — team members cannot tell if the variable is intentionally unused or orphaned. Both increase cognitive load during maintenance.

**classification:** Best Practice
**remediation:**
Inspect jobs for components with no output connections. Check context variable definitions against component references. Remove unused items. Schedule quarterly audits to prevent accumulation.

**source:** Talend maintainability best practices

---

## BP-MAIN-008: Code Duplication Prevention

**rule_id:** BP-MAIN-008
**category:** maintainability
**title:** Code Duplication Prevention
**description:**
Prevent code duplication using these strategies: Talend routines for repeated Java logic; metadata connections for repeated DB/file schemas; context variables for repeated configuration values; reusable subjobs for repeated workflows; tRunJob to call subjobs instead of replicating logic; tLibraryLoad for centralized library management; template jobs as starting points. Prioritize fixing duplication that causes the most maintenance pain: queries with changing schemas, business logic that needs updates, identical large lookups loaded N times.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Maintainability Finding RULE-COMP-006.

**impact:**
Duplicate code means every bug fix, schema change, or optimization must be applied N times across N copies. This multiplies maintenance effort and creates inconsistency risk when some copies are missed.

**classification:** Best Practice
**remediation:**
Identify identical tMap configurations, copy-pasted tJava code, repeated SQL queries, and repeated file schemas. Extract shared logic into routines, metadata connections, or subjobs. Use template jobs to prevent future duplication.

**source:** Talend maintainability best practices

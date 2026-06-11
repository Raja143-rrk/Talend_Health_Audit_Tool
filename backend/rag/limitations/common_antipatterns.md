# Common Talend Anti-Patterns

---

## AP-001: Monolithic Jobs

**rule_id:** AP-001
**category:** limitations
**title:** Monolithic jobs
**description:** One job doing everything — extract, transform, load, report. Makes debugging and reuse nearly impossible. A single failure in the final stage invalidates all prior work.

**detection_logic:** Check for jobs with more than 50 components that do not use tRunJob to delegate to subjobs. Verify the job performs multiple unrelated processing stages.

**impact:** Monolithic jobs cannot be partially restarted, are hard to test, and obscure the data flow logic.

**classification:** Anti-Pattern
**remediation:** Decompose into focused subjobs (extract, transform, load) linked by a parent orchestrator via tRunJob.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-002: Copy-Paste Components

**rule_id:** AP-002
**category:** limitations
**title:** Copy-paste components
**description:** Duplicating the same component configuration across many jobs instead of using metadata connections or reusable subjobs.

**detection_logic:** Compare component parameters across similar components in different jobs. Flag identical configurations appearing in 3 or more jobs.

**impact:** Every configuration change must be applied N times across N jobs, creating maintenance overhead and inconsistency risk.

**classification:** Anti-Pattern
**remediation:** Extract shared configurations into governed metadata connections, Talend routines, or reusable subjobs.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-003: Disabled Component Graveyard

**rule_id:** AP-003
**category:** limitations
**title:** Disabled component graveyard
**description:** Leaving dozens of disabled components in production jobs just in case they are needed later. These components are still compiled and consume resources.

**detection_logic:** Count disabled components in production jobs. More than 3 disabled components in a single job indicates this anti-pattern.

**impact:** Dead code increases compilation time, memory footprint, and confuses team members.

**classification:** Anti-Pattern
**remediation:** Remove disabled components. Version control is the appropriate mechanism for preserving unused code.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-004: Hardcoded Everything

**rule_id:** AP-004
**category:** limitations
**title:** Hardcoded everything
**description:** Embedding environment-specific values directly in component parameters instead of using context variables.

**detection_logic:** Scan component parameters for hardcoded hostnames, ports, file paths, credentials, and connection strings instead of `context.*` references.

**impact:** Environment promotion becomes error-prone, security is compromised, and configuration management is impossible.

**classification:** Anti-Pattern
**remediation:** Use context variables for all environment-specific values. Create `.properties` files per environment.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-005: No Error Handling

**rule_id:** AP-005
**category:** limitations
**title:** No error handling
**description:** Data flows without reject links, assuming every row will succeed. No tTryCatch around critical operations.

**detection_logic:** Check tMap components for missing reject outputs. Check for absence of tTryCatch around database writes and file operations.

**impact:** A single bad record crashes the entire job. Silent data corruption occurs when rows fail mapping conditions without detection.

**classification:** Anti-Pattern
**remediation:** Add reject flows to all tMap components. Wrap critical operations with tTryCatch. Implement error logging.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-006: tJava for Everything

**rule_id:** AP-006
**category:** limitations
**title:** tJava for everything
**description:** Writing all transformation logic in tJava instead of using Talend's native components. Bypasses Talend's code optimization and increases maintenance burden.

**detection_logic:** Count tJava, tJavaRow, and tJavaFlex components. More than 3 in a single job indicates this anti-pattern.

**impact:** Custom Java code cannot be optimized by Talend, increases compilation time, and complicates migration.

**classification:** Anti-Pattern
**remediation:** Replace standard transformations with native Talend components. Extract remaining custom logic into Talend routines.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-007: Row-by-Row Processing

**rule_id:** AP-007
**category:** limitations
**title:** Row-by-row processing
**description:** Using tJavaRow for operations that could be done with set-based native components. Each row executes individually, preventing database-level optimizations.

**detection_logic:** Identify tJavaRow components performing operations (aggregation, filtering, lookups) that could be handled by tMap or SQL.

**impact:** Row-by-row processing is orders of magnitude slower than set-based operations and cannot be parallelized.

**classification:** Anti-Pattern
**remediation:** Replace row-by-row tJavaRow operations with tMap expressions, database SQL pushdown, or Talend routines operating on batches.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-008: Ignoring Commit Sizes

**rule_id:** AP-008
**category:** limitations
**title:** Ignoring commit sizes
**description:** Using default commit intervals (often 1 or 10) for bulk load operations, causing excessive transaction overhead.

**detection_logic:** Check COMMIT_EVERY, BATCH_SIZE parameters on output components. Values less than 100 for bulk operations indicate this anti-pattern.

**impact:** Throughput can be 10x lower than optimal due to excessive transaction commits.

**classification:** Anti-Pattern
**remediation:** Benchmark and set appropriate commit sizes (500-1000 for OLTP, 5000-10000 for bulk loads).

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-009: No Contexts

**rule_id:** AP-009
**category:** limitations
**title:** No contexts
**description:** No context groups defined, making environment promotion a manual error-prone process. All environment-specific values are hardcoded in job designs.

**detection_logic:** Check project inventory for zero context groups. All job parameter values use hardcoded strings instead of `context.*` references.

**impact:** Every environment deployment requires manually editing multiple jobs. Credentials are exposed in job metadata.

**classification:** Anti-Pattern
**remediation:** Create context groups per environment. Migrate hardcoded values to context variables.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-010: No Governed Metadata

**rule_id:** AP-010
**category:** limitations
**title:** No governed metadata
**description:** Every job defines its own connections instead of using shared tMetadataConnection components. Connection changes require updating every job individually.

**detection_logic:** Check database connection components for inline configuration vs. metadata references. More than 50% inline connections indicates this anti-pattern.

**impact:** Changing a database endpoint requires updating N jobs instead of one metadata connection. Inline credentials bypass security audits.

**classification:** Anti-Pattern
**remediation:** Create governed metadata connections for all databases and file schemas. Replace inline components with metadata references.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-011: No Naming Standards

**rule_id:** AP-011
**category:** limitations
**title:** No naming standards
**description:** Components named tMap_1, tMap_2, tMap_3 with no indication of their purpose. Job names are generic (NewJob, Job1).

**detection_logic:** Check component labels for default auto-generated patterns (`tMap_1`, `tDBInput_3`). Check job names for generic patterns (`Job1`, `NewJob`).

**impact:** Job logic is hard to understand at a glance. Finding specific components requires examining each one individually.

**classification:** Anti-Pattern
**remediation:** Establish naming conventions for jobs and components. Rename existing items to follow the convention.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-012: Missing Documentation

**rule_id:** AP-012
**category:** limitations
**title:** Missing documentation
**description:** No comments or descriptions explaining non-obvious transformation logic. Complex tMap expressions and tJava code are undocumented.

**detection_logic:** Check documentation/comment fields on tMap components with more than 5 expressions and all tJava/tJavaRow components.

**impact:** Business knowledge is lost when the original developer leaves. Troubleshooting and onboarding are significantly slower.

**classification:** Anti-Pattern
**remediation:** Add documentation to all complex components explaining the business rule, edge cases, and rationale.

**source:** Talend Health Analyzer anti-pattern catalog

---

## AP-013: Inconsistent Patterns

**rule_id:** AP-013
**category:** limitations
**title:** Inconsistent patterns
**description:** Each developer uses different error handling, logging, and component style. No standardized approach across the project.

**detection_logic:** Sample jobs across the project and compare error handling approaches, logging mechanisms, and coding styles. Three or more distinct approaches indicate this anti-pattern.

**impact:** Team members struggle to understand each other's jobs. Operational monitoring is difficult when every job logs differently.

**classification:** Anti-Pattern
**remediation:** Establish and enforce project-wide standards for error handling, logging, naming, and job structure.

**source:** Talend Health Analyzer anti-pattern catalog

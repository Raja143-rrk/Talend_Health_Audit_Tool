# Security Findings

---

## RULE-SEC-001: Hardcoded Password

**rule_id:** RULE-SEC-001
**category:** security
**title:** Hardcoded password
**description:** A component contains a password-like parameter value. The rule engine scans all component parameters for names containing keywords: `password`, `passwd`, `pwd` with a non-empty value.

**detection_logic:** For each component instance, iterate over all parameter name-value pairs. If a parameter name (case-insensitive) contains any password-related keyword AND the corresponding value is non-empty, flag the component. Disabled components are excluded from scoring but the finding remains visible for review.

**impact:** Hardcoded passwords in Talend job metadata are visible to anyone with project or repository access. They cannot be centrally rotated, violating compliance standards (SOC2, PCI-DSS, SOX, HIPAA). If compromised, every environment using that job is exposed. This is an active component-level security finding.

**classification:** Risk — Hardcoded credential that requires technical access to exploit but poses immediate compliance violation.

**remediation:** Replace hardcoded password values with encrypted context variables. Create a context variable for each credential, enable encryption via the key icon in the context editor, and reference it as `context.variable_name` in the component parameter. Rotate any credential that was hardcoded. See Security Remediation → Fixing Hardcoded Credentials (RULE-SEC-001) for detailed steps.

**source:** Talend Health Analyzer security rule engine

---

## RULE-SEC-002: Inline JDBC URL

**rule_id:** RULE-SEC-002
**category:** security
**title:** Inline JDBC URL
**description:** A component contains a parameter value starting with `jdbc:` indicating an inline database connection string. Inline JDBC URLs frequently embed hostnames, ports, credentials, and connection parameters directly in job designs.

**detection_logic:** For each component parameter value, check if the value (when lowercased and trimmed) starts with `jdbc:`. If matched, flag the component. This covers tJDBCConnection, tMysqlConnection, tPostgresqlConnection, tOracleConnection, tMSSqlConnection, and any custom component with a JDBC parameter.

**impact:** Inline JDBC URLs expose database connection details beyond the development team. They bypass governed metadata connections, making security audits incomplete and environment promotion error-prone. If credentials are embedded in the URL, a single workspace export exposes all database access points. This is an active component-level security finding with a 5-point deduction.

**classification:** Risk — Systemic weakness that requires technical access to exploit.
**remediation:** Create governed tMetadataConnection components in the Repository. Replace inline JDBC components with metadata-referencing versions. Remove inline JDBC strings from all component parameters. See Security Remediation → Fixing Inline JDBC URLs (RULE-SEC-002) for detailed steps.

**source:** Talend Health Analyzer security rule engine

---

## RULE-SEC-003: High Number of Security Findings

**rule_id:** RULE-SEC-003
**category:** security
**title:** High number of security findings
**description:** The analysis contains more than 5 security findings across all components. This indicates systemic security weaknesses rather than isolated issues.

**detection_logic:** Count the total number of active-component security findings (RULE-SEC-001 + RULE-SEC-002 + any other security rules). If the count exceeds 5, flag the inventory. Findings from disabled components are included in the count but excluded from scoring.

**impact:** A high volume of security issues indicates that credential management and connection security practices are not consistently applied across the project. This increases the risk of a production data breach and makes compliance audits difficult to pass. This is an inventory-level security finding with a 5-point deduction, applied once per analysis.

**classification:** Risk — Systemic weakness reflecting widespread insecure practices.
**remediation:** Triage findings by severity (CRITICAL first). Perform root cause analysis to identify patterns. Implement preventative controls: shared context templates, security checklists, CI/CD integration blocking CRITICAL/HIGH findings. Schedule regular security scans. See Security Remediation → Reducing Overall Security Findings (RULE-SEC-003) for detailed steps.

**source:** Talend Health Analyzer security rule engine

---

## RULE-SEC-004: Missing or Unencrypted Credential Context Variables

**rule_id:** RULE-SEC-004
**category:** security
**title:** Missing or unencrypted credential context variables
**description:** The project uses credential-like parameter values in component parameters but has not defined corresponding encrypted context variables. Alternatively, context variables that clearly hold credentials are stored without encryption enabled.

**detection_logic:** Scan all component parameters for values matching `context.<name>` where the referenced context variable name suggests a credential (password, pwd, secret, token, key). Cross-reference against the inventory's context definitions. Flag if: the referenced context variable does not exist in any context group, the context variable exists but does not have encryption enabled, or no context groups are defined at all.

**impact:** Even when developers attempt to use context variables, missing or unencrypted definitions leave credentials exposed. Unencrypted context variables store values in plaintext within the job's compiled code and logs, providing no real security benefit over hardcoding. This is an inventory-level security finding with a 5-point deduction.

**classification:** Risk — Incomplete or insecure context variable implementation.
**remediation:** Audit context definitions for missing variables and unencrypted sensitive values. Create missing context variables matching component references. Enable encryption on sensitive variables via the key icon. Validate context coverage across all environments. See Security Remediation → Fixing Missing or Unencrypted Context Variables (RULE-SEC-004) for detailed steps.

**source:** Talend Health Analyzer security rule engine

---

## RULE-SEC-005: API Key or Token Exposed in Component

**rule_id:** RULE-SEC-005
**category:** security
**title:** API key or token exposed in component
**description:** An API key, bearer token, or OAuth client secret is embedded directly in a component parameter value. API credentials are commonly found in tRestClient, tRestRequest, or tHttpRequest component headers, URL query parameters, or configuration fields.

**detection_logic:** For each component, scan parameter names and values for patterns indicating API credentials: parameter names containing `api_key`, `apikey`, `api_secret`, `bearer`, `token`, `oauth`, `client_secret`, `access_key`, `auth_token`; parameter values that look like API keys (alphanumeric strings of 20+ characters in sensitive parameter positions); header configuration parameters containing `Authorization: Bearer` or `X-API-Key:` with a non-context-variable value.

**impact:** Exposed API keys and tokens allow unauthorized access to third-party services, cloud resources, and internal APIs. Unlike database credentials, API keys often have broad permissions and may not trigger standard security alerts when misused. This is an active component-level security finding with a 10-point deduction.

**classification:** Critical Risk — Direct API credential exposure with immediate exploitation risk.
**remediation:** Revoke and rotate the exposed key/token immediately via the provider's admin console. Store new credentials in encrypted context variables. Configure REST components to read credentials from context variables. See Security Remediation → Fixing Exposed API Keys and Tokens (RULE-SEC-005) for detailed steps.

**source:** Talend Health Analyzer security rule engine

---

## RULE-SEC-006: Insecure Database Connection Configuration

**rule_id:** RULE-SEC-006
**category:** security
**title:** Insecure database connection configuration
**description:** A database connection component is configured without encryption (TLS/SSL) or with security-weakening settings such as `trustAllCertificates=true`, `allowPublicKeyRetrieval=true`, or `requireSSL=false`.

**detection_logic:** For each database connection component (tJDBCConnection, tMysqlConnection, tPostgresqlConnection, tOracleConnection, tMSSqlConnection, tRedshiftConnection, tSnowflakeConnection), scan parameters for: `useSSL=false` or missing `useSSL` parameter (MySQL); `sslmode=disable` or `sslmode=allow` or `sslmode=prefer` (PostgreSQL); `trustAllCertificates=true` (generic); `allowPublicKeyRetrieval=true` (MySQL); `encrypt=false` or missing `encrypt` parameter (SQL Server, Snowflake); missing TLS/SSL-related parameters entirely.

**impact:** Data transmitted over unencrypted database connections can be intercepted by anyone with network access to the traffic path. In cloud environments, this exposes sensitive data to potential interception between the Talend runtime and the database service. This is an active component-level security finding with a 2-point deduction.

**classification:** Warning — Configuration weakness that increases attack surface.
**remediation:** Enable TLS/SSL per database type: set `useSSL=true` and `requireSSL=true` for MySQL; set `sslmode=verify-full` for PostgreSQL; set `encrypt=true` for SQL Server; set `ssl=on` for Snowflake. Store TLS configuration in context variables. See Security Remediation → Fixing Insecure Database Connections (RULE-SEC-006) for database-specific configuration steps.

**source:** Talend Health Analyzer security rule engine

---

## RULE-SEC-007: Cross-Environment Context Exposure

**rule_id:** RULE-SEC-007
**category:** security
**title:** Cross-environment context exposure
**description:** Production-like values are detected in context variable defaults or development context files, indicating risk of production data exposure to non-production environments.

**detection_logic:** Scan context variable default values and all `.properties` file patterns (DEV, TEST) for: hostnames or URLs containing `prod`, `production`, `live`, or internal production domain patterns; database names indicating production instances; values that match known production connection patterns; service principals or accounts with names suggesting elevated privileges.

**impact:** Development and test environments with production credentials expose critical systems to developers, contractors, and CI/CD systems that should not have production access. A compromised development workstation could lead to production data exfiltration. This is an inventory-level security finding with a 2-point deduction.

**classification:** Warning — Information disclosure that increases attack surface.
**remediation:** Create distinct context groups per environment. Move production values out of defaults and DEV properties. Implement environment promotion controls with CI/CD context injection. See Security Remediation → Fixing Cross-Environment Context Exposure (RULE-SEC-007) for detailed steps.

**source:** Talend Health Analyzer security rule engine

---

## RULE-SEC-008: Hardcoded Username

**rule_id:** RULE-SEC-008
**category:** security
**title:** Hardcoded username
**description:** A component contains a username-like parameter value. The rule engine scans all component parameters for names containing keywords: `username`, `user`, `uid` with a non-empty value.

**detection_logic:** For each component instance, iterate over all parameter name-value pairs. If a parameter name (case-insensitive) contains any username-related keyword AND the corresponding value is non-empty, flag the component. Disabled components are excluded from scoring but the finding remains visible for review.

**impact:** Hardcoded usernames in Talend job metadata reduce portability across environments and increase maintenance overhead when credentials change. While less immediately exploitable than passwords, embedded usernames indicate poor credential management practices.

**classification:** Warning — Non-credential exposure indicating configuration management weakness.

**remediation:** Externalize usernames into environment-specific context variables. Create a context variable for each username and reference it as `context.variable_name` in the component parameter.

**source:** Talend Health Analyzer security rule engine

---

## Severity Classification Guide

| Severity | Criteria | Examples |
|----------|----------|---------|
| **Critical Risk** | Direct credential or key exposure with immediate exploitation risk | Plaintext API keys, embedded tokens, exposed production credentials |
| **Risk** | Credential or systemic weakness that requires technical access to exploit | Hardcoded passwords, inline JDBC URLs, missing encryption, insecure connections |
| **Warning** | Configuration weaknesses, policy violations, or non-critical exposures | Hardcoded usernames, missing context variables, disabled TLS, cross-environment leaks |
| **Advisory** | Minor issues, redundant elements, or non-critical improvements | Disabled components, disconnected components, unused context variables, redundant components |
| **Informational** | Observations without direct security or operational impact | Poor naming conventions, documentation missing, layout/design improvements |

# Security Remediation

---

## RM-SEC-001: Fixing Hardcoded Credentials

**rule_id:** RM-SEC-001
**category:** security
**title:** Fixing hardcoded credentials
**description:** Step-by-step guidance for resolving RULE-SEC-001 by replacing hardcoded credential values with encrypted context variables.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-SEC-001 for detection logic.

**impact:** Resolving RULE-SEC-001 eliminates direct credential exposure in job metadata, bringing the project into compliance with security standards and enabling centralized credential rotation.

**classification:** Remediation — CRITICAL severity
**remediation:**
1. Review the complete findings list for all RULE-SEC-001 violations. Note each affected component, job name, and the specific parameter with the hardcoded value. Prioritize CRITICAL findings in jobs that run against production systems.
2. In Talend Studio, open the context editor for each affected job. Create a new context variable for each credential (e.g., `context.db_password`, `context.sftp_password`). Enable encryption: click the key icon next to the variable to mark it as encrypted. Set a meaningful default value for development environments only.
3. For each flagged component, replace the hardcoded credential value with `context.variable_name`. Example: Replace `password="P@ssw0rd123"` with `password=context.db_password`. Verify the component functions correctly using the default context value in DEV.
4. Create `.properties` files for each environment: `dev.properties`, `test.properties`, `uat.properties`, `prod.properties`. Add the context variable values to each file. For production, use the build/deployment pipeline to inject values from a secrets vault. Never commit production credential values to version control.
5. Rotate any credential that was hardcoded in job metadata immediately. The credential may have been captured in: version control history, backup exports, error logs, or developer workstations. Follow your organization's credential rotation policy; if none exists, rotate immediately.
6. Run the Talend Health Analyzer again to confirm the finding is resolved. Execute the affected jobs in each environment to verify connectivity. Update your CI/CD pipeline to reject builds with hardcoded credentials.

**source:** Talend Health Analyzer remediation documentation

---

## RM-SEC-002: Fixing Inline JDBC URLs

**rule_id:** RM-SEC-002
**category:** security
**title:** Fixing inline JDBC URLs
**description:** Step-by-step guidance for resolving RULE-SEC-002 by migrating inline JDBC connections to governed metadata connections.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-SEC-002 for detection logic.

**impact:** Resolving RULE-SEC-002 centralizes database connection management, removes inline credentials from job designs, and enables environment-agnostic connection configuration.

**classification:** Remediation — HIGH severity
**remediation:**
1. In Talend Studio's Repository tree, right-click on Metadata → Db Connections → Create connection. Define the connection using the database type, host, port, and database name. Map all connection properties to context variables: `context.db_host`, `context.db_port`, `context.db_name`, `context.db_user`, `context.db_password`. Test the connection in DEV and save.
2. For each flagged tJDBCConnection or database-specific connection component: delete the component from the job design (or disable as a temporary measure). Drag the governed metadata connection from the Repository onto the job design canvas. This creates a component pre-configured with the metadata settings. Ensure context variable mappings are inherited correctly.
3. If the same inline pattern is repeated across multiple jobs, update each one. For large projects, consider using Talend's batch update feature or search-and-replace across job designs. Remove all inline JDBC strings from component parameters.
4. Once all jobs use governed metadata connections, verify each environment: DEV against development database instances, TEST with integration test suite, UAT with user acceptance tests, PROD during a maintenance window with rollback plan. Remove the original inline JDBC connections from the repository.

**source:** Talend Health Analyzer remediation documentation

---

## RM-SEC-003: Fixing Missing or Unencrypted Context Variables

**rule_id:** RM-SEC-003
**category:** security
**title:** Fixing missing or unencrypted context variables
**description:** Step-by-step guidance for resolving RULE-SEC-003 by creating missing context variables and enabling encryption on sensitive ones.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-SEC-003 for detection logic.

**impact:** Resolving RULE-SEC-003 ensures all credential references in component parameters are backed by properly defined encrypted context variables, closing a common security gap.

**classification:** Remediation — HIGH severity
**remediation:**
1. Open the context editor for each job and review all defined context variables. Identify variables that contain sensitive data but lack encryption (no key icon next to the value). Identify `context.variable` references in components that do not have corresponding variable definitions.
2. For each undefined `context.*` reference found in component parameters: create the context variable with the correct name matching the reference. Set an appropriate default value for development. Enable encryption if the variable holds sensitive data.
3. In the context editor, click the key icon for each sensitive variable to enable encryption. Encrypted variables show asterisks in the context editor and are stored encrypted in the compiled job. After enabling encryption, update the default values (they will be cleared by the encryption process).
4. Ensure every environment has the required context variables defined in its `.properties` file. Missing context variables cause job failures at runtime — use a validation script to check completeness. Run the analyzer again to verify the finding is resolved.

**source:** Talend Health Analyzer remediation documentation

---

## RM-SEC-004: Fixing Exposed API Keys and Tokens

**rule_id:** RM-SEC-004
**category:** security
**title:** Fixing exposed API keys and tokens
**description:** Step-by-step guidance for resolving RULE-SEC-004 by securing API credentials in Talend REST components.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-SEC-004 for detection logic.

**impact:** Resolving RULE-SEC-004 eliminates unauthorized API access risk and ensures API credentials are managed securely and rotated properly.

**classification:** Remediation — CRITICAL severity
**remediation:**
1. Review findings for RULE-SEC-004 to identify all API components with exposed keys or tokens. Common locations: tRestClient headers, tRestRequest configuration, tHttpRequest URLs, tLibraryLoad initialization parameters. Note the service or API provider for each exposed credential.
2. For each exposed API key or token: revoke the current key/token through the provider's admin console. Generate a new key/token with the minimum required permissions. Record the rotation in your credential management system. Do not skip this step — exposed keys may have been captured in logs, exports, or developer workstations.
3. Create encrypted context variables for each API credential: `context.api_client_id`, `context.api_client_secret`, `context.api_token`. For OAuth2 flows, store the client ID and client secret in encrypted context variables, not the access token (tokens are short-lived and obtained programmatically). Configure tRestClient to read credentials from context: set the Authorization header to `Bearer context.api_token`.
4. In tRestClient/tRestRequest advanced settings: set connection timeout and read timeout via context variables. Disable `trustAllCertificates` in production (set to false). Configure proxy settings through context variables if needed. Never log request or response payloads in production — disable debug-level logging. Verify the API integration works in each environment after migration.
5. Set up monitoring for API credential expiry and rotate before expiration. Log API call metadata (status codes, response times) without sensitive payload data. Configure alerts for API authentication failures which may indicate compromised credentials.

**source:** Talend Health Analyzer remediation documentation

---

## RM-SEC-005: Fixing Insecure Database Connections

**rule_id:** RM-SEC-005
**category:** security
**title:** Fixing insecure database connections
**description:** Step-by-step guidance for resolving RULE-SEC-005 by enabling TLS/SSL encryption on database connections per database type.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-SEC-005 for detection logic.

**impact:** Resolving RULE-SEC-005 ensures all data in transit between the Talend runtime and databases is encrypted, preventing network-level interception.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. Review RULE-SEC-005 findings to list all database connections without encryption. Note the database type and the specific insecure parameters detected. Check whether the target database supports TLS/SSL connections.
2. Configure TLS per database type:
   - **MySQL / MariaDB:** Add or set `useSSL=true` and `requireSSL=true`. Set `verifyServerCertificate=true` in production. Remove `allowPublicKeyRetrieval=true` if set.
   - **PostgreSQL:** Set `sslmode=require` or `sslmode=verify-full` in production. Use `sslmode=verify-full` with `sslrootcert` to validate the server certificate. Avoid `sslmode=disable`, `sslmode=allow`, or `sslmode=prefer`.
   - **SQL Server:** Set `encrypt=true` in the connection string. Set `trustServerCertificate=false` in production. Use `hostNameInCertificate` if the certificate CN does not match the server hostname.
   - **Snowflake:** Set `ssl=on` (enabled by default in recent drivers). Configure `private_key_file` and `private_key_file_pwd` for key-pair authentication. Avoid `authenticator=externalbrowser` in automated jobs.
3. Move TLS-related parameters to context variables for environment-specific control (e.g., `context.db_use_ssl=true`, `context.db_ssl_mode=verify-full`). This allows different TLS settings per environment (self-signed certs in DEV, CA-verified in PROD).
4. Verify TLS-enabled connections in each environment. Use network monitoring to confirm data is encrypted in transit. Run the analyzer again to confirm all findings are resolved.

**source:** Talend Health Analyzer remediation documentation

---

## RM-SEC-006: Fixing Cross-Environment Context Exposure

**rule_id:** RM-SEC-006
**category:** security
**title:** Fixing cross-environment context exposure
**description:** Step-by-step guidance for resolving RULE-SEC-006 by separating environment-specific context values.

**detection_logic:** Not applicable — this is a remediation guidance document. Refer to RULE-SEC-006 for detection logic.

**impact:** Resolving RULE-SEC-006 prevents production credential leakage to non-production environments and establishes a secure environment promotion workflow.

**classification:** Remediation — MEDIUM severity
**remediation:**
1. Review all context variable default values in job context editors. Check DEV `.properties` files for any values that reference production systems. Look for: production hostnames, production database names, production service accounts, production API endpoints.
2. Create distinct context groups for each environment: `DEV_Config`, `TEST_Config`, `UAT_Config`, `PROD_Config`. Move production-specific values out of defaults and DEV properties. Use context group inheritance: DEV_Config gets base values, TEST_Config overrides what differs, UAT_Config further overrides, PROD_Config contains production values. Override only the values that change between environments in each child group.
3. Set up a CI/CD pipeline that injects the correct context values at deploy time. Use Talend Administration Center's Environment Management for controlled promotion. Never allow developers direct access to production context files or values. Production deployment should require an approved change ticket and automated approval.
4. Create a validation script that checks context values per environment and alerts on anomalies. Run the analyzer after environment separation to verify the finding is resolved. Conduct periodic audits of context values to ensure no production data leaks into non-production environments.

**source:** Talend Health Analyzer remediation documentation

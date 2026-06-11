# Security Best Practices

---

## BP-SEC-001: Context Variables

**rule_id:** BP-SEC-001
**category:** security
**title:** Context Variables
**description:**
Always use Talend context variables for any value that changes between environments. Create context variables for: database connection strings, credentials, file paths, API endpoints, timeout values, and feature flags. Reference context variables in component parameters using the `context.variable_name` syntax. Set default values in the context editor for development convenience, but never commit production values. Maintain separate `.properties` files per environment to supply context values at runtime. Use Talend's built-in context encryption for sensitive variables. Document each context variable with its purpose, expected format, and environment availability.

**detection_logic:** Not applicable — this is a best practice guidance document. Implementation is verified through code review and the findings defined in the Security Findings rules (SEC-001 through SEC-007).

**impact:**
Without context variables, environment-specific values are hardcoded into job designs. This makes environment promotion error-prone, increases the risk of credential exposure, and prevents centralized configuration management. Context variables are the foundation of secure, portable Talend job design.

**classification:** Best Practice
**remediation:**
Create context groups per environment. Define variables for all configurable values. Use `context.variable_name` syntax in component parameters. Maintain environment-specific `.properties` files in version control. Enable encryption for sensitive variables via the key icon in the context editor.

**source:** Talend security best practices, OWASP Secure Coding Guidelines

---

## BP-SEC-002: Context Groups

**rule_id:** BP-SEC-002
**category:** security
**title:** Context Groups
**description:**
Organize context variables into logical groups by concern (e.g., Database, FileSystem, API, Email). Create a base context group with shared variables and environment-specific child groups. Use context group inheritance to avoid duplicating variables across groups. Name context groups clearly: DEV_Config, TEST_Config, UAT_Config, PROD_Config. Limit each context group to 20-30 variables to maintain readability. Remove unused or deprecated context variables to reduce confusion.

**detection_logic:** Not applicable — this is a best practice guidance document.

**impact:**
Well-organized context groups improve maintainability and reduce the risk of misconfiguration during environment promotion. Inheritance reduces duplication and ensures that common variables have a single source of truth. Limiting group size prevents context overload and makes group configuration easier to audit.

**classification:** Best Practice
**remediation:**
Create logical context groups per environment. Define a base group for shared variables. Use inheritance for environment-specific overrides. Name groups with environment prefixes. Audit and remove unused variables regularly.

**source:** Talend security best practices

---

## BP-SEC-003: Environment Separation (DEV/TEST/UAT/PROD)

**rule_id:** BP-SEC-003
**category:** security
**title:** Environment Separation
**description:**
Create one context group per environment with environment-specific values. Never share production context values with developers. Use a secrets vault or Talend Administration Center for production credential injection. Implement a promotion workflow: code moves from DEV to TEST to UAT to PROD, with context values set at each stage. Use `.properties` files with environment-specific names. Store `.properties` files in version control with production values vaulted or set via the deployment pipeline. Tag context variables with their environment scope in the name. Automate context validation during CI/CD to ensure no environment is missing required variables.

**detection_logic:** Not applicable — this is a best practice guidance document.

**impact:**
Proper environment separation prevents production credentials from leaking into development or test environments. It ensures that each environment operates against its own resources, preventing accidental data corruption or unauthorized access. Environment-aware context variables make the promotion pipeline auditable and repeatable.

**classification:** Best Practice
**remediation:**
Create distinct context groups per environment. Store production values in a secrets vault. Implement a promotion workflow with CI/CD validation. Tag variables with environment scope. Never share production context files with developers.

**source:** Talend security best practices, SOC2 compliance guidelines

---

## BP-SEC-004: Hardcoded Credentials

**rule_id:** BP-SEC-004
**category:** security
**title:** Hardcoded Credentials
**description:**
Treat any hardcoded credential in a component parameter as a security incident. Common hardcoded patterns detected: `password=`, `passwd=`, `pwd=`, `secret=`, `token=`, `api_key=`, `apikey=` in parameter values. Never embed credentials in: tJDBCConnection properties, tRestClient headers, tFileProperties, or custom Java code (tJava/tJavaRow). Use Talend's context encryption for all credential-type context variables. Rotate any credential that has been hardcoded, even briefly, as it may have been captured in logs or version control. Implement a credential scanning step in your CI/CD pipeline as a preventive control.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Security Finding RULE-SEC-001.

**impact:**
Hardcoded credentials in Talend job metadata are visible to anyone with project or repository access. They cannot be centrally rotated, violating compliance standards (SOC2, PCI-DSS, SOX, HIPAA). A single compromised credential can lead to a full data breach.

**classification:** Best Practice
**remediation:**
Scan all jobs for hardcoded credentials. Replace with encrypted context variables. Rotate any exposed credentials immediately. Add credential scanning to the CI/CD pipeline. Train developers on secure credential management.

**source:** Talend security best practices, OWASP Top 10

---

## BP-SEC-005: Secret Management

**rule_id:** BP-SEC-005
**category:** security
**title:** Secret Management
**description:**
Integrate Talend with a dedicated secrets management platform: HashiCorp Vault, Azure Key Vault, AWS Secrets Manager, or CyberArk. For cloud deployments, use cloud-native secret services (e.g., AWS Systems Manager Parameter Store) with IAM-based access control. In on-premises environments, use Talend's encrypted context variables combined with filesystem-level access controls. Never store secrets in: job metadata, XML files, CSV lookup files, or shared network drives accessible to non-production users. Implement secret rotation policies: rotate database credentials every 90 days, API keys every 180 days, certificates before expiry. Audit secret usage regularly. Use distinct service accounts per application or integration.

**detection_logic:** Not applicable — this is a best practice guidance document.

**impact:**
Without a dedicated secrets management platform, credentials are stored in plaintext or weakly protected formats. Secrets rotation becomes a manual, error-prone process. Audit trails for credential access are non-existent, making compliance certification difficult.

**classification:** Best Practice
**remediation:**
Integrate with a secrets management platform. Use IAM-based authentication for cloud services. Implement regular rotation policies. Audit secret usage. Use distinct service accounts per integration.

**source:** Talend security best practices, NIST SP 800-53

---

## BP-SEC-006: Database Connection Security

**rule_id:** BP-SEC-006
**category:** security
**title:** Database Connection Security
**description:**
Use tMetadataConnection for governed, centralized database connection management. Encrypt database connections using TLS/SSL where the target database supports it. Set connection parameters: `useSSL=true`, `requireSSL=true` for JDBC connections to enforce encryption. Avoid using the `allowPublicKeyRetrieval=true` JDBC flag in production. Configure connection pool limits: set maxActive, maxIdle, and maxWait appropriately. Validate connection SQL on checkout to detect stale connections early. Use read-only credentials for jobs that only query data. For cloud databases, use IAM-based authentication instead of passwords where available. Store JDBC connection strings in context variables. Parameterize schema names, table names, and query parameters through context variables to prevent SQL injection through metadata.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Security Findings RULE-SEC-002 and RULE-SEC-006.

**impact:**
Unencrypted database connections expose data in transit. Inline JDBC URLs with credentials bypass governed metadata and security audits. Without connection governance, changing a database endpoint requires updating every job individually.

**classification:** Best Practice
**remediation:**
Use tMetadataConnection for all database connections. Enable TLS/SSL with database-specific parameters. Use context variables for all connection properties. Implement IAM-based authentication for cloud databases. Configure connection pool limits.

**source:** Talend security best practices, database vendor security guides

---

## BP-SEC-007: API Security

**rule_id:** BP-SEC-007
**category:** security
**title:** API Security
**description:**
Use Talend's tRestClient or tRestRequest components with proper authentication configuration. Store API keys, tokens, and client secrets in encrypted context variables — never in component parameters. Configure OAuth2 client credentials flow for machine-to-machine API communication where supported. Set appropriate timeout values: connect timeout, read timeout, and write timeout. Implement retry logic with exponential backoff for transient API failures. Validate TLS certificates in production — disable `trustAllCertificates` except in development. Use mutual TLS (mTLS) for high-security API integrations. Avoid passing sensitive data in URL query parameters; use request headers or body instead. Log API call metadata (endpoint, status code, duration) but never log request or response payloads containing sensitive data. Rotate API keys and regenerate tokens on a defined schedule.

**detection_logic:** Not applicable — this is a best practice guidance document. Active detection is performed by Security Finding RULE-SEC-005.

**impact:**
Exposed API keys and tokens allow unauthorized access to third-party services and cloud resources. Unlike database credentials, API keys often have broad permissions and may not trigger standard security alerts when misused. Insecure API configurations can lead to data exfiltration and service abuse.

**classification:** Best Practice
**remediation:**
Store all API credentials in encrypted context variables. Implement OAuth2 client credentials flow. Set appropriate timeouts and retry logic. Validate TLS certificates in production. Rotate keys on a defined schedule. Log metadata, never payloads.

**source:** Talend security best practices, OWASP API Security Top 10

---

## BP-SEC-008: Credential Rotation and Incident Response

**rule_id:** BP-SEC-008
**category:** security
**title:** Credential Rotation and Incident Response
**description:**
Establish a credential rotation policy: database credentials every 90 days, API keys every 180 days, certificates before expiry. Automate rotation using secrets management platform APIs. When a credential is found hardcoded, rotate it immediately — it may have been captured in version control history, backup exports, error logs, or developer workstations. Maintain an inventory of all credentials used by Talend jobs with their rotation schedule. Implement monitoring for credential expiry and alert before expiration. Document incident response procedures for credential compromise: revoke immediately, rotate all affected credentials, audit access logs, notify security team.

**detection_logic:** Not applicable — this is a best practice guidance document.

**impact:**
Without a rotation policy, compromised credentials remain valid indefinitely. Stale credentials increase the blast radius of a security breach. Manual rotation processes are error-prone and often skipped, leaving systems vulnerable.

**classification:** Best Practice
**remediation:**
Define a rotation schedule per credential type. Automate rotation via secrets management APIs. Rotate immediately on any hardcoded exposure. Monitor credential expiry. Document incident response procedures.

**source:** Talend security best practices, NIST SP 800-63B

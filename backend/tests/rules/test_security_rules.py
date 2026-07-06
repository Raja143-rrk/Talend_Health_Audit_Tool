from backend.rule_engine.rules.security import SECURITY_RULES


def _rule_by_id(rule_id: str):
    return next(r for r in SECURITY_RULES if r.id == rule_id)


class TestSec001HardcodedCredential:
    def test_detects_password_param(self, component_factory):
        rule = _rule_by_id("RULE-SEC-001")
        comp = component_factory(params={"PASSWORD": "s3cret"})
        assert rule.predicate(comp, {})

    def test_detects_secret_param(self, component_factory):
        rule = _rule_by_id("RULE-SEC-001")
        comp = component_factory(params={"SECRET_KEY": "mysecret"})
        assert rule.predicate(comp, {})

    def test_detects_token_param(self, component_factory):
        rule = _rule_by_id("RULE-SEC-001")
        comp = component_factory(params={"TOKEN": "abc123"})
        assert rule.predicate(comp, {})

    def test_detects_api_key_param(self, component_factory):
        rule = _rule_by_id("RULE-SEC-001")
        comp = component_factory(params={"API_KEY": "key-12345"})
        assert rule.predicate(comp, {})

    def test_ignores_empty_value(self, component_factory):
        rule = _rule_by_id("RULE-SEC-001")
        comp = component_factory(params={"PASSWORD": ""})
        assert not rule.predicate(comp, {})

    def test_ignores_safe_params(self, component_factory):
        rule = _rule_by_id("RULE-SEC-001")
        comp = component_factory(params={"HOST": "localhost", "PORT": "5432"})
        assert not rule.predicate(comp, {})


class TestSec002InlineJdbcUrl:
    def test_detects_jdbc_url(self, component_factory):
        rule = _rule_by_id("RULE-SEC-002")
        comp = component_factory(params={"URL": "jdbc:mysql://localhost:3306/db"})
        assert rule.predicate(comp, {})

    def test_detects_jdbc_url_uppercase(self, component_factory):
        rule = _rule_by_id("RULE-SEC-002")
        comp = component_factory(params={"URL": "JDBC:postgresql://prod:5432/db"})
        assert rule.predicate(comp, {})

    def test_ignores_non_jdbc(self, component_factory):
        rule = _rule_by_id("RULE-SEC-002")
        comp = component_factory(params={"URL": "http://example.com"})
        assert not rule.predicate(comp, {})


class TestSec003MissingContextVars:
    def test_detects_missing_contexts(self, empty_inventory):
        rule = _rule_by_id("RULE-SEC-003")
        assert rule.predicate(empty_inventory, {})

    def test_passes_with_contexts(self, empty_inventory):
        rule = _rule_by_id("RULE-SEC-003")
        empty_inventory["contexts"] = ["Default", "DEV"]
        assert not rule.predicate(empty_inventory, {})


class TestSec004ExposedApiKey:
    def test_detects_api_key(self, component_factory):
        rule = _rule_by_id("RULE-SEC-004")
        comp = component_factory(params={"API_KEY": "sk-abc123def456"})
        assert rule.predicate(comp, {})

    def test_detects_bearer_token(self, component_factory):
        rule = _rule_by_id("RULE-SEC-004")
        comp = component_factory(params={"BEARER": "eyJhbGciOiJIUzI1NiJ9"})
        assert rule.predicate(comp, {})

    def test_detects_oauth_client_secret(self, component_factory):
        rule = _rule_by_id("RULE-SEC-004")
        comp = component_factory(params={"CLIENT_SECRET": "mysecret123"})
        assert rule.predicate(comp, {})

    def test_detects_auth_token(self, component_factory):
        rule = _rule_by_id("RULE-SEC-004")
        comp = component_factory(params={"AUTH_TOKEN": "tok-xyz"})
        assert rule.predicate(comp, {})

    def test_ignores_safe_params(self, component_factory):
        rule = _rule_by_id("RULE-SEC-004")
        comp = component_factory(params={"USERNAME": "admin"})
        assert not rule.predicate(comp, {})


class TestSec005InsecureDbConfig:
    def test_detects_ssl_disabled(self, component_factory):
        rule = _rule_by_id("RULE-SEC-005")
        comp = component_factory(params={"useSSL": "false"})
        assert rule.predicate(comp, {})

    def test_detects_sslmode_disable(self, component_factory):
        rule = _rule_by_id("RULE-SEC-005")
        comp = component_factory(params={"sslmode": "disable"})
        assert rule.predicate(comp, {})

    def test_detects_encrypt_disabled(self, component_factory):
        rule = _rule_by_id("RULE-SEC-005")
        comp = component_factory(params={"encrypt": "false"})
        assert rule.predicate(comp, {})

    def test_passes_with_ssl_enabled(self, component_factory):
        rule = _rule_by_id("RULE-SEC-005")
        comp = component_factory(params={"useSSL": "true"})
        assert not rule.predicate(comp, {})

    def test_ignores_unrelated_params(self, component_factory):
        rule = _rule_by_id("RULE-SEC-005")
        comp = component_factory(params={"HOST": "localhost"})
        assert not rule.predicate(comp, {})


class TestSec006CrossEnvContextExposure:
    def test_detects_prod_value_in_dev_context(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-006")
        inv = inventory_factory(context_groups=[
            {
                "name": "DEV",
                "parameters": [
                    {"name": "db_host", "value": "prod.example.com"}
                ],
            }
        ])
        assert rule.predicate(inv, {})

    def test_detects_prod_in_value(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-006")
        inv = inventory_factory(context_groups=[
            {
                "name": "Test",
                "parameters": [
                    {"name": "password", "value": "production_password"}
                ],
            }
        ])
        assert rule.predicate(inv, {})

    def test_passes_without_prod_values(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-006")
        inv = inventory_factory(context_groups=[
            {
                "name": "DEV",
                "parameters": [
                    {"name": "db_host", "value": "dev.localhost"}
                ],
            }
        ])
        assert not rule.predicate(inv, {})

    def test_passes_no_context_groups(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-006")
        assert not rule.predicate(inventory_factory(), {})

    def test_passes_prod_group_with_prod_values(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-006")
        inv = inventory_factory(context_groups=[
            {
                "name": "PROD",
                "parameters": [
                    {"name": "db_host", "value": "prod.example.com"}
                ],
            }
        ])
        assert not rule.predicate(inv, {})


class TestSec007UnencryptedSensitiveContextVars:
    def test_detects_unencrypted_password(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-007")
        inv = inventory_factory(context_groups=[
            {
                "name": "Default",
                "parameters": [
                    {"name": "db_password", "value": "s3cret", "encrypted": False},
                ],
            }
        ])
        assert rule.predicate(inv, {})

    def test_passes_with_encrypted_password(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-007")
        inv = inventory_factory(context_groups=[
            {
                "name": "Default",
                "parameters": [
                    {"name": "db_password", "value": "encrypted_value", "encrypted": True},
                ],
            }
        ])
        assert not rule.predicate(inv, {})

    def test_passes_no_sensitive_params(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-007")
        inv = inventory_factory(context_groups=[
            {
                "name": "Default",
                "parameters": [
                    {"name": "db_host", "value": "localhost", "encrypted": False},
                ],
            }
        ])
        assert not rule.predicate(inv, {})


class TestSec009UnsecuredContextLoading:
    def test_detects_external_file_with_sensitive_param(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-009")
        inv = inventory_factory(context_groups=[
            {
                "name": "ExternalConfig",
                "external_file_path": "config/db.properties",
                "parameters": [
                    {"name": "db_password", "value": "dummy", "encrypted": False},
                ],
            }
        ])
        assert rule.predicate(inv, {})

    def test_passes_builtin_context_no_external_file(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-009")
        inv = inventory_factory(context_groups=[
            {
                "name": "Default",
                "parameters": [
                    {"name": "db_password", "value": "s3cret", "encrypted": False},
                ],
            }
        ])
        assert not rule.predicate(inv, {})

    def test_passes_external_file_no_sensitive_params(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-009")
        inv = inventory_factory(context_groups=[
            {
                "name": "ExternalConfig",
                "external_file_path": "config/app.properties",
                "parameters": [
                    {"name": "db_host", "value": "localhost"},
                ],
            }
        ])
        assert not rule.predicate(inv, {})

    def test_passes_no_context_groups(self, inventory_factory):
        rule = _rule_by_id("RULE-SEC-009")
        assert not rule.predicate(inventory_factory(), {})

from backend.rule_engine.rules.architecture import ARCHITECTURE_RULES


def _rule_by_id(rule_id: str):
    return next(r for r in ARCHITECTURE_RULES if r.id == rule_id)


class TestArch001NoContexts:
    def test_detects_missing_contexts(self, empty_inventory):
        rule = _rule_by_id("RULE-ARCH-001")
        assert rule.predicate(empty_inventory, {})

    def test_passes_with_contexts(self, empty_inventory):
        rule = _rule_by_id("RULE-ARCH-001")
        empty_inventory["contexts"] = ["Default"]
        assert not rule.predicate(empty_inventory, {})


class TestArch002HighSystemSpread:
    def test_detects_high_spread(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-002")
        inv = inventory_factory(overrides={
            "source_systems": ["MySQL", "Oracle", "PostgreSQL", "MongoDB", "Redis"],
            "target_systems": ["Salesforce", "S3", "Snowflake", "Redshift", "Kafka"],
        })
        assert rule.predicate(inv, {})

    def test_passes_low_spread(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-002")
        inv = inventory_factory(overrides={
            "source_systems": ["MySQL", "Oracle"],
            "target_systems": ["Salesforce"],
        })
        assert not rule.predicate(inv, {})


class TestArch003MissingErrorHandling:
    def test_detects_output_without_trycatch(self, job_factory):
        rule = _rule_by_id("RULE-ARCH-003")
        comps = [
            {"name": "out", "component_name": "tDBOutput", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_no_output_components(self, job_factory):
        rule = _rule_by_id("RULE-ARCH-003")
        comps = [
            {"name": "map", "component_name": "tMap", "disabled": False, "parameters": {}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})


class TestArch004NoCicd:
    def test_detects_no_cicd_files(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-004")
        assert rule.predicate(inventory_factory(), {})

    def test_passes_with_github_actions(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-004")
        inv = inventory_factory(overrides={
            "item_files": ["/repo/.github/workflows/ci.yml"]
        })
        assert not rule.predicate(inv, {})

    def test_passes_with_jenkinsfile(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-004")
        inv = inventory_factory(overrides={
            "item_files": ["/repo/Jenkinsfile"]
        })
        assert not rule.predicate(inv, {})


class TestArch005InconsistentLogging:
    def test_detects_no_logging(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-005")
        jobs = [
            {"name": "j1", "components": [
                {"name": "out", "component_name": "tDBOutput", "disabled": False, "parameters": {}}
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert rule.predicate(inv, {})

    def test_passes_with_logging(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-005")
        jobs = [
            {"name": "j1", "components": [
                {"name": "log", "component_name": "tLogRow", "disabled": False, "parameters": {}}
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert not rule.predicate(inv, {})

    def test_passes_partial_logging(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-005")
        jobs = [
            {"name": "j1", "components": [
                {"name": "log", "component_name": "tLogRow", "disabled": False, "parameters": {}}
            ]},
            {"name": "j2", "components": [
                {"name": "out", "component_name": "tDBOutput", "disabled": False, "parameters": {}}
            ]},
        ]
        assert rule.predicate(inventory_factory(jobs=jobs), {})


class TestArch006MissingGovernedMetadata:
    def test_detects_inline_without_metadata(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-006")
        jobs = [
            {"name": "j1", "components": [
                {"name": "conn", "component_name": "tJDBCConnection", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert rule.predicate(inv, {})

    def test_passes_with_metadata_connection(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-006")
        jobs = [
            {"name": "j1", "components": [
                {"name": "conn", "component_name": "tJDBCConnection", "disabled": False, "parameters": {}},
                {"name": "meta", "component_name": "tMetadataConnection", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert not rule.predicate(inv, {})

    def test_passes_no_inline_connections(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-006")
        jobs = [
            {"name": "j1", "components": [
                {"name": "map", "component_name": "tMap", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert not rule.predicate(inv, {})


class TestArch007MissingDecomposition:
    def test_detects_large_job_without_trunjob(self, job_factory):
        rule = _rule_by_id("RULE-ARCH-007")
        comps = [{"name": f"c{i}", "component_name": "tMap", "disabled": False, "parameters": {}}
                 for i in range(55)]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_with_trunjob(self, job_factory):
        rule = _rule_by_id("RULE-ARCH-007")
        comps = [{"name": f"c{i}", "component_name": "tMap", "disabled": False, "parameters": {}}
                 for i in range(55)]
        comps.append({"name": "run", "component_name": "tRunJob", "disabled": False, "parameters": {}})
        assert not rule.predicate(job_factory(components=comps), {})


class TestArch008MissingJoblet:
    def test_detects_no_joblets(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-008")
        assert rule.predicate(inventory_factory(), {})

    def test_passes_with_joblet_file(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-008")
        inv = inventory_factory(overrides={
            "item_files": ["/project/myJoblet.joblet"]
        })
        assert not rule.predicate(inv, {})

    def test_passes_with_tjoblet_component(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-008")
        jobs = [
            {"name": "j1", "components": [
                {"name": "jlet", "component_name": "tJoblet", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert not rule.predicate(inv, {})


class TestArch009MissingErrorFramework:
    def test_detects_no_ttrycatch(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-009")
        jobs = [
            {"name": "j1", "components": [
                {"name": "out", "component_name": "tDBOutput", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert rule.predicate(inv, {})

    def test_passes_with_ttrycatch(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-009")
        jobs = [
            {"name": "j1", "components": [
                {"name": "catch", "component_name": "tTryCatch", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert not rule.predicate(inv, {})


class TestArch010MissingMonitoring:
    def test_detects_no_monitoring(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-010")
        inv = inventory_factory()
        assert rule.predicate(inv, {})

    def test_passes_with_logrow(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-010")
        jobs = [
            {"name": "j1", "components": [
                {"name": "log", "component_name": "tLogRow", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert not rule.predicate(inv, {})

    def test_passes_with_statscatcher(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-010")
        jobs = [
            {"name": "j1", "components": [
                {"name": "stat", "component_name": "tStatsCatcher", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert not rule.predicate(inv, {})


class TestArch011MissingExceptionFramework:
    def test_detects_no_error_handling(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-011")
        inv = inventory_factory()
        assert rule.predicate(inv, {})

    def test_passes_with_ttrycatch(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-011")
        jobs = [
            {"name": "j1", "components": [
                {"name": "catch", "component_name": "tTryCatch", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert not rule.predicate(inv, {})

    def test_passes_with_terrorhandler(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-011")
        jobs = [
            {"name": "j1", "components": [
                {"name": "err", "component_name": "tErrorHandler", "disabled": False, "parameters": {}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs)
        assert not rule.predicate(inv, {})


class TestArch012UntrackedContextVars:
    def test_detects_undefined_context_ref(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-012")
        jobs = [
            {"name": "j1", "components": [
                {"name": "comp", "component_name": "tDBInput", "disabled": False,
                 "parameters": {"TABLE": "context.undefined_var"}},
            ]},
        ]
        assert rule.predicate(inventory_factory(jobs=jobs), {})

    def test_passes_all_refs_defined(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-012")
        jobs = [
            {"name": "j1", "components": [
                {"name": "comp", "component_name": "tDBInput", "disabled": False,
                 "parameters": {"TABLE": "context.my_table"}},
            ]},
        ]
        inv = inventory_factory(jobs=jobs, context_groups=[
            {
                "name": "Default",
                "parameters": [{"name": "my_table", "value": "users"}],
            }
        ])
        assert not rule.predicate(inv, {})

    def test_passes_no_context_refs(self, inventory_factory):
        rule = _rule_by_id("RULE-ARCH-012")
        jobs = [
            {"name": "j1", "components": [
                {"name": "comp", "component_name": "tDBInput", "disabled": False,
                 "parameters": {"TABLE": "users"}},
            ]},
        ]
        assert not rule.predicate(inventory_factory(jobs=jobs), {})

from backend.rule_engine.rules.components import COMPONENT_RULES


def _rule_by_id(rule_id: str):
    return next(r for r in COMPONENT_RULES if r.id == rule_id)


class TestComp001DisabledComponent:
    def test_detects_disabled(self, component_factory):
        rule = _rule_by_id("RULE-COMP-001")
        comp = component_factory(overrides={"disabled": True})
        assert rule.predicate(comp, {})

    def test_passes_enabled(self, component_factory):
        rule = _rule_by_id("RULE-COMP-001")
        comp = component_factory(overrides={"disabled": False})
        assert not rule.predicate(comp, {})


class TestComp002LargeJobCount:
    def test_detects_large_job(self, job_factory):
        rule = _rule_by_id("RULE-COMP-002")
        comps = [{"name": f"c{i}", "component_name": "tMap", "disabled": False, "parameters": {}}
                 for i in range(55)]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_small_job(self, job_factory):
        rule = _rule_by_id("RULE-COMP-002")
        comps = [{"name": f"c{i}", "component_name": "tMap", "disabled": False, "parameters": {}}
                 for i in range(10)]
        assert not rule.predicate(job_factory(components=comps), {})


class TestComp003NamingConvention:
    def test_detects_default_name(self, job_factory):
        rule = _rule_by_id("RULE-COMP-003")
        comps = [{"name": "tMap_1", "component_name": "tMap", "disabled": False, "parameters": {}}]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_custom_name(self, job_factory):
        rule = _rule_by_id("RULE-COMP-003")
        comps = [{"name": "transformUsers", "component_name": "tMap", "disabled": False, "parameters": {}}]
        assert not rule.predicate(job_factory(components=comps), {})


class TestComp004MissingDocumentation:
    def test_detects_undocumented_complex(self, component_factory):
        rule = _rule_by_id("RULE-COMP-004")
        comp = component_factory(overrides={"component_name": "tMap"})
        assert rule.predicate(comp, {})

    def test_passes_with_notes(self, component_factory):
        rule = _rule_by_id("RULE-COMP-004")
        comp = component_factory(overrides={"component_name": "tMap"},
                                  params={"NOTES": "This mapping joins users to orders"})
        assert not rule.predicate(comp, {})

    def test_ignores_simple_components(self, component_factory):
        rule = _rule_by_id("RULE-COMP-004")
        comp = component_factory(overrides={"component_name": "tDBInput"})
        assert not rule.predicate(comp, {})


class TestComp005DuplicateConfig:
    def test_detects_duplicate_configs(self, job_factory):
        rule = _rule_by_id("RULE-COMP-005")
        comps = [
            {"name": "tMap_1", "component_name": "tMap", "disabled": False,
             "parameters": {"LOOKUP": "users", "JOIN": "INNER"}},
            {"name": "tMap_2", "component_name": "tMap", "disabled": False,
             "parameters": {"LOOKUP": "users", "JOIN": "INNER"}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_unique_configs(self, job_factory):
        rule = _rule_by_id("RULE-COMP-005")
        comps = [
            {"name": "tMap_1", "component_name": "tMap", "disabled": False,
             "parameters": {"LOOKUP": "users"}},
            {"name": "tMap_2", "component_name": "tMap", "disabled": False,
             "parameters": {"LOOKUP": "orders"}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})


class TestComp006MissingReusableExtraction:
    def test_detects_repeated_pattern(self, inventory_factory):
        rule = _rule_by_id("RULE-COMP-006")
        jobs = []
        for i in range(4):
            jobs.append({
                "name": f"job{i}",
                "components": [
                    {"name": f"in{i}", "component_name": "tFileInputDelimited", "disabled": False, "parameters": {}},
                    {"name": f"map{i}", "component_name": "tMap", "disabled": False, "parameters": {}},
                    {"name": f"out{i}", "component_name": "tFileOutputDelimited", "disabled": False, "parameters": {}},
                ],
            })
        assert rule.predicate(inventory_factory(jobs=jobs), {})

    def test_passes_unique_patterns(self, inventory_factory):
        rule = _rule_by_id("RULE-COMP-006")
        jobs = [
            {"name": "job1", "components": [
                {"name": "in1", "component_name": "tFileInputDelimited", "disabled": False, "parameters": {}},
                {"name": "out1", "component_name": "tFileOutputDelimited", "disabled": False, "parameters": {}},
            ]},
            {"name": "job2", "components": [
                {"name": "in2", "component_name": "tDBInput", "disabled": False, "parameters": {}},
                {"name": "out2", "component_name": "tDBOutput", "disabled": False, "parameters": {}},
            ]},
        ]
        assert not rule.predicate(inventory_factory(jobs=jobs), {})


class TestComp007MissingContextStandardization:
    def test_detects_hardcoded_localhost(self, job_factory):
        rule = _rule_by_id("RULE-COMP-007")
        comps = [
            {"name": "conn", "component_name": "tJDBCConnection", "disabled": False,
             "parameters": {"HOST": "localhost"}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_detects_hardcoded_ip(self, job_factory):
        rule = _rule_by_id("RULE-COMP-007")
        comps = [
            {"name": "conn", "component_name": "tJDBCConnection", "disabled": False,
             "parameters": {"HOST": "127.0.0.1"}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_context_variable(self, job_factory):
        rule = _rule_by_id("RULE-COMP-007")
        comps = [
            {"name": "conn", "component_name": "tJDBCConnection", "disabled": False,
             "parameters": {"HOST": "context.db_host"}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})

    def test_passes_safe_values(self, job_factory):
        rule = _rule_by_id("RULE-COMP-007")
        comps = [
            {"name": "conn", "component_name": "tJDBCConnection", "disabled": False,
             "parameters": {"PORT": "8080"}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})


class TestComp008UnusedComponents:
    def test_fallback_detects_unused_named_component(self, job_factory):
        rule = _rule_by_id("RULE-COMP-008")
        comps = [
            {"name": "unused_tMap", "component_name": "tMap", "disabled": False, "parameters": {}},
            {"name": "active", "component_name": "tDBOutput", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_fallback_detects_disabled_copy(self, job_factory):
        rule = _rule_by_id("RULE-COMP-008")
        comps = [
            {"name": "disabled_copy_1", "component_name": "tMap", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_fallback_detects_test_named_component(self, job_factory):
        rule = _rule_by_id("RULE-COMP-008")
        comps = [
            {"name": "test_connection", "component_name": "tJDBCConnection", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_fallback_detects_debug_named_component(self, job_factory):
        rule = _rule_by_id("RULE-COMP-008")
        comps = [
            {"name": "debug_log", "component_name": "tLogRow", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_fallback_detects_temp_named_component(self, job_factory):
        rule = _rule_by_id("RULE-COMP-008")
        comps = [
            {"name": "temp_output", "component_name": "tFileOutputDelimited", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_fallback_detects_backup_named_component(self, job_factory):
        rule = _rule_by_id("RULE-COMP-008")
        comps = [
            {"name": "backup_transform", "component_name": "tMap", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_fallback_passes_clean_job(self, job_factory):
        rule = _rule_by_id("RULE-COMP-008")
        comps = [
            {"name": "loadUsers", "component_name": "tMap", "disabled": False, "parameters": {}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})

    def test_detects_orphan_via_topology(self, job_factory):
        rule = _rule_by_id("RULE-COMP-008")
        comps = [
            {"name": "input", "component_name": "tFileInputDelimited", "disabled": False,
             "id": "c1", "parameters": {}},
            {"name": "map", "component_name": "tMap", "disabled": False,
             "id": "c2", "parameters": {}},
            {"name": "orphan", "component_name": "tLogRow", "disabled": False,
             "id": "c99", "parameters": {}},
        ]
        conns = [
            {"source_id": "c1", "target_id": "c2", "connection_type": "FLOW"},
        ]
        job = job_factory(components=comps, overrides={"connections": conns})
        assert rule.predicate(job, {})

    def test_passes_connected_job(self, job_factory):
        rule = _rule_by_id("RULE-COMP-008")
        comps = [
            {"name": "input", "component_name": "tFileInputDelimited", "disabled": False,
             "id": "c1", "parameters": {}},
            {"name": "map", "component_name": "tMap", "disabled": False,
             "id": "c2", "parameters": {}},
            {"name": "output", "component_name": "tFileOutputDelimited", "disabled": False,
             "id": "c3", "parameters": {}},
        ]
        conns = [
            {"source_id": "c1", "target_id": "c2", "connection_type": "FLOW"},
            {"source_id": "c2", "target_id": "c3", "connection_type": "FLOW"},
        ]
        job = job_factory(components=comps, overrides={"connections": conns})
        assert not rule.predicate(job, {})


class TestComp009CrossJobDuplicate:
    def test_detects_cross_job_duplicates(self, inventory_factory):
        rule = _rule_by_id("RULE-COMP-009")
        jobs = [
            {"name": "j1", "components": [
                {"name": "map1", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP": "countries", "JOIN_TYPE": "INNER"}},
            ]},
            {"name": "j2", "components": [
                {"name": "map2", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP": "countries", "JOIN_TYPE": "INNER"}},
            ]},
            {"name": "j3", "components": [
                {"name": "map3", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP": "countries", "JOIN_TYPE": "INNER"}},
            ]},
        ]
        assert rule.predicate(inventory_factory(jobs=jobs), {})

    def test_passes_unique_configs_across_jobs(self, inventory_factory):
        rule = _rule_by_id("RULE-COMP-009")
        jobs = [
            {"name": "j1", "components": [
                {"name": "map1", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP": "customers", "JOIN_TYPE": "INNER"}},
            ]},
            {"name": "j2", "components": [
                {"name": "map2", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP": "orders", "JOIN_TYPE": "LEFT"}},
            ]},
        ]
        assert not rule.predicate(inventory_factory(jobs=jobs), {})

    def test_passes_threshold_not_reached(self, inventory_factory):
        rule = _rule_by_id("RULE-COMP-009")
        jobs = [
            {"name": "j1", "components": [
                {"name": "map1", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP": "countries", "JOIN_TYPE": "INNER"}},
            ]},
            {"name": "j2", "components": [
                {"name": "map2", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP": "countries", "JOIN_TYPE": "INNER"}},
            ]},
        ]
        assert not rule.predicate(inventory_factory(jobs=jobs), {})


class TestComp010OverlyComplexTmap:
    def test_detects_many_lookups(self, component_factory):
        rule = _rule_by_id("RULE-COMP-010")
        params = {f"LOOKUP_{i}_TABLE": f"table{i}" for i in range(5)}
        comp = component_factory(overrides={"component_name": "tMap"}, params=params)
        assert rule.predicate(comp, {})

    def test_detects_many_expressions(self, component_factory):
        rule = _rule_by_id("RULE-COMP-010")
        comp = component_factory(overrides={"component_name": "tMap"},
                                 params={"NB_LINE": "55"})
        assert rule.predicate(comp, {})

    def test_detects_many_output_expressions(self, component_factory):
        rule = _rule_by_id("RULE-COMP-010")
        params = {f"OUTPUT_0_EXPRESSION_{i}": f"row1.col{i}" for i in range(50)}
        comp = component_factory(overrides={"component_name": "tMap"}, params=params)
        assert rule.predicate(comp, {})

    def test_detects_summed_nb_lines(self, component_factory):
        rule = _rule_by_id("RULE-COMP-010")
        comp = component_factory(overrides={"component_name": "tMap"},
                                 params={"NB_LINE_OUTPUT_0": "30", "NB_LINE_OUTPUT_1": "25"})
        assert rule.predicate(comp, {})

    def test_passes_simple_tmap(self, component_factory):
        rule = _rule_by_id("RULE-COMP-010")
        comp = component_factory(overrides={"component_name": "tMap"},
                                 params={"LOOKUP_0_TABLE": "users", "NB_LINE": "10"})
        assert not rule.predicate(comp, {})

    def test_ignores_non_tmap(self, component_factory):
        rule = _rule_by_id("RULE-COMP-010")
        comp = component_factory(overrides={"component_name": "tDBInput"},
                                 params={"NB_LINE": "200"})
        assert not rule.predicate(comp, {})

    def test_ignores_non_tmap_components(self, inventory_factory):
        rule = _rule_by_id("RULE-COMP-009")
        jobs = [
            {"name": "j1", "components": [
                {"name": "in1", "component_name": "tDBInput", "disabled": False,
                 "parameters": {"TABLE": "users"}},
            ]},
            {"name": "j2", "components": [
                {"name": "in2", "component_name": "tDBInput", "disabled": False,
                 "parameters": {"TABLE": "users"}},
            ]},
            {"name": "j3", "components": [
                {"name": "in3", "component_name": "tDBInput", "disabled": False,
                 "parameters": {"TABLE": "users"}},
            ]},
        ]
        assert not rule.predicate(inventory_factory(jobs=jobs), {})

    def test_detects_lookup_only_duplicates(self, inventory_factory):
        rule = _rule_by_id("RULE-COMP-009")
        jobs = [
            {"name": "j1", "components": [
                {"name": "map1", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP_TABLE": "countries", "JOIN_TYPE": "INNER"}},
            ]},
            {"name": "j2", "components": [
                {"name": "map2", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP_TABLE": "countries", "JOIN_TYPE": "LEFT"}},
            ]},
            {"name": "j3", "components": [
                {"name": "map3", "component_name": "tMap", "disabled": False,
                 "parameters": {"LOOKUP_TABLE": "countries", "JOIN_TYPE": "RIGHT"}},
            ]},
        ]
        assert rule.predicate(inventory_factory(jobs=jobs), {})

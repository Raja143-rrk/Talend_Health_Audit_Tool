from backend.rule_engine.rules.performance import PERFORMANCE_RULES


def _rule_by_id(rule_id: str):
    return next(r for r in PERFORMANCE_RULES if r.id == rule_id)


class TestPerf001ExcessiveTJava:
    def test_detects_three_or_more_tjava(self, job_factory):
        rule = _rule_by_id("RULE-PERF-001")
        comps = [
            {"name": "tJava_1", "component_name": "tJava", "disabled": False, "parameters": {}},
            {"name": "tJava_2", "component_name": "tJava", "disabled": False, "parameters": {}},
            {"name": "tJava_3", "component_name": "tJava", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_with_less_than_three(self, job_factory):
        rule = _rule_by_id("RULE-PERF-001")
        comps = [
            {"name": "tJava_1", "component_name": "tJava", "disabled": False, "parameters": {}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})

    def test_ignores_disabled_components(self, job_factory):
        rule = _rule_by_id("RULE-PERF-001")
        comps = [
            {"name": "tJava_1", "component_name": "tJava", "disabled": True, "parameters": {}},
            {"name": "tJava_2", "component_name": "tJava", "disabled": True, "parameters": {}},
            {"name": "tJava_3", "component_name": "tJava", "disabled": True, "parameters": {}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})


class TestPerf002HeavyTMap:
    def test_detects_three_or_more_tmaps(self, job_factory):
        rule = _rule_by_id("RULE-PERF-002")
        comps = [
            {"name": "tMap_1", "component_name": "tMap", "disabled": False, "parameters": {}},
            {"name": "tMap_2", "component_name": "tMap", "disabled": False, "parameters": {}},
            {"name": "tMap_3", "component_name": "tMap", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_with_one_tmap(self, job_factory):
        rule = _rule_by_id("RULE-PERF-002")
        comps = [
            {"name": "tMap_1", "component_name": "tMap", "disabled": False, "parameters": {}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})


class TestPerf003SmallCommit:
    def test_detects_small_commit(self, component_factory):
        rule = _rule_by_id("RULE-PERF-003")
        comp = component_factory(overrides={"component_name": "tDBOutput"}, params={"COMMIT_EVERY": "10"})
        assert rule.predicate(comp, {})

    def test_passes_large_commit(self, component_factory):
        rule = _rule_by_id("RULE-PERF-003")
        comp = component_factory(overrides={"component_name": "tDBOutput"}, params={"COMMIT_EVERY": "1000"})
        assert not rule.predicate(comp, {})

    def test_ignores_non_output_components(self, component_factory):
        rule = _rule_by_id("RULE-PERF-003")
        comp = component_factory(overrides={"component_name": "tMap"}, params={"COMMIT_EVERY": "10"})
        assert not rule.predicate(comp, {})


class TestPerf004MissingSourcePushdown:
    def test_detects_table_mode_db_input(self, job_factory):
        rule = _rule_by_id("RULE-PERF-004")
        comps = [
            {"name": "input", "component_name": "tDBInput", "disabled": False,
             "parameters": {"USE_QUERY": "false", "TABLE": "users"}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_with_custom_sql(self, job_factory):
        rule = _rule_by_id("RULE-PERF-004")
        comps = [
            {"name": "input", "component_name": "tDBInput", "disabled": False,
             "parameters": {"USE_QUERY": "true", "SQL_QUERY": "SELECT * FROM users WHERE active=1"}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})

    def test_ignores_non_db_input(self, job_factory):
        rule = _rule_by_id("RULE-PERF-004")
        comps = [
            {"name": "input", "component_name": "tFileInputDelimited", "disabled": False,
             "parameters": {"FILE_NAME": "data.csv"}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})


class TestPerf005InefficientLookup:
    def test_detects_all_rows_lookup(self, component_factory):
        rule = _rule_by_id("RULE-PERF-005")
        comp = component_factory(overrides={"component_name": "tMap"},
                                  params={"LOOKUP_MATCH_MODEL": "ALL_ROWS"})
        assert rule.predicate(comp, {})

    def test_passes_unique_match_lookup(self, component_factory):
        rule = _rule_by_id("RULE-PERF-005")
        comp = component_factory(overrides={"component_name": "tMap"},
                                  params={"LOOKUP_MATCH_MODEL": "UNIQUE_MATCH"})
        assert not rule.predicate(comp, {})

    def test_ignores_non_tmap(self, component_factory):
        rule = _rule_by_id("RULE-PERF-005")
        comp = component_factory(overrides={"component_name": "tDBInput"},
                                  params={"LOOKUP_MATCH_MODEL": "ALL_ROWS"})
        assert not rule.predicate(comp, {})


class TestPerf006MissingParallelization:
    def test_detects_loop_without_parallelize(self, job_factory):
        rule = _rule_by_id("RULE-PERF-006")
        comps = [
            {"name": "loop", "component_name": "tLoop", "disabled": False, "parameters": {}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_with_parallelize(self, job_factory):
        rule = _rule_by_id("RULE-PERF-006")
        comps = [
            {"name": "loop", "component_name": "tLoop", "disabled": False, "parameters": {}},
            {"name": "par", "component_name": "tParallelize", "disabled": False, "parameters": {}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})


class TestPerf007ExcessiveMemory:
    def test_detects_large_buffer(self, job_factory):
        rule = _rule_by_id("RULE-PERF-007")
        comps = [
            {"name": "buf", "component_name": "tBufferOutput", "disabled": False,
             "parameters": {"BUFFER_SIZE": "50000"}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_small_buffer(self, job_factory):
        rule = _rule_by_id("RULE-PERF-007")
        comps = [
            {"name": "buf", "component_name": "tBufferOutput", "disabled": False,
             "parameters": {"BUFFER_SIZE": "100"}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})

    def test_ignores_non_buffer_comps(self, job_factory):
        rule = _rule_by_id("RULE-PERF-007")
        comps = [
            {"name": "input", "component_name": "tDBInput", "disabled": False,
             "parameters": {"BUFFER_SIZE": "50000"}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})


class TestPerf008ExcessiveRedundancy:
    def test_detects_duplicate_configs(self, job_factory):
        rule = _rule_by_id("RULE-PERF-008")
        comps = [
            {"name": "tMap_1", "component_name": "tMap", "disabled": False,
             "parameters": {"LOOKUP": "table1", "JOIN_TYPE": "INNER"}},
            {"name": "tMap_2", "component_name": "tMap", "disabled": False,
             "parameters": {"LOOKUP": "table1", "JOIN_TYPE": "INNER"}},
        ]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_unique_configs(self, job_factory):
        rule = _rule_by_id("RULE-PERF-008")
        comps = [
            {"name": "tMap_1", "component_name": "tMap", "disabled": False,
             "parameters": {"LOOKUP": "table1", "JOIN_TYPE": "INNER"}},
            {"name": "tMap_2", "component_name": "tMap", "disabled": False,
             "parameters": {"LOOKUP": "table2", "JOIN_TYPE": "LEFT"}},
        ]
        assert not rule.predicate(job_factory(components=comps), {})


class TestPerf009MonolithicSubjob:
    def test_detects_monolithic_job(self, job_factory):
        rule = _rule_by_id("RULE-PERF-009")
        comps = [{"name": f"c{i}", "component_name": "tMap", "disabled": False, "parameters": {}}
                 for i in range(35)]
        assert rule.predicate(job_factory(components=comps), {})

    def test_passes_with_trunjob(self, job_factory):
        rule = _rule_by_id("RULE-PERF-009")
        comps = [{"name": f"c{i}", "component_name": "tMap", "disabled": False, "parameters": {}}
                 for i in range(35)]
        comps.append({"name": "run", "component_name": "tRunJob", "disabled": False, "parameters": {}})
        assert not rule.predicate(job_factory(components=comps), {})

    def test_passes_small_job(self, job_factory):
        rule = _rule_by_id("RULE-PERF-009")
        comps = [{"name": f"c{i}", "component_name": "tMap", "disabled": False, "parameters": {}}
                 for i in range(10)]
        assert not rule.predicate(job_factory(components=comps), {})


class TestPerf010MissingRuntimeMonitoring:
    def test_detects_no_tflowmeter(self, inventory_factory):
        rule = _rule_by_id("RULE-PERF-010")
        assert rule.predicate(inventory_factory(), {})

    def test_passes_with_tflowmeter(self, inventory_factory):
        rule = _rule_by_id("RULE-PERF-010")
        jobs = [
            {"name": "j1", "components": [
                {"name": "meter", "component_name": "tFlowMeter", "disabled": False, "parameters": {}},
            ]},
        ]
        assert not rule.predicate(inventory_factory(jobs=jobs), {})

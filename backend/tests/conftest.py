import pytest


@pytest.fixture
def empty_inventory():
    return {
        "project_name": "test",
        "workspace_path": "/fake",
        "jobs": [],
        "components": [],
        "contexts": [],
        "context_groups": [],
        "item_files": [],
        "property_files": [],
        "project_files": [],
        "source_systems": [],
        "target_systems": [],
        "disabled_components": [],
        "parse_errors": [],
    }


@pytest.fixture
def minimal_job():
    return {
        "name": "test_job",
        "path": "/fake/test_job.item",
        "components": [],
        "contexts": [],
        "source_systems": [],
        "target_systems": [],
        "disabled_components": [],
    }


@pytest.fixture
def component(password: str = "", name: str = "tJDBCConnection") -> dict:
    return {
        "name": "comp1",
        "component_name": name,
        "disabled": False,
        "job": "test_job",
        "job_path": "/fake/test_job.item",
        "parameters": {},
    }


@pytest.fixture
def component_factory():
    def _make(overrides: dict = None, params: dict = None):
        c = {
            "name": "comp1",
            "component_name": "tJDBCConnection",
            "disabled": False,
            "job": "test_job",
            "job_path": "/fake/test_job.item",
            "parameters": params or {},
        }
        if overrides:
            c.update(overrides)
        return c
    return _make


@pytest.fixture
def job_factory():
    def _make(components: list[dict] = None, overrides: dict = None):
        j = {
            "name": "test_job",
            "path": "/fake/test_job.item",
            "components": components or [],
            "contexts": [],
            "source_systems": [],
            "target_systems": [],
            "disabled_components": [],
        }
        if overrides:
            j.update(overrides)
        return j
    return _make


@pytest.fixture
def inventory_factory():
    def _make(jobs: list[dict] = None, context_groups: list[dict] = None, overrides: dict = None):
        inv = {
            "project_name": "test",
            "workspace_path": "/fake",
            "jobs": jobs or [],
            "components": [],
            "contexts": [],
            "context_groups": context_groups or [],
            "item_files": [],
            "property_files": [],
            "project_files": [],
            "source_systems": [],
            "target_systems": [],
            "disabled_components": [],
            "parse_errors": [],
        }
        if overrides:
            inv.update(overrides)
        return inv
    return _make

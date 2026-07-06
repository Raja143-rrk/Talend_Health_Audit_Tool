from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.shared.models import (
    AgentArtifact,
    AgentContext,
    AgentFinding,
    AgentRecommendation,
    AgentResponse,
    AgentStatus,
    FindingSeverity,
)


@pytest.fixture
def agent_context() -> AgentContext:
    return AgentContext(
        analysis_id="test-analysis-001",
        project_name="TestProject",
        metadata={
            "workspace_path": "/fake/workspace",
            "talend_inventory": {
                "project_name": "TestProject",
                "workspace_path": "/fake/workspace",
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
            },
        },
    )


@pytest.fixture
def mock_rule_engine():
    engine = MagicMock()
    engine.evaluate = MagicMock(return_value=[])
    engine.validate_findings = MagicMock(side_effect=lambda findings, **kwargs: findings)
    engine.configure = MagicMock()
    return engine


@pytest.fixture
def sample_finding() -> AgentFinding:
    return AgentFinding(
        id="RULE-SEC-001-test",
        title="Test finding",
        job_name="test_job",
        component_name="comp1",
        component_type="tJDBCConnection",
        category="security",
        severity=FindingSeverity.WARNING,
        rule_triggered="RULE-SEC-001",
        description="A test finding",
        evidence={
            "rule_id": "RULE-SEC-001",
            "job_name": "test_job",
            "component_name": "comp1",
            "component_type": "tJDBCConnection",
            "xml_file": "/fake/test_job.item",
            "xml_path": "/job/component/parameter",
            "matched_value": "s3cret",
            "rule_triggered": "RULE-SEC-001",
        },
    )


@pytest.fixture
def sample_recommendation() -> AgentRecommendation:
    return AgentRecommendation(
        id="REC-001",
        title="Test recommendation",
        priority="P1",
        category="security",
        rationale="Test rationale",
        action="Test action",
        expected_impact="Test impact",
    )


@pytest.fixture
def started_at() -> datetime:
    return datetime.now(timezone.utc)

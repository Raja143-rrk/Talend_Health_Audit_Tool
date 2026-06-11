from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverity(StrEnum):
    INFORMATIONAL = "informational"
    ADVISORY = "advisory"
    WARNING = "warning"
    RISK = "risk"
    CRITICAL_RISK = "critical_risk"


class AgentContext(BaseModel):
    analysis_id: str
    project_name: str = "Talend Health Analyzer"
    upload_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentArtifact(BaseModel):
    name: str
    artifact_type: str
    path: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentFinding(BaseModel):
    id: str
    title: str
    job_name: str = "unknown"
    component_name: str = "unknown"
    component_type: str = "unknown"
    category: str
    severity: FindingSeverity
    rule_triggered: str = "unknown"
    description: str
    impact: str = ""
    recommendation: str = ""
    source: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class AgentRecommendation(BaseModel):
    id: str
    title: str
    priority: str
    job_name: str | None = None
    component_name: str | None = None
    component_type: str | None = None
    category: str = "recommendation"
    severity: str = "informational"
    rule_triggered: str | None = None
    finding_id: str | None = None
    rationale: str
    action: str
    expected_impact: str


class AgentResponse(BaseModel):
    agent_name: str
    status: AgentStatus
    started_at: datetime
    completed_at: datetime | None = None
    attempts: int = 1
    duration_ms: int | None = None
    artifacts: list[AgentArtifact] = Field(default_factory=list)
    findings: list[AgentFinding] = Field(default_factory=list)
    recommendations: list[AgentRecommendation] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    @classmethod
    def completed(
        cls,
        agent_name: str,
        started_at: datetime,
        artifacts: list[AgentArtifact] | None = None,
        findings: list[AgentFinding] | None = None,
        recommendations: list[AgentRecommendation] | None = None,
        metrics: dict[str, Any] | None = None,
        attempts: int = 1,
    ) -> "AgentResponse":
        completed_at = datetime.now(timezone.utc)
        return cls(
            agent_name=agent_name,
            status=AgentStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            attempts=attempts,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            artifacts=artifacts or [],
            findings=findings or [],
            recommendations=recommendations or [],
            metrics=metrics or {},
        )

    @classmethod
    def failed(
        cls,
        agent_name: str,
        started_at: datetime,
        error: Exception,
        attempts: int,
    ) -> "AgentResponse":
        completed_at = datetime.now(timezone.utc)
        return cls(
            agent_name=agent_name,
            status=AgentStatus.FAILED,
            started_at=started_at,
            completed_at=completed_at,
            attempts=attempts,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            errors=[str(error)],
        )


AgentExecutionResult = AgentResponse

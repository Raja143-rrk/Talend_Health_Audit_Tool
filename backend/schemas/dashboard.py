from typing import Any

from pydantic import BaseModel, Field


class AnalysisLog(BaseModel):
    timestamp: str
    message: str
    level: str


class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    status: str
    progress: int
    current_step: str
    logs: list[AnalysisLog]


class DashboardMetric(BaseModel):
    label: str
    value: int
    suffix: str | None = None
    change: str = ""
    severity: str


class CategoryScore(BaseModel):
    key: str
    label: str
    score: int
    grade: str


class ScoreBreakdown(BaseModel):
    overall_score: int
    grade: str
    category_scores: list[CategoryScore] = Field(default_factory=list)


class ComplianceCategoryScore(BaseModel):
    key: str
    label: str
    score: int
    grade: str
    total_rules: int
    passed_rules: int
    failed_rules: int
    failed_rule_ids: list[str] = Field(default_factory=list)


class ComplianceBreakdown(BaseModel):
    overall_score: int
    grade: str
    maturity: str
    category_scores: list[ComplianceCategoryScore] = Field(default_factory=list)
    total_rules_evaluated: int
    total_passed: int
    total_failed: int


class DashboardSummaryResponse(BaseModel):
    project_name: str
    environment: str
    total_jobs: int = 0
    job_names: list[str] = Field(default_factory=list)
    compliance_score: int = 100
    compliance_grade: str = "Optimized"
    compliance_maturity: str = "standard"
    compliance_breakdown: ComplianceBreakdown | None = None
    last_analyzed_at: str
    metrics: list[DashboardMetric]
    score_breakdown: ScoreBreakdown


class ChartPoint(BaseModel):
    name: str
    value: int | None = None
    source: int | None = None
    target: int | None = None
    critical_risk: int | None = None
    risk: int | None = None
    warning: int | None = None
    advisory: int | None = None
    informational: int | None = None
    score: int | None = None
    runtime: int | None = None
    memory: int | None = None
    retries: int | None = None


class ChartDataResponse(BaseModel):
    component_distribution: list[ChartPoint] = Field(default_factory=list)
    active_component_distribution: list[ChartPoint] = Field(default_factory=list)
    disabled_component_distribution: list[ChartPoint] = Field(default_factory=list)
    performance_issues: list[ChartPoint] = Field(default_factory=list)
    security_issues: list[ChartPoint] = Field(default_factory=list)
    source_target_systems: list[ChartPoint] = Field(default_factory=list)
    score_breakdown: list[ChartPoint] = Field(default_factory=list)
    risk_timeline: list[ChartPoint] = Field(default_factory=list)


class Finding(BaseModel):
    id: str
    name: str
    job_name: str
    component_name: str
    component_type: str
    category: str
    severity: str
    rule_triggered: str
    status: str = "open"
    owner: str = "unassigned"
    impact: str = ""
    recommendation: str
    remediation: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class FindingsResponse(BaseModel):
    total: int
    items: list[Finding]


class Recommendation(BaseModel):
    id: str
    title: str
    category: str
    severity: str
    priority: str
    job_name: str | None = None
    component_name: str | None = None
    component_type: str | None = None
    rule_triggered: str | None = None
    finding_id: str | None = None
    suggestion: str
    expected_impact: str
    rationale: str | None = None


class ComponentDrillDown(BaseModel):
    job_name: str
    component_name: str
    component_type: str
    findings: list[Finding] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)


class RecommendationsResponse(BaseModel):
    total: int
    items: list[Recommendation]


class AgentStatusInfo(BaseModel):
    name: str
    label: str
    description: str
    status: str
    duration_ms: int | None = None
    findings_count: int = 0
    errors: list[str] = Field(default_factory=list)


class DashboardOverviewResponse(BaseModel):
    analysis_id: str | None = None
    status: str
    summary: DashboardSummaryResponse
    charts: ChartDataResponse
    recommendations: RecommendationsResponse
    security_findings: FindingsResponse
    performance_findings: FindingsResponse
    component_drilldown: list[ComponentDrillDown] = Field(default_factory=list)
    agents: list[AgentStatusInfo] = Field(default_factory=list)

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
    total_rules: int = 0
    passed_rules: int = 0
    failed_rules: int = 0


class ScoreBreakdown(BaseModel):
    overall_score: int
    grade: str
    maturity: str = "standard"
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
    total_subjobs: int = 0
    total_master_jobs: int = 0
    subjob_names: list[str] = Field(default_factory=list)
    master_job_names: list[str] = Field(default_factory=list)
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
    subjob_name: str = ""
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


class OperationalPerformanceMetrics(BaseModel):
    performance_score: int = 100
    performance_grade: str = "Optimized"
    overall_failure_rate: float = 0.0
    total_executions: int = 0
    total_failures: int = 0
    recurring_failures: int = 0
    average_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0
    average_restart_delay_hours: float = 0.0
    total_restarts: int = 0
    top_5_longest_jobs: list[dict[str, Any]] = Field(default_factory=list)
    daily_trend: list[dict[str, Any]] = Field(default_factory=list)
    failed_jobs_count: int = 0
    failed_executions: list[dict[str, Any]] = Field(default_factory=list)
    error_groups: dict[str, list[str]] = Field(default_factory=dict)


class DashboardOverviewResponse(BaseModel):
    analysis_id: str | None = None
    status: str
    summary: DashboardSummaryResponse
    charts: ChartDataResponse
    recommendations: RecommendationsResponse
    security_findings: FindingsResponse
    performance_findings: FindingsResponse
    operational_performance: OperationalPerformanceMetrics = Field(default_factory=OperationalPerformanceMetrics)
    component_drilldown: list[ComponentDrillDown] = Field(default_factory=list)
    agents: list[AgentStatusInfo] = Field(default_factory=list)

from pydantic import BaseModel, Field


class DashboardKpi(BaseModel):
    label: str
    value: int
    suffix: str | None = None
    severity: str


class DashboardChartData(BaseModel):
    component_distribution: list[dict] = Field(default_factory=list)
    active_component_distribution: list[dict] = Field(default_factory=list)
    disabled_component_distribution: list[dict] = Field(default_factory=list)
    severity_summary: list[dict] = Field(default_factory=list)
    issue_categories: list[dict] = Field(default_factory=list)
    source_target_systems: list[dict] = Field(default_factory=list)
    score_breakdown: list[dict] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    analysis_id: str
    project_name: str
    total_jobs: int
    job_names: list[str] = Field(default_factory=list)
    total_subjobs: int = 0
    total_master_jobs: int = 0
    subjob_names: list[str] = Field(default_factory=list)
    master_job_names: list[str] = Field(default_factory=list)
    total_components: int
    total_disabled_components: int = 0
    critical_issues: int
    compliance_score: int = 100
    compliance_grade: str = "Optimized"
    compliance_maturity: str = "standard"
    compliance_breakdown: dict = Field(default_factory=dict)
    kpis: list[DashboardKpi]
    severity_summary: dict[str, int]
    score_breakdown: dict = Field(default_factory=dict)
    charts: DashboardChartData
    recommendations: list[dict] = Field(default_factory=list)
    findings: list[dict] = Field(default_factory=list)
    component_traceability: list[dict] = Field(default_factory=list)
    remediation_mapping: dict[str, str] = Field(default_factory=dict)

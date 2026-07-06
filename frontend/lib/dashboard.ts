import { appConfig } from "@/lib/config";

export type DashboardMetric = {
  label: string;
  value: number;
  suffix?: string | null;
  change: string;
  severity: string;
};

export type CategoryScore = {
  key: string;
  label: string;
  score: number;
  grade: string;
  total_rules: number;
  passed_rules: number;
  failed_rules: number;
};

export type ScoreBreakdown = {
  overall_score: number;
  grade: string;
  maturity: string;
  category_scores: CategoryScore[];
};

export type DashboardRecommendation = {
  id: string;
  title: string;
  category: string;
  severity: string;
  priority: string;
  job_name?: string | null;
  component_name?: string | null;
  component_type?: string | null;
  rule_triggered?: string | null;
  finding_id?: string | null;
  suggestion: string;
  expected_impact: string;
  rationale?: string | null;
};

export type DashboardChartPoint = {
  name: string;
  value?: number | null;
  source?: number | null;
  target?: number | null;
  critical_risk?: number | null;
  risk?: number | null;
  warning?: number | null;
  advisory?: number | null;
  informational?: number | null;
  score?: number | null;
  runtime?: number | null;
  memory?: number | null;
  retries?: number | null;
};

export type DashboardFinding = {
  id: string;
  name: string;
  job_name: string;
  component_name: string;
  component_type: string;
  category: string;
  severity: string;
  rule_triggered: string;
  status: string;
  owner: string;
  impact: string;
  recommendation: string;
  subjob_name?: string | null;
  remediation?: string | null;
  evidence: Record<string, unknown>;
};

export type ComponentDrillDown = {
  job_name: string;
  component_name: string;
  component_type: string;
  findings: DashboardFinding[];
  recommendations: DashboardRecommendation[];
};

export type AgentInfo = {
  name: string;
  label: string;
  description: string;
  status: string;
  duration_ms: number | null;
  findings_count: number;
  errors: string[];
};

export type DailyTrendPoint = {
  date: string;
  executions: number;
  failures: number;
};

export type FailedExecution = {
  job_name: string;
  timestamp: string;
  error_message: string;
  execution_id: string;
};

export type OperationalPerformanceMetrics = {
  performance_score: number;
  performance_grade: string;
  overall_failure_rate: number;
  total_executions: number;
  total_failures: number;
  recurring_failures: number;
  average_duration_seconds: number;
  max_duration_seconds: number;
  average_restart_delay_hours: number;
  total_restarts: number;
  top_5_longest_jobs: Array<{ job_name: string; average_duration_seconds: number }>;
  daily_trend: DailyTrendPoint[];
  failed_jobs_count: number;
  failed_executions: FailedExecution[];
  error_groups: Record<string, string[]>;
};

export type DashboardOverview = {
  analysis_id?: string | null;
  status: string;
  summary: {
    project_name: string;
    environment: string;
    total_jobs: number;
    job_names: string[];
    compliance_score: number;
    compliance_grade: string;
    last_analyzed_at: string;
    metrics: DashboardMetric[];
    score_breakdown: ScoreBreakdown;
    total_subjobs?: number;
    total_master_jobs?: number;
    subjob_names?: string[];
    master_job_names?: string[];
  };
  recommendations: {
    total: number;
    items: DashboardRecommendation[];
  };
  charts: {
    component_distribution: DashboardChartPoint[];
    active_component_distribution: DashboardChartPoint[];
    disabled_component_distribution: DashboardChartPoint[];
    performance_issues: DashboardChartPoint[];
    security_issues: DashboardChartPoint[];
    source_target_systems: DashboardChartPoint[];
    score_breakdown: DashboardChartPoint[];
    risk_timeline: DashboardChartPoint[];
  };
  security_findings: {
    total: number;
    items: DashboardFinding[];
  };
  performance_findings: {
    total: number;
    items: DashboardFinding[];
  };
  operational_performance: OperationalPerformanceMetrics;
  component_drilldown: ComponentDrillDown[];
  agents: AgentInfo[];
};

export async function getDashboardOverview(
  analysisId: string,
  jobName?: string,
): Promise<DashboardOverview> {
  const params = new URLSearchParams({ analysis_id: analysisId });
  if (jobName) {
    params.set("job_name", jobName);
  }
  const response = await fetch(
    `${appConfig.apiBaseUrl.replace(/\/$/, "")}/dashboard?${params.toString()}`,
    { cache: "no-store" },
  );

  if (!response.ok) {
    throw new Error(`Dashboard request failed with status ${response.status}.`);
  }

  return (await response.json()) as DashboardOverview;
}

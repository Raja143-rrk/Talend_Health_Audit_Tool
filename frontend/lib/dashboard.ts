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

export type DashboardOverview = {
  analysis_id?: string | null;
  status: string;
  summary: {
    project_name: string;
    environment: string;
    compliance_score: number;
    compliance_grade: string;
    last_analyzed_at: string;
    metrics: DashboardMetric[];
    score_breakdown: ScoreBreakdown;
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
  component_drilldown: ComponentDrillDown[];
  agents: AgentInfo[];
};

export async function getDashboardOverview(
  analysisId: string,
): Promise<DashboardOverview> {
  const response = await fetch(
    `${appConfig.apiBaseUrl.replace(/\/$/, "")}/dashboard?analysis_id=${encodeURIComponent(analysisId)}`,
    { cache: "no-store" },
  );

  if (!response.ok) {
    throw new Error(`Dashboard request failed with status ${response.status}.`);
  }

  return (await response.json()) as DashboardOverview;
}

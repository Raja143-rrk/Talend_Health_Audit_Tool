"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  Bug,
  Download,
  FileText,
  Gauge,
  HardDrive,
  Layers,
  Search,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { AnalysisLoader } from "@/components/dashboard/analysis-loader";
import { AiAgentsSection } from "@/components/dashboard/ai-agents-section";
import { AnalysisTabs } from "@/components/dashboard/analysis-tabs";
import { AiChatPanel } from "@/components/dashboard/ai-chat-panel";
import { AnalyticsChartGrid } from "@/components/dashboard/analytics-charts";
import { JobFilter } from "@/components/dashboard/job-filter";
import {
  DashboardLayout,
  type DashboardSection,
} from "@/components/dashboard/dashboard-layout";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { cn } from "@/lib/utils";
import { PerformanceView } from "@/components/performance/performance-view";
import {
  getDashboardOverview,
  type ComponentDrillDown,
  type DashboardFinding,
  type DashboardOverview,
} from "@/lib/dashboard";
import {
  fetchProjectUploadSummary,
  type ProjectUploadSummary,
} from "@/lib/execution-logs";
import type { AnalysisTaskStatus } from "@/lib/tasks";

function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-slate-950">
      <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
        {eyebrow}
      </p>
      <h1 className="mt-2 text-3xl font-semibold text-slate-950 dark:text-white">
        {title}
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
        {description}
      </p>
    </section>
  );
}

function findingKey(finding: DashboardFinding) {
  return `${finding.job_name}|${finding.component_name}|${finding.component_type}`;
}

function filterDrilldown(
  drilldown: ComponentDrillDown[] = [],
  findings: DashboardFinding[] = [],
) {
  const keys = new Set(findings.map(findingKey));
  return drilldown
    .map((component) => ({
      ...component,
      findings: component.findings.filter((finding) => keys.has(findingKey(finding))),
      recommendations: component.recommendations.filter(
        (recommendation) =>
          keys.has(
            `${recommendation.job_name ?? component.job_name}|${recommendation.component_name ?? component.component_name}|${recommendation.component_type ?? component.component_type}`,
          ),
      ),
    }))
    .filter((component) => keys.has(`${component.job_name}|${component.component_name}|${component.component_type}`));
}

function ComponentsSection({
  dashboard,
  query = "",
  jobName = "",
}: {
  dashboard: DashboardOverview | null;
  query?: string;
  jobName?: string;
}) {
  const [localQuery, setLocalQuery] = useState("");
  const effectiveQuery = query || localQuery;
  const normalizedQuery = effectiveQuery.trim().toLowerCase();
  const components = (dashboard?.component_drilldown ?? []).filter((component) => {
    if (jobName && component.job_name !== jobName) {
      return false;
    }
    if (component.component_name === component.job_name) {
      return false;
    }
    if (!normalizedQuery) {
      return true;
    }
    return [
      component.job_name,
      component.component_name,
      component.component_type,
      ...component.findings.map((finding) => finding.rule_triggered),
      ...component.recommendations.map((recommendation) => recommendation.suggestion),
    ]
      .join(" ")
      .toLowerCase()
      .includes(normalizedQuery);
  });
  const activeDistribution = dashboard?.charts?.active_component_distribution ?? [];
  const disabledDistribution = dashboard?.charts?.disabled_component_distribution ?? [];
  const totalComponents = dashboard?.summary?.metrics?.find(
    (metric) => metric.label === "Total Components",
  )?.value ?? 0;
  const disabledComponents = dashboard?.summary?.metrics?.find(
    (metric) => metric.label === "Disabled Components",
  )?.value ?? 0;
  const activeComponents = totalComponents - disabledComponents;
  const issueCount = components.reduce((total, component) => total + component.findings.length, 0);

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Components"
        title="Component inventory and usage"
        description="Review component distribution, impacted components, status, and mapped issues without security or performance detail duplication."
      />
      <section className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-950">
        <div className="relative max-w-xs flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={localQuery}
            onChange={(e) => setLocalQuery(e.target.value)}
            placeholder="Search components, jobs, rules..."
            className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 pl-9 text-sm text-slate-950 outline-none transition placeholder:text-slate-500 focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/15 dark:border-white/10 dark:bg-slate-950 dark:text-white dark:placeholder:text-slate-400"
          />
        </div>
      </section>
      <section className="grid gap-4 md:grid-cols-4">
        {[
          ["Active Components", activeComponents],
          ["Disabled Components", disabledComponents],
          ["Impacted Components", components.length],
          ["Mapped Issues", issueCount],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-slate-950"
          >
            <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
              {label}
            </p>
            <p className="mt-3 text-3xl font-semibold">{value}</p>
          </div>
        ))}
      </section>
      {disabledDistribution.length > 0 ? (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-5 shadow-sm dark:border-amber-500/30 dark:bg-amber-950/20">
          <p className="text-xs font-semibold uppercase text-amber-700 dark:text-amber-400">
            Disabled Components — Cleanup Recommended
          </p>
          <p className="mt-1 text-sm text-amber-600 dark:text-amber-300">
            The following component types have deactivated instances that should be removed from job designs.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {disabledDistribution.map((point) => (
              <div
                key={point.name}
                className="rounded-lg border border-amber-300 bg-white p-4 dark:border-amber-500/30 dark:bg-amber-950/30"
              >
                <p className="font-semibold">{point.name}</p>
                <p className="mt-2 text-2xl font-semibold">{point.value ?? 0} disabled</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-slate-950">
        <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
          Active Component Usage By Type
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {activeDistribution.length ? activeDistribution.map((point) => (
            <div
              key={point.name}
              className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5"
            >
              <p className="font-semibold">{point.name}</p>
              <p className="mt-2 text-2xl font-semibold">{point.value ?? 0}</p>
            </div>
          )) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {jobName ? "No components found for the selected job." : "No component inventory output available."}
            </p>
          )}
        </div>
      </section>
      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-slate-950">
        <div className="border-b border-slate-200 p-5 dark:border-white/10">
          <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
            Component Status
          </p>
          <h2 className="mt-2 text-xl font-semibold">Issues by component</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase text-slate-500 dark:bg-white/5 dark:text-slate-400">
              <tr>
                {["Job", "Component", "Type", "Status", "Issues"].map((label) => (
                  <th key={label} className="px-4 py-3 font-semibold">{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {components.length ? components.map((component) => (
                <tr
                  key={`${component.job_name}-${component.component_name}-${component.component_type}`}
                  className="border-t border-slate-200 dark:border-white/10"
                >
                  <td className="px-4 py-4">{component.job_name}</td>
                  <td className="px-4 py-4 font-semibold">{component.component_name}</td>
                  <td className="px-4 py-4">{component.component_type}</td>
                  <td className="px-4 py-4">
                    {component.findings.length ? "Action required" : "Healthy"}
                  </td>
                  <td className="px-4 py-4">{component.findings.length}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-sm text-slate-500 dark:text-slate-400">
                    {jobName ? "No components found for the selected job." : "No component-level issues are available in the current dashboard output."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function ReportsSection({ dashboard }: { dashboard: DashboardOverview | null }) {
  const allFindings = dashboard
    ? [
        ...dashboard.security_findings.items,
        ...dashboard.performance_findings.items,
      ]
    : [];

  const categories = [
    { key: "architecture", label: "Architecture" },
    { key: "component", label: "Maintainability" },
    { key: "performance", label: "Performance" },
    { key: "security", label: "Security" },
  ];

  const findMetric = (label: string) =>
    dashboard?.summary.metrics?.find((m) => m.label === label)?.value ?? 0;

  const exportJson = () => {
    if (!dashboard) return;
    const catData = categories.map((cat) => ({
      category: cat.label,
      count: allFindings.filter((f) => f.category === cat.key).length,
      findings: allFindings.filter((f) => f.category === cat.key),
    }));
    const report = {
      project_name: dashboard.summary.project_name,
      analysis_id: dashboard.analysis_id,
      last_analyzed_at: dashboard.summary.last_analyzed_at,
      summary: {
        compliance_score: dashboard.summary.compliance_score,
        compliance_grade: dashboard.summary.compliance_grade,
        total_jobs: findMetric("Total Jobs"),
        total_subjobs: dashboard.summary.total_subjobs ?? 0,
        total_master_jobs: dashboard.summary.total_master_jobs ?? 0,
        subjob_names: dashboard.summary.subjob_names ?? [],
        master_job_names: dashboard.summary.master_job_names ?? [],
        total_components: findMetric("Total Components"),
        disabled_components: findMetric("Disabled Components"),
        critical_issues: findMetric("Critical Issues"),
        total_findings: (dashboard.security_findings?.total ?? 0) + (dashboard.performance_findings?.total ?? 0),
      },
      findings_by_category: catData,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `talend-health-report-${dashboard.analysis_id ?? "latest"}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const csvEsc = (v: unknown) => `"${String(v).replaceAll('"', '""')}"`;

  const exportFindingsCsv = () => {
    if (!dashboard) return;
    const lines: string[] = [];
    lines.push(`# Talend Health Audit Report - ${dashboard.summary.project_name}`);
    lines.push(`# Analysis ID: ${dashboard.analysis_id}`);
    lines.push(`# Last analyzed: ${dashboard.summary.last_analyzed_at}`);
    lines.push(`# Compliance Score: ${dashboard.summary.compliance_score}%`);
    lines.push(`# Grade: ${dashboard.summary.compliance_grade}`);
    lines.push(`# Total Jobs: ${findMetric("Total Jobs")} (Master: ${dashboard.summary.total_master_jobs ?? 0}, Subjobs: ${dashboard.summary.total_subjobs ?? 0})`);
    lines.push(`# Total Components: ${findMetric("Total Components")}`);
    lines.push(`# Disabled Components: ${findMetric("Disabled Components")}`);
    lines.push(`# Critical Issues: ${findMetric("Critical Issues")}`);
    lines.push(`# Total Findings: ${(dashboard.security_findings?.total ?? 0) + (dashboard.performance_findings?.total ?? 0)}`);
    lines.push("");

    for (const cat of categories) {
      const catFindings = allFindings.filter((f) => f.category === cat.key);
      if (catFindings.length === 0) continue;
      lines.push(`# ${cat.label} Findings (${catFindings.length})`);
      lines.push(["id", "name", "job", "component", "type", "severity", "rule", "subjob"].map(csvEsc).join(","));
      for (const f of catFindings) {
        lines.push([f.id, f.name, f.job_name, f.component_name, f.component_type, f.severity, f.rule_triggered, f.subjob_name ?? ""].map(csvEsc).join(","));
      }
      lines.push("");
    }
    const csv = lines.join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `talend-health-findings-${dashboard.analysis_id ?? "latest"}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportWord = () => {
    if (!dashboard) return;

    const catData = categories.map((cat) => ({
      ...cat,
      findings: allFindings.filter((f) => f.category === cat.key),
    }));

    const rowsHtml = catData.map((cat) => `
      <tr>
        <td style="padding:8px;border:1px solid #ccc;font-weight:bold">${cat.label}</td>
        <td style="padding:8px;border:1px solid #ccc">${cat.findings.length}</td>
      </tr>
    `).join("");

    const catTablesHtml = catData.filter((c) => c.findings.length > 0).map((cat) => `
      <h2 style="color:#1e293b;border-bottom:2px solid #7c3aed;padding-bottom:6px;margin-top:30px">${cat.label} Findings</h2>
      <table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:12px">
        <thead>
          <tr style="background:#1e293b;color:#fff">
            <th style="padding:8px;border:1px solid #334155;text-align:left">ID</th>
            <th style="padding:8px;border:1px solid #334155;text-align:left">Name</th>
            <th style="padding:8px;border:1px solid #334155;text-align:left">Job</th>
            <th style="padding:8px;border:1px solid #334155;text-align:left">Subjob</th>
            <th style="padding:8px;border:1px solid #334155;text-align:left">Component</th>
            <th style="padding:8px;border:1px solid #334155;text-align:left">Severity</th>
            <th style="padding:8px;border:1px solid #334155;text-align:left">Rule</th>
          </tr>
        </thead>
        <tbody>
          ${cat.findings.map((f) => `
            <tr>
              <td style="padding:6px;border:1px solid #e2e8f0">${f.id}</td>
              <td style="padding:6px;border:1px solid #e2e8f0">${f.name}</td>
              <td style="padding:6px;border:1px solid #e2e8f0">${f.job_name}</td>
              <td style="padding:6px;border:1px solid #e2e8f0">${f.subjob_name ?? ""}</td>
              <td style="padding:6px;border:1px solid #e2e8f0">${f.component_name}</td>
              <td style="padding:6px;border:1px solid #e2e8f0">${f.severity}</td>
              <td style="padding:6px;border:1px solid #e2e8f0">${f.rule_triggered}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `).join("");

    const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Talend Health Audit Report</title>
  <style>
    body { font-family: Calibri, Arial, sans-serif; margin: 40px; color: #1e293b; }
    h1 { color: #0d9488; font-size: 28px; margin-bottom: 4px; }
    .subtitle { color: #64748b; font-size: 14px; margin-bottom: 24px; }
    .summary-grid { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }
    .summary-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 24px; min-width: 140px; }
    .summary-card .label { font-size: 11px; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px; }
    .summary-card .value { font-size: 24px; font-weight: bold; margin-top: 4px; }
  </style>
</head>
<body>
  <h1>Talend Health Audit Report</h1>
  <p class="subtitle">${dashboard.summary.project_name} &mdash; ${dashboard.summary.last_analyzed_at}</p>

  <h2 style="color:#1e293b;border-bottom:2px solid #0d9488;padding-bottom:6px">Dashboard Summary</h2>
  <div class="summary-grid">
    <div class="summary-card">
      <div class="label">Compliance Score</div>
      <div class="value">${dashboard.summary.compliance_score}%</div>
    </div>
    <div class="summary-card">
      <div class="label">Grade</div>
      <div class="value">${dashboard.summary.compliance_grade}</div>
    </div>
    <div class="summary-card">
      <div class="label">Total Jobs</div>
      <div class="value">${findMetric("Total Jobs")}</div>
      <div style="font-size:11px;color:#64748b;margin-top:2px">${dashboard.summary.total_master_jobs ?? 0} master, ${dashboard.summary.total_subjobs ?? 0} subjob${(dashboard.summary.total_subjobs ?? 0) !== 1 ? "s" : ""}</div>
    </div>
    <div class="summary-card">
      <div class="label">Total Components</div>
      <div class="value">${findMetric("Total Components")}</div>
    </div>
    <div class="summary-card">
      <div class="label">Disabled Components</div>
      <div class="value">${findMetric("Disabled Components")}</div>
    </div>
    <div class="summary-card">
      <div class="label">Critical Issues</div>
      <div class="value">${findMetric("Critical Issues")}</div>
    </div>
    <div class="summary-card">
      <div class="label">Total Findings</div>
      <div class="value">${(dashboard.security_findings?.total ?? 0) + (dashboard.performance_findings?.total ?? 0)}</div>
    </div>
  </div>

  <h2 style="color:#1e293b;border-bottom:2px solid #7c3aed;padding-bottom:6px;margin-top:30px">Findings by Category</h2>
  <table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:13px">
    <thead>
      <tr style="background:#7c3aed;color:#fff">
        <th style="padding:10px;border:1px solid #6d28d9;text-align:left">Category</th>
        <th style="padding:10px;border:1px solid #6d28d9;text-align:left">Finding Count</th>
      </tr>
    </thead>
    <tbody>
      ${rowsHtml}
    </tbody>
  </table>

  ${catTablesHtml}

  <p style="margin-top:40px;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:12px">
    Generated by Talend Health Audit Tool &mdash; Analysis ID: ${dashboard.analysis_id}
  </p>
</body>
</html>`;

    const blob = new Blob([html], { type: "application/msword" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `talend-health-report-${dashboard.analysis_id ?? "latest"}.doc`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Reports"
        title="Report history and exports"
        description="Access the current analysis report and export dashboard data for audit review or offline distribution."
      />
      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-slate-950">
          <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
            Report History
          </p>
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
            <div className="flex items-start gap-3">
              <FileText className="mt-0.5 h-5 w-5 text-cyan-600 dark:text-cyan-300" />
              <div>
                <p className="font-semibold">{dashboard?.summary.project_name ?? "Current analysis"}</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Analysis ID: {dashboard?.analysis_id ?? "Not loaded"}
                </p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Last analyzed: {dashboard?.summary.last_analyzed_at ?? "Unavailable"}
                </p>
              </div>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-slate-950">
          <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
            Export Options
          </p>
          <div className="mt-4 space-y-3">
            <button
              type="button"
              onClick={exportJson}
              className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-semibold dark:border-white/10 dark:bg-white/5"
            >
              Export dashboard JSON
              <Download className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={exportFindingsCsv}
              className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-semibold dark:border-white/10 dark:bg-white/5"
            >
              Export findings CSV
              <Download className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={exportWord}
              className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-semibold dark:border-white/10 dark:bg-white/5"
            >
              Export report as Word
              <FileText className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function DashboardPageContent() {
  const searchParams = useSearchParams();
  const taskId = searchParams.get("taskId");
  const sectionParam = searchParams.get("section");
  const [activeSection, setActiveSection] = useState<DashboardSection>(
    (sectionParam as DashboardSection) ?? "Dashboard",
  );
  const [sectionQuery, setSectionQuery] = useState("");
  const [aiAgentsEnabled, setAiAgentsEnabled] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("aiAgentsEnabled") !== "false";
    }
    return true;
  });
  const [completedTask, setCompletedTask] = useState<AnalysisTaskStatus | null>(null);
  const [analysisRunning, setAnalysisRunning] = useState(Boolean(taskId));
  const [dashboard, setDashboard] = useState<DashboardOverview | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<string>("");
  const [allJobNames, setAllJobNames] = useState<string[]>([]);
  const [execLogSummary, setExecLogSummary] = useState<ProjectUploadSummary | null>(null);
  const completeAnalysis = useCallback((status?: AnalysisTaskStatus) => {
    if (status) {
      setCompletedTask(status);
    }
    setAnalysisRunning(false);
  }, []);
  const analysisId = completedTask?.analysis_id ?? searchParams.get("analysisId");

  useEffect(() => {
    if (analysisId) {
      fetchProjectUploadSummary(analysisId).then(setExecLogSummary);
    }
  }, [analysisId]);

  useEffect(() => {
    if (analysisRunning || !analysisId) {
      return;
    }

    let cancelled = false;
    const activeAnalysisId = analysisId;

    async function loadDashboard() {
      try {
        const overview = await getDashboardOverview(
          activeAnalysisId,
          selectedJob || undefined,
        );
        if (!cancelled) {
          setDashboard(overview);
          setDashboardError(null);
          if (overview.summary?.job_names?.length) {
            setAllJobNames((prev) => prev.length ? prev : overview.summary.job_names);
          }
        }
      } catch (error) {
        if (!cancelled) {
          setDashboardError(
            error instanceof Error
              ? error.message
              : "Unable to load generated dashboard.",
          );
        }
      }
    }

    void loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [analysisId, analysisRunning, selectedJob]);

  const jobNames = dashboard?.summary?.job_names ?? [];
  const projectName = dashboard?.summary?.project_name ?? "No dashboard output loaded";
  const complianceScore = dashboard?.summary?.compliance_score;
  const complianceGrade = dashboard?.summary?.compliance_grade;
  const totalJobs = dashboard?.summary?.metrics?.find((m) => m.label === "Total Jobs")?.value ?? 0;
  const totalSubjobs = dashboard?.summary?.total_subjobs ?? 0;
  const totalMasterJobs = dashboard?.summary?.total_master_jobs ?? 0;
  const totalComponents = dashboard?.summary?.metrics?.find((m) => m.label === "Total Components")?.value ?? 0;
  const disabledComponents = dashboard?.summary?.metrics?.find((m) => m.label === "Disabled Components")?.value ?? 0;
  const activeComponents = totalComponents - disabledComponents;
  const criticalIssues =
    dashboard?.summary?.metrics?.find((metric) => metric.label === "Critical Issues")?.value ?? 0;
  const totalFindings =
    (dashboard?.security_findings?.total ?? 0) + (dashboard?.performance_findings?.total ?? 0);
  const categoryScores = dashboard?.summary?.score_breakdown?.category_scores ?? [];
  const securityFindings = dashboard?.security_findings?.items ?? [];
  const performanceFindings = dashboard?.performance_findings?.items ?? [];
  const allFindings = [...securityFindings, ...performanceFindings];
  const architectureFindings = allFindings.filter((f) => f.category === "architecture");
  const maintainabilityFindings = allFindings.filter((f) => f.category === "component");
  const componentDrilldown = dashboard?.component_drilldown ?? [];
  const securityDrilldown = filterDrilldown(componentDrilldown, securityFindings);
  const performanceDrilldown = filterDrilldown(componentDrilldown, performanceFindings);
  const architectureDrilldown = filterDrilldown(componentDrilldown, architectureFindings);
  const maintainabilityDrilldown = filterDrilldown(componentDrilldown, maintainabilityFindings);
  useEffect(() => {
    localStorage.setItem("aiAgentsEnabled", String(aiAgentsEnabled));
  }, [aiAgentsEnabled]);

  const handleChatAction = useCallback((section: DashboardSection, query?: string) => {
    setSectionQuery(query ?? "");
    setActiveSection(section);
  }, []);

  return (
    <DashboardLayout
      activeSection={activeSection}
      onSectionChange={setActiveSection}
      aiAgentsEnabled={aiAgentsEnabled}
    >
      <AnimatePresence mode="wait">
        {analysisRunning ? (
          <AnalysisLoader
            key="analysis-loader"
            taskId={taskId}
            onComplete={completeAnalysis}
          />
        ) : (
          <motion.div
            key={`dashboard-content-${activeSection}`}
            className={cn("space-y-6", activeSection === "AI Chat" && "flex min-h-0 flex-col space-y-0")}
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.35 }}
          >
            {activeSection === "Dashboard" ? (
              <>
            <section className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 p-6 shadow-lg dark:border-white/10">
              <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br from-cyan-500/10 to-transparent blur-3xl" />
              <div className="relative flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-cyan-300">
                    Talend Health Audit
                  </p>
                  <h1 className="mt-2 text-3xl font-bold text-white">
                    {projectName}
                  </h1>
                </div>
                <div className="flex items-center gap-3">
                  <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/80 backdrop-blur-sm">
                    {completedTask
                      ? `Analysis ${completedTask.status}`
                      : "Analysis completed"}
                  </div>
                  {allJobNames.length > 1 ? (
                    <select
                      value={selectedJob}
                      onChange={(e) => setSelectedJob(e.target.value)}
                      className="h-10 rounded-xl border border-white/10 bg-white/5 px-3 text-sm text-white/80 outline-none backdrop-blur-sm focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20"
                    >
                      <option value="">All jobs</option>
                      {allJobNames.map((name) => (
                        <option key={name} value={name} className="bg-slate-800 text-white">
                          {name}
                        </option>
                      ))}
                    </select>
                  ) : null}
                  {complianceScore != null ? (
                    <div className="rounded-xl bg-cyan-500/15 px-4 py-2 text-sm font-semibold text-cyan-300 backdrop-blur-sm">
                      {complianceGrade}
                    </div>
                  ) : null}
                </div>
              </div>
              {dashboardError ? (
                <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                  {dashboardError}
                </div>
              ) : null}
            </section>

            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <KpiCard
                title="Health Score"
                value={complianceScore ?? 0}
                suffix="%"
                change={complianceGrade ?? "Pending"}
                tone={complianceScore != null && complianceScore >= 80 ? "emerald" : complianceScore != null && complianceScore >= 60 ? "amber" : "red"}
                icon={Gauge}
                subtitle={complianceGrade ?? undefined}
              />
              <KpiCard
                title="Critical Issues"
                value={criticalIssues}
                tone="red"
                icon={AlertTriangle}
              />
              <KpiCard
                title="Total Jobs"
                value={totalJobs}
                tone="blue"
                icon={HardDrive}
                subtitle={`${totalMasterJobs} master, ${totalSubjobs} subjob${totalSubjobs !== 1 ? "s" : ""}`}
              />
              <KpiCard
                title="Active Components"
                value={activeComponents}
                tone="cyan"
                icon={Layers}
                subtitle={`${disabledComponents} disabled`}
                onClick={() => setActiveSection("Components")}
              />
              <motion.article
                className="group relative overflow-hidden rounded-2xl border bg-gradient-to-br from-violet-500/20 to-violet-600/5 border-violet-500/30 bg-white/80 p-5 shadow-lg shadow-violet-500/10 backdrop-blur-xl transition-all dark:border-white/10 dark:bg-slate-950/80"
                whileHover={{ y: -4, scale: 1.02 }}
                transition={{ duration: 0.2 }}
              >
                <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gradient-to-br from-white/40 to-transparent blur-2xl dark:from-white/5" />
                <div className="relative">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        Total Findings
                      </p>
                      <p className="mt-2 text-3xl font-bold text-slate-950 dark:text-white">
                        {totalFindings}
                      </p>
                    </div>
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-500/15 text-violet-600 shadow-sm backdrop-blur-sm dark:text-violet-300">
                      <Bug className="h-5 w-5" />
                    </div>
                  </div>
                  {categoryScores.length > 0 ? (
                    <div className="mt-4 space-y-1">
                      {categoryScores.map((cs) => (
                        <div
                          key={cs.key}
                          className="flex cursor-pointer items-center justify-between text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                          onClick={() => setActiveSection(cs.label as DashboardSection)}
                        >
                          <span>{cs.label}</span>
                          <span className="font-semibold tabular-nums text-slate-700 dark:text-slate-200">
                            {cs.failed_rules}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </motion.article>
            </section>

            <AnalyticsChartGrid
              charts={dashboard?.charts}
              insightsSummary={{
                project_name: projectName,
                compliance_score: complianceScore,
                compliance_grade: complianceGrade,
                critical_issues: criticalIssues,
                total_findings: totalFindings,
                total_jobs: totalJobs ?? 0,
                total_components: totalComponents ?? 0,
                disabled_components: disabledComponents ?? 0,
              }}
              onNavigate={setActiveSection}
            />
              </>
            ) : null}

            {activeSection === "Security" ? (
              <>
                <SectionHeader
                  eyebrow="Security"
                  title="Security findings"
                  description="Focused view of security findings, affected components, severity, evidence, and remediation recommendations."
                />
                <section className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-950">
                  <div>
                    {selectedJob ? (
                      <p className="text-sm text-slate-600 dark:text-slate-300">
                        Showing results for <span className="font-semibold">{selectedJob}</span>
                      </p>
                    ) : (
                      <p className="text-sm text-slate-500 dark:text-slate-400">All jobs</p>
                    )}
                  </div>
                  <JobFilter
                    jobNames={allJobNames}
                    selectedJob={selectedJob}
                    onSelect={setSelectedJob}
                    onClear={() => setSelectedJob("")}
                  />
                </section>
                <AnalysisTabs
                  key={`security-findings-${sectionQuery}`}
                  lockedTab="security"
                  title="Security findings"
                  eyebrow="Security Workspace"
                  initialQuery={sectionQuery}
                  securityFindings={securityFindings}
                  recommendations={dashboard?.recommendations?.items}
                  componentDrilldown={securityDrilldown}
                />
              </>
            ) : null}

            {activeSection === "Performance" ? (
              <>
                <section className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-950">
                  <div>
                    {selectedJob ? (
                      <p className="text-sm text-slate-600 dark:text-slate-300">
                        Showing results for <span className="font-semibold">{selectedJob}</span>
                      </p>
                    ) : (
                      <p className="text-sm text-slate-500 dark:text-slate-400">All jobs</p>
                    )}
                  </div>
                  <JobFilter
                    jobNames={allJobNames}
                    selectedJob={selectedJob}
                    onSelect={setSelectedJob}
                    onClear={() => setSelectedJob("")}
                  />
                </section>
<PerformanceView
  op={dashboard?.operational_performance}
  recommendations={dashboard?.recommendations?.items}
  execLogSummary={execLogSummary}
/>
              </>
            ) : null}

            {activeSection === "Architecture" ? (
              <>
                <SectionHeader
                  eyebrow="Architecture"
                  title="Architecture findings"
                  description="Focused view of architecture findings, affected components, severity, evidence, and remediation recommendations."
                />
                <section className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-950">
                  <div>
                    {selectedJob ? (
                      <p className="text-sm text-slate-600 dark:text-slate-300">
                        Showing results for <span className="font-semibold">{selectedJob}</span>
                      </p>
                    ) : (
                      <p className="text-sm text-slate-500 dark:text-slate-400">All jobs</p>
                    )}
                  </div>
                  <JobFilter
                    jobNames={allJobNames}
                    selectedJob={selectedJob}
                    onSelect={setSelectedJob}
                    onClear={() => setSelectedJob("")}
                  />
                </section>
                <AnalysisTabs
                  key={`architecture-findings-${sectionQuery}`}
                  lockedTab="security"
                  title="Architecture findings"
                  eyebrow="Architecture Workspace"
                  initialQuery={sectionQuery}
                  securityFindings={architectureFindings}
                  recommendations={dashboard?.recommendations?.items}
                  componentDrilldown={architectureDrilldown}
                />
              </>
            ) : null}

            {activeSection === "Maintainability" ? (
              <>
                <SectionHeader
                  eyebrow="Maintainability"
                  title="Maintainability findings"
                  description="Focused view of maintainability findings, affected components, severity, evidence, and remediation recommendations."
                />
                <section className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-950">
                  <div>
                    {selectedJob ? (
                      <p className="text-sm text-slate-600 dark:text-slate-300">
                        Showing results for <span className="font-semibold">{selectedJob}</span>
                      </p>
                    ) : (
                      <p className="text-sm text-slate-500 dark:text-slate-400">All jobs</p>
                    )}
                  </div>
                  <JobFilter
                    jobNames={allJobNames}
                    selectedJob={selectedJob}
                    onSelect={setSelectedJob}
                    onClear={() => setSelectedJob("")}
                  />
                </section>
                <AnalysisTabs
                  key={`maintainability-findings-${sectionQuery}`}
                  lockedTab="security"
                  title="Maintainability findings"
                  eyebrow="Maintainability Workspace"
                  initialQuery={sectionQuery}
                  securityFindings={maintainabilityFindings}
                  recommendations={dashboard?.recommendations?.items}
                  componentDrilldown={maintainabilityDrilldown}
                />
              </>
            ) : null}

            {activeSection === "Components" ? (
              <>
                <section className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-950">
                  <div>
                    {selectedJob ? (
                      <p className="text-sm text-slate-600 dark:text-slate-300">
                        Showing results for <span className="font-semibold">{selectedJob}</span>
                      </p>
                    ) : (
                      <p className="text-sm text-slate-500 dark:text-slate-400">All jobs</p>
                    )}
                  </div>
                  <JobFilter
                    jobNames={allJobNames}
                    selectedJob={selectedJob}
                    onSelect={setSelectedJob}
                    onClear={() => setSelectedJob("")}
                  />
                </section>
                <ComponentsSection dashboard={dashboard} query={sectionQuery} jobName={selectedJob} />
              </>
            ) : null}

            {activeSection === "AI Chat" ? (
              <div className="flex flex-1 min-h-0 flex-col">
                <AiChatPanel
                  analysisId={analysisId}
                  onAction={handleChatAction}
                />
              </div>
            ) : null}

            {activeSection === "Recommendations" ? (
              <>
                <SectionHeader
                  eyebrow="Recommendations"
                  title="Recommendations and remediation"
                  description="Prioritized remediation actions consolidated from the current analysis."
                />
                <section className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-950">
                  <div>
                    {selectedJob ? (
                      <p className="text-sm text-slate-600 dark:text-slate-300">
                        Showing results for <span className="font-semibold">{selectedJob}</span>
                      </p>
                    ) : (
                      <p className="text-sm text-slate-500 dark:text-slate-400">All jobs</p>
                    )}
                  </div>
                  <JobFilter
                    jobNames={allJobNames}
                    selectedJob={selectedJob}
                    onSelect={setSelectedJob}
                    onClear={() => setSelectedJob("")}
                  />
                </section>
                <AnalysisTabs
                  key={`recommendation-actions-${sectionQuery}`}
                  lockedTab="recommendations"
                  title="Remediation actions"
                  eyebrow="Recommendations Workspace"
                  initialQuery={sectionQuery}
                  recommendations={dashboard?.recommendations?.items}
                />
              </>
            ) : null}

            {activeSection === "AI Agents" ? (
              <AiAgentsSection agents={dashboard?.agents ?? []} />
            ) : null}

            {activeSection === "Reports" ? (
              <ReportsSection dashboard={dashboard} />
            ) : null}

            {activeSection === "Settings" ? (
              <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-slate-950">
                <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                  Settings
                </p>
                <h1 className="mt-2 text-3xl font-semibold text-slate-950 dark:text-white">
                  Dashboard settings
                </h1>
                <div className="mt-6 space-y-4">
                  <div className="flex items-center justify-between rounded-lg border border-slate-200 p-4 dark:border-white/10">
                    <div>
                      <p className="text-sm font-semibold text-slate-950 dark:text-white">
                        AI Agents
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Show or hide the AI Agents module in the sidebar.
                      </p>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={aiAgentsEnabled}
                      onClick={() => setAiAgentsEnabled((prev) => !prev)}
                      className={cn(
                        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-slate-300 dark:focus-visible:ring-offset-slate-950",
                        aiAgentsEnabled
                          ? "bg-cyan-600"
                          : "bg-slate-200 dark:bg-slate-700",
                      )}
                    >
                      <span
                        className={cn(
                          "pointer-events-none block h-5 w-5 rounded-full bg-white shadow-lg ring-0 transition-transform",
                          aiAgentsEnabled ? "translate-x-5" : "translate-x-0",
                        )}
                      />
                    </button>
                  </div>
                </div>
              </section>
            ) : null}
          </motion.div>
        )}
      </AnimatePresence>
    </DashboardLayout>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<AnalysisLoader onComplete={() => undefined} />}>
      <DashboardPageContent />
    </Suspense>
  );
}

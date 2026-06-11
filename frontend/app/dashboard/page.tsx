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
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { AnalysisLoader } from "@/components/dashboard/analysis-loader";
import { AiAgentsSection } from "@/components/dashboard/ai-agents-section";
import { AnalysisTabs } from "@/components/dashboard/analysis-tabs";
import { AiChatPanel } from "@/components/dashboard/ai-chat-panel";
import { AnalyticsChartGrid } from "@/components/dashboard/analytics-charts";
import {
  DashboardLayout,
  type DashboardSection,
} from "@/components/dashboard/dashboard-layout";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { cn } from "@/lib/utils";
import {
  getDashboardOverview,
  type ComponentDrillDown,
  type DashboardFinding,
  type DashboardOverview,
} from "@/lib/dashboard";
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
}: {
  dashboard: DashboardOverview | null;
  query?: string;
}) {
  const normalizedQuery = query.trim().toLowerCase();
  const components = (dashboard?.component_drilldown ?? []).filter((component) => {
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
  const issueCount = components.reduce((total, component) => total + component.findings.length, 0);

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Components"
        title="Component inventory and usage"
        description="Review component distribution, impacted components, status, and mapped issues without security or performance detail duplication."
      />
      <section className="grid gap-4 md:grid-cols-4">
        {[
          ["Active Components", totalComponents],
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
              No component inventory output available.
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
                {["Job", "Component", "Type", "Status", "Issues", "Rules"].map((label) => (
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
                  <td className="px-4 py-4">
                    {Array.from(new Set(component.findings.map((finding) => finding.rule_triggered))).join(", ") || "None"}
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-sm text-slate-500 dark:text-slate-400">
                    No component-level issues are available in the current dashboard output.
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
  const exportJson = () => {
    if (!dashboard) return;
    const blob = new Blob([JSON.stringify(dashboard, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `talend-health-report-${dashboard.analysis_id ?? "latest"}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportFindingsCsv = () => {
    if (!dashboard) return;
    const findings = [
      ...dashboard.security_findings.items,
      ...dashboard.performance_findings.items,
    ];
    const rows = [
      ["id", "name", "job", "component", "type", "category", "severity", "rule"],
      ...findings.map((finding) => [
        finding.id,
        finding.name,
        finding.job_name,
        finding.component_name,
        finding.component_type,
        finding.category,
        finding.severity,
        finding.rule_triggered,
      ]),
    ];
    const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `talend-health-findings-${dashboard.analysis_id ?? "latest"}.csv`;
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
          </div>
        </div>
      </section>
    </div>
  );
}

function DashboardPageContent() {
  const searchParams = useSearchParams();
  const taskId = searchParams.get("taskId");
  const [activeSection, setActiveSection] = useState<DashboardSection>("Dashboard");
  const [sectionQuery, setSectionQuery] = useState("");
  const [completedTask, setCompletedTask] = useState<AnalysisTaskStatus | null>(null);
  const [analysisRunning, setAnalysisRunning] = useState(Boolean(taskId));
  const [dashboard, setDashboard] = useState<DashboardOverview | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const completeAnalysis = useCallback((status?: AnalysisTaskStatus) => {
    if (status) {
      setCompletedTask(status);
    }
    setAnalysisRunning(false);
  }, []);
  const analysisId = completedTask?.analysis_id ?? searchParams.get("analysisId");

  useEffect(() => {
    if (analysisRunning || !analysisId) {
      return;
    }

    let cancelled = false;
    const activeAnalysisId = analysisId;

    async function loadDashboard() {
      try {
        const overview = await getDashboardOverview(activeAnalysisId);
        if (!cancelled) {
          setDashboard(overview);
          setDashboardError(null);
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
  }, [analysisId, analysisRunning]);

  const projectName = dashboard?.summary?.project_name ?? "No dashboard output loaded";
  const complianceScore = dashboard?.summary?.compliance_score;
  const complianceGrade = dashboard?.summary?.compliance_grade;
  const totalJobs = dashboard?.summary?.metrics?.find((m) => m.label === "Total Jobs")?.value ?? 0;
  const totalComponents = dashboard?.summary?.metrics?.find((m) => m.label === "Total Components")?.value ?? 0;
  const disabledComponents = dashboard?.summary?.metrics?.find((m) => m.label === "Disabled Components")?.value ?? 0;
  const criticalIssues =
    dashboard?.summary?.metrics?.find((metric) => metric.label === "Critical Issues")?.value ?? 0;
  const totalFindings =
    (dashboard?.security_findings?.total ?? 0) + (dashboard?.performance_findings?.total ?? 0);
  const securityFindings = dashboard?.security_findings?.items ?? [];
  const performanceFindings = dashboard?.performance_findings?.items ?? [];
  const componentDrilldown = dashboard?.component_drilldown ?? [];
  const securityDrilldown = filterDrilldown(componentDrilldown, securityFindings);
  const performanceDrilldown = filterDrilldown(componentDrilldown, performanceFindings);
  const handleChatAction = useCallback((section: DashboardSection, query?: string) => {
    setSectionQuery(query ?? "");
    setActiveSection(section);
  }, []);

  return (
    <DashboardLayout
      activeSection={activeSection}
      onSectionChange={setActiveSection}
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
              />
              <KpiCard
                title="Active Components"
                value={totalComponents}
                tone="cyan"
                icon={Layers}
                subtitle={`${disabledComponents} disabled`}
                onClick={() => setActiveSection("Components")}
              />
              <KpiCard
                title="Total Findings"
                value={totalFindings}
                tone="violet"
                icon={Bug}
                onClick={() => setActiveSection("Security")}
              />
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
                <SectionHeader
                  eyebrow="Performance"
                  title="Performance findings"
                  description="Focused view of performance findings and optimization recommendations."
                />
                <AnalysisTabs
                  key={`performance-findings-${sectionQuery}`}
                  lockedTab="performance"
                  title="Performance findings"
                  eyebrow="Performance Workspace"
                  initialQuery={sectionQuery}
                  performanceFindings={performanceFindings}
                  recommendations={dashboard?.recommendations?.items}
                  componentDrilldown={performanceDrilldown}
                />
              </>
            ) : null}

            {activeSection === "Components" ? (
              <ComponentsSection dashboard={dashboard} query={sectionQuery} />
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
              <SectionHeader
                eyebrow="Settings"
                title="Dashboard settings"
                description="No configurable dashboard settings are exposed for this workflow."
              />
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

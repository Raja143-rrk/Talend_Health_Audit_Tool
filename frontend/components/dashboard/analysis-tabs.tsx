"use client";

import { useMemo, useState } from "react";
import {
  Archive,
  ArrowDownUp,
  ChevronLeft,
  ChevronRight,
  Component,
  GitBranch,
  Gauge,
  Lightbulb,
  Search,
  ShieldCheck,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  ComponentDrillDown,
  DashboardFinding,
  DashboardRecommendation,
} from "@/lib/dashboard";
import { cn } from "@/lib/utils";

type Severity = "Critical Risk" | "Risk" | "Warning" | "Advisory" | "Informational";
type SortKey =
  | "name"
  | "jobName"
  | "componentName"
  | "componentType"
  | "category"
  | "severity"
  | "ruleTriggered";
type TabKey = "security" | "performance" | "components" | "recommendations";

type AnalysisRow = {
  id: string;
  name: string;
  jobName: string;
  subjobName?: string | null;
  componentName: string;
  componentType: string;
  category: string;
  severity: Severity;
  ruleTriggered: string;
  issueDescription: string;
  recommendation: string;
  evidence: Record<string, unknown>;
};

const tabs = [
  { key: "security", label: "Security", icon: ShieldCheck },
  { key: "performance", label: "Performance", icon: Gauge },
  { key: "components", label: "Components", icon: Component },
  { key: "recommendations", label: "Recommendations", icon: Lightbulb },
] satisfies Array<{ key: TabKey; label: string; icon: typeof ShieldCheck }>;

const severityOrder: Record<Severity, number> = {
  "Critical Risk": 4,
  Risk: 3,
  Warning: 2,
  Advisory: 1,
  Informational: 0,
};

const severityClasses: Record<Severity, string> = {
  "Critical Risk": "border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300",
  Risk: "border-orange-300 bg-orange-50 text-orange-700 dark:border-orange-700 dark:bg-orange-950 dark:text-orange-300",
  Warning: "border-yellow-300 bg-yellow-50 text-yellow-700 dark:border-yellow-700 dark:bg-yellow-950 dark:text-yellow-300",
  Advisory: "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300",
  Informational: "border-gray-300 bg-gray-50 text-gray-600 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-400",
};

const pageSize = 10;

function uniqueValues(values: string[]) {
  return Array.from(new Set(values.filter((value) => value && value !== "unknown")));
}

function compareRows(a: AnalysisRow, b: AnalysisRow, key: SortKey) {
  if (key === "severity") {
    return severityOrder[a.severity] - severityOrder[b.severity];
  }

  return a[key].localeCompare(b[key]);
}

function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={cn(
        "inline-flex min-w-20 items-center justify-center rounded-full border px-2.5 py-1 text-xs font-semibold",
        severityClasses[severity],
      )}
    >
      {severity}
    </span>
  );
}

function normalizeSeverity(value: string): Severity {
  const normalized = value.toLowerCase();
  if (normalized === "critical_risk") return "Critical Risk";
  if (normalized === "risk") return "Risk";
  if (normalized === "warning") return "Warning";
  if (normalized === "advisory") return "Advisory";
  return "Informational";
}

function findingToRow(finding: DashboardFinding): AnalysisRow {
  return {
    id: finding.id,
    name: finding.name,
    jobName: finding.job_name,
    subjobName: finding.subjob_name || undefined,
    componentName: finding.component_name,
    componentType: finding.component_type,
    category: finding.category,
    severity: normalizeSeverity(finding.severity),
    ruleTriggered: finding.rule_triggered,
    issueDescription: finding.impact || finding.recommendation || finding.name,
    recommendation: finding.recommendation,
    evidence: finding.evidence,
  };
}

function recommendationToRow(recommendation: DashboardRecommendation): AnalysisRow {
  return {
    id: recommendation.id,
    name: recommendation.title,
    jobName: recommendation.job_name ?? "unknown",
    componentName: recommendation.component_name ?? "unknown",
    componentType: recommendation.component_type ?? "unknown",
    category: recommendation.category,
    severity: normalizeSeverity(recommendation.severity),
    ruleTriggered: recommendation.rule_triggered ?? "recommendation",
    issueDescription: recommendation.suggestion || recommendation.expected_impact,
    recommendation: recommendation.suggestion,
    evidence: {
      finding_id: recommendation.finding_id,
      expected_impact: recommendation.expected_impact,
    },
  };
}

function componentToRow(component: ComponentDrillDown): AnalysisRow {
  const highestSeverity = component.findings
    .map((finding) => normalizeSeverity(finding.severity))
    .sort((a, b) => severityOrder[b] - severityOrder[a])[0] ?? "Info";
  const rules = component.findings
    .map((finding) => finding.rule_triggered)
    .filter(Boolean);
  const categories = component.findings
    .map((finding) => finding.category)
    .filter(Boolean);

  return {
    id: `${component.job_name}-${component.component_name}-${component.component_type}`,
    name: component.component_name,
    jobName: component.job_name,
    componentName: component.component_name,
    componentType: component.component_type,
    category: Array.from(new Set(categories)).join(", ") || "component",
    severity: highestSeverity,
    ruleTriggered: Array.from(new Set(rules)).join(", ") || "none",
    issueDescription: `${component.findings.length} findings mapped to this component.`,
    recommendation: `${component.recommendations.length} recommendations mapped to this component.`,
    evidence: {
      findings: component.findings.length,
      recommendations: component.recommendations.length,
    },
  };
}

function componentGroups(rows: AnalysisRow[]) {
  const groups = new Map<
    string,
    {
      id: string;
      jobName: string;
      componentName: string;
      componentType: string;
      count: number;
      severities: Severity[];
      rules: string[];
      categories: string[];
      recommendations: string[];
    }
  >();

  rows.forEach((row) => {
    const key = `${row.jobName}|${row.componentName}|${row.componentType}`;
    const group = groups.get(key) ?? {
      id: key,
      jobName: row.jobName,
      componentName: row.componentName,
      componentType: row.componentType,
      count: 0,
      severities: [],
      rules: [],
      categories: [],
      recommendations: [],
    };
    group.count += 1;
    group.severities.push(row.severity);
    group.rules.push(row.ruleTriggered);
    group.categories.push(row.category);
    group.recommendations.push(row.recommendation);
    groups.set(key, group);
  });

  return Array.from(groups.values())
    .filter((group) => group.componentName !== "unknown")
    .sort((a, b) => {
      const aSeverity = Math.max(...a.severities.map((severity) => severityOrder[severity]));
      const bSeverity = Math.max(...b.severities.map((severity) => severityOrder[severity]));
      if (aSeverity !== bSeverity) return bSeverity - aSeverity;
      return b.count - a.count;
    });
}

export function AnalysisTabs({
  securityFindings = [],
  performanceFindings = [],
  recommendations = [],
  componentDrilldown = [],
  initialTab = "security",
  initialQuery = "",
  lockedTab,
  title = "Findings",
  eyebrow = "Analysis Workspace",
}: {
  securityFindings?: DashboardFinding[];
  performanceFindings?: DashboardFinding[];
  recommendations?: DashboardRecommendation[];
  componentDrilldown?: ComponentDrillDown[];
  initialTab?: TabKey;
  initialQuery?: string;
  lockedTab?: TabKey;
  title?: string;
  eyebrow?: string;
}) {
  const [activeTab, setActiveTab] = useState<TabKey>(lockedTab ?? initialTab);
  const [query, setQuery] = useState(initialQuery);
  const [severityFilter, setSeverityFilter] = useState<Severity | "All">("All");
  const [sortKey, setSortKey] = useState<SortKey>("severity");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const analysisData = useMemo<Record<TabKey, AnalysisRow[]>>(
    () => ({
      security: securityFindings.map(findingToRow),
      performance: performanceFindings.map(findingToRow),
      components: componentDrilldown.map(componentToRow),
      recommendations: recommendations.map(recommendationToRow).filter((r) => r.category !== "cleanup"),
    }),
    [componentDrilldown, performanceFindings, recommendations, securityFindings],
  );

  const cleanupRows = useMemo(
    () => recommendations.map(recommendationToRow).filter((r) => r.category === "cleanup"),
    [recommendations],
  );

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return [...analysisData[activeTab]]
      .filter((row) => {
        const matchesQuery =
          !normalizedQuery ||
          [
            row.id,
            row.name,
            row.jobName,
            row.componentName,
            row.componentType,
            row.category,
            row.ruleTriggered,
            row.issueDescription,
            row.recommendation,
          ]
            .join(" ")
            .toLowerCase()
            .includes(normalizedQuery);
        const matchesSeverity =
          severityFilter === "All" || row.severity === severityFilter;

        return matchesQuery && matchesSeverity;
      })
      .sort((a, b) => {
        const result = compareRows(a, b, sortKey);
        return sortDirection === "asc" ? result : -result;
      });
  }, [activeTab, analysisData, query, severityFilter, sortDirection, sortKey]);

  const activeRows = analysisData[activeTab];
  const activeGroups = useMemo(() => componentGroups(filteredRows), [filteredRows]);
  const criticalOrHighCount = filteredRows.filter(
    (row) => row.severity === "Critical Risk" || row.severity === "Risk",
  ).length;
  const uniqueRules = uniqueValues(filteredRows.map((row) => row.ruleTriggered));
  const shouldPaginate = activeTab !== "recommendations";
  const totalPages = shouldPaginate ? Math.max(1, Math.ceil(filteredRows.length / pageSize)) : 1;
  const visibleRows = shouldPaginate
    ? filteredRows.slice((page - 1) * pageSize, page * pageSize)
    : filteredRows;

  const updateSort = (key: SortKey) => {
    setPage(1);
    if (sortKey === key) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortKey(key);
    setSortDirection(key === "severity" ? "desc" : "asc");
  };

  const switchTab = (key: TabKey) => {
    if (lockedTab) {
      return;
    }
    setActiveTab(key);
    setQuery("");
    setSeverityFilter("All");
    setPage(1);
    setSortKey("severity");
    setSortDirection("desc");
  };

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-slate-950">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
            {eyebrow}
          </p>
          <h2 className="mt-2 text-xl font-semibold">{title}</h2>
        </div>

        {!lockedTab ? <div className="flex overflow-x-auto rounded-lg border border-slate-200 bg-slate-50 p-1 dark:border-white/10 dark:bg-white/5">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => switchTab(tab.key)}
                className={cn(
                  "relative flex h-10 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium transition",
                  activeTab === tab.key
                    ? "text-white dark:text-slate-950"
                    : "text-slate-600 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white",
                )}
              >
                {activeTab === tab.key ? (
                  <motion.span
                    layoutId="analysis-active-tab"
                    className="absolute inset-0 rounded-md bg-slate-950 dark:bg-white"
                    transition={{ duration: 0.22 }}
                  />
                ) : null}
                <Icon className="relative h-4 w-4" />
                <span className="relative">{tab.label}</span>
              </button>
            );
          })}
        </div> : null}
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
            placeholder="Search jobs, components, findings, rules"
            className="pl-9"
          />
        </div>

        <select
          value={severityFilter}
          onChange={(event) => {
            setSeverityFilter(event.target.value as Severity | "All");
            setPage(1);
          }}
          className="h-10 rounded-md border border-slate-300 bg-white/80 px-3 text-sm text-slate-950 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 dark:border-white/10 dark:bg-white/5 dark:text-white"
        >
          <option value="All">All severity</option>
          <option value="Critical Risk">Critical Risk</option>
          <option value="Risk">Risk</option>
          <option value="Warning">Warning</option>
          <option value="Advisory">Advisory</option>
          <option value="Informational">Informational</option>
        </select>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        {[
          ["Records", `${filteredRows.length} of ${activeRows.length}`],
          ["Critical Risk / Risk", `${criticalOrHighCount}`],
          ["Unique Rules", `${uniqueRules.length}`],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5"
          >
            <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
              {label}
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-950 dark:text-white">
              {value}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-5 overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-white/10 dark:bg-slate-950">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1280px] border-collapse text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase text-slate-500 dark:bg-white/5 dark:text-slate-400">
              <tr>
                {[
                  ["name", "Finding"],
                  ["jobName", "Job Name"],
                  ["componentName", "Component"],
                  ["componentType", "Type"],
                  ["category", "Category"],
                  ["severity", "Severity"],
                  ...(activeTab !== "security" && activeTab !== "recommendations" ? [["ruleTriggered", "Rule"] as const] : []),
                ].map(([key, label]) => (
                  <th key={key} className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => updateSort(key as SortKey)}
                      className="flex items-center gap-2 font-semibold"
                    >
                      {label}
                      <ArrowDownUp className="h-3.5 w-3.5" />
                    </button>
                  </th>
                ))}
                <th className="px-4 py-3 font-semibold">Issue Description</th>
                <th className="px-4 py-3 font-semibold">Recommendation</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence mode="popLayout">
                {visibleRows.map((row, index) => (
                  <motion.tr
                    key={`${row.id}-${row.jobName}-${row.componentName}-${index}`}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="border-t border-slate-200 transition hover:bg-slate-50 dark:border-white/10 dark:hover:bg-white/5"
                  >
                    <td className="px-4 py-4">
                      <p className="font-semibold text-slate-950 dark:text-white">
                        {row.name}
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {row.id}
                      </p>
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      <div className="flex items-center gap-2">
                        {row.jobName}
                        {row.subjobName ? (
                          <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
                            subjob
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      {row.componentName}
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      {row.componentType}
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      {row.category}
                    </td>
                    <td className="px-4 py-4">
                      <SeverityBadge severity={row.severity} />
                    </td>
                    {activeTab !== "security" && activeTab !== "recommendations" ? (
                      <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                        {row.ruleTriggered}
                      </td>
                    ) : null}
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      <div className="max-w-xs">
                        <p>{row.issueDescription}</p>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      {row.recommendation}
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </div>

      {activeTab === "recommendations" && cleanupRows.length ? (
        <div className="mt-6 overflow-hidden rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-950/20">
          <div className="flex items-center gap-3 border-b border-amber-200 p-5 dark:border-amber-500/30">
            <Archive className="h-5 w-5 text-amber-600 dark:text-amber-300" />
            <div>
              <h3 className="font-semibold text-amber-800 dark:text-amber-200">
                Disabled Component Cleanup ({cleanupRows.length})
              </h3>
              <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                These components are deactivated and can be removed from job designs to reduce technical debt.
              </p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1280px] border-collapse text-left text-sm">
              <thead className="bg-amber-100 text-xs uppercase text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
                <tr>
                  <th className="px-4 py-3 font-semibold">Finding</th>
                  <th className="px-4 py-3 font-semibold">Job Name</th>
                  <th className="px-4 py-3 font-semibold">Component</th>
                  <th className="px-4 py-3 font-semibold">Type</th>
                  <th className="px-4 py-3 font-semibold">Category</th>
                  <th className="px-4 py-3 font-semibold">Severity</th>
                  <th className="px-4 py-3 font-semibold">Rule</th>
                  <th className="px-4 py-3 font-semibold">Evidence</th>
                  <th className="px-4 py-3 font-semibold">Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {cleanupRows.map((row) => (
                  <tr
                    key={row.id}
                    className="border-t border-amber-200 transition hover:bg-amber-100/50 dark:border-amber-500/30 dark:hover:bg-amber-950/30"
                  >
                    <td className="px-4 py-4">
                      <p className="font-semibold text-amber-900 dark:text-amber-100">{row.name}</p>
                      <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">{row.id}</p>
                    </td>
                    <td className="px-4 py-4 text-amber-800 dark:text-amber-200">{row.jobName}</td>
                    <td className="px-4 py-4 text-amber-800 dark:text-amber-200">{row.componentName}</td>
                    <td className="px-4 py-4 text-amber-800 dark:text-amber-200">{row.componentType}</td>
                    <td className="px-4 py-4 text-amber-800 dark:text-amber-200">{row.category}</td>
                    <td className="px-4 py-4">
                      <SeverityBadge severity={row.severity} />
                    </td>
                    <td className="px-4 py-4 text-amber-800 dark:text-amber-200">{row.ruleTriggered}</td>
                    <td className="px-4 py-4 text-amber-800 dark:text-amber-200">{row.issueDescription}</td>
                    <td className="px-4 py-4 text-amber-800 dark:text-amber-200">{row.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {activeTab !== "recommendations" ? <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
        <div className="flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-cyan-600 dark:text-cyan-300" />
          <h3 className="font-semibold">Component drill-down</h3>
        </div>
        <div className="mt-4 grid gap-3">
          {componentDrilldown.length ? (
            componentDrilldown.map((component) => (
              <details
                key={`${component.job_name}-${component.component_name}-${component.component_type}`}
                className="rounded-lg border border-slate-200 bg-white/70 p-4 dark:border-white/10 dark:bg-white/5"
              >
                <summary className="cursor-pointer text-sm font-semibold">
                  {component.component_name} ({component.component_type}) in {component.job_name}
                </summary>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <div className="rounded-md bg-slate-50 p-3 dark:bg-slate-900/60">
                    <p className="text-xs font-semibold uppercase text-slate-500">
                      Findings
                    </p>
                    <p className="mt-2 text-lg font-semibold">
                      {component.findings.length}
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 p-3 dark:bg-slate-900/60">
                    <p className="text-xs font-semibold uppercase text-slate-500">
                      Rules
                    </p>
                    <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                      {uniqueValues(component.findings.map((finding) => finding.rule_triggered)).join(", ") || "None"}
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 p-3 dark:bg-slate-900/60">
                    <p className="text-xs font-semibold uppercase text-slate-500">
                      Recommendations
                    </p>
                    <p className="mt-2 text-lg font-semibold">
                      {uniqueValues(component.recommendations.map((recommendation) => recommendation.suggestion)).length}
                    </p>
                  </div>
                </div>
                <div className="mt-4 rounded-md border border-slate-200 bg-white p-3 text-sm dark:border-white/10 dark:bg-slate-950">
                  <p className="text-xs font-semibold uppercase text-slate-500">
                    Consolidated Remediation
                  </p>
                  <div className="mt-2 space-y-2 text-slate-600 dark:text-slate-300">
                    {uniqueValues(
                      component.recommendations.map((recommendation) => recommendation.suggestion),
                    ).length ? (
                      uniqueValues(
                        component.recommendations.map((recommendation) => recommendation.suggestion),
                      ).map((suggestion) => (
                        <p key={`${component.component_name}-${suggestion}`}>
                          {suggestion}
                        </p>
                      ))
                    ) : (
                      <p>Review mapped findings and apply rule-specific remediation.</p>
                    )}
                  </div>
                </div>
              </details>
            ))
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              No component-level findings are available.
            </p>
          )}
        </div>
      </div> : null}

      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Showing {visibleRows.length} of {filteredRows.length} records
        </p>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <span className="rounded-md border border-slate-200 bg-white/70 px-3 py-2 text-sm dark:border-white/10 dark:bg-white/5">
            Page {page} of {totalPages}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={page === totalPages}
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </section>
  );
}

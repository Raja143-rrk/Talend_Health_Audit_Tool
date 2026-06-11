"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { cn } from "@/lib/utils";
import type { DashboardChartPoint } from "@/lib/dashboard";

const chartColors = ["#06b6d4", "#2563eb", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444", "#ec4899"];

type ChartCardProps = {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
  onClick?: () => void;
};

function ChartCard({ title, description, children, className, onClick }: ChartCardProps) {
  return (
    <motion.article
      className={cn(
        "relative overflow-hidden rounded-2xl border bg-white/80 p-5 shadow-lg backdrop-blur-xl transition-all",
        "dark:border-white/10 dark:bg-slate-950/80",
        className,
        onClick && "cursor-pointer",
      )}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.18 }}
      onClick={onClick}
    >
      <div className="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-gradient-to-br from-white/30 to-transparent blur-3xl dark:from-white/5" />
      <div className="relative">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {title}
          </p>
          {description ? (
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {description}
            </p>
          ) : null}
        </div>
        <div className="h-72 min-w-0">{children}</div>
      </div>
    </motion.article>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number; color?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="rounded-xl border border-slate-200/60 bg-white/90 px-4 py-2.5 text-sm shadow-xl backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/90">
      {label ? <p className="mb-1.5 font-semibold">{label}</p> : null}
      <div className="space-y-1">
        {payload.map((entry) => (
          <div key={`${entry.name}-${entry.value}`} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-slate-600 dark:text-slate-300">
              {entry.name}: {entry.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyChartState() {
  return (
    <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white/50 text-sm text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-400">
      No data available for this chart.
    </div>
  );
}

export function ComponentDistributionChart({
  data,
  onClick,
}: {
  data: DashboardChartPoint[];
  onClick?: () => void;
}) {
  if (!data.length) {
    return (
      <ChartCard title="Component Distribution" description="Active components by type." onClick={onClick}>
        <EmptyChartState />
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Component Distribution" description="Active components by type." onClick={onClick}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={62}
            outerRadius={94}
            paddingAngle={3}
            animationDuration={800}
          >
            {data.map((entry, index) => (
              <Cell
                key={entry.name}
                fill={chartColors[index % chartColors.length]}
              />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
          <Legend iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function RiskSeverityDonutChart({
  data,
}: {
  data: DashboardChartPoint[];
}) {
  if (!data.length) {
    return (
      <ChartCard title="Risk Severity" description="Findings by severity level.">
        <EmptyChartState />
      </ChartCard>
    );
  }

  const severityColors: Record<string, string> = {
    critical_risk: "#ef4444",
    risk: "#f59e0b",
    warning: "#eab308",
    advisory: "#3b82f6",
    informational: "#10b981",
  };

  return (
    <ChartCard title="Risk Severity" description="Findings by severity level.">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={50}
            outerRadius={90}
            paddingAngle={2}
            animationDuration={800}
          >
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={severityColors[entry.name?.toLowerCase()] ?? chartColors[0]}
              />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
          <Legend iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function SourceTargetFlowDiagram({
  data,
}: {
  data: DashboardChartPoint[];
}) {
  if (!data.length) {
    return (
      <ChartCard title="Source vs Target Systems" description="System connectivity flow.">
        <EmptyChartState />
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Source vs Target Systems" description="System connectivity flow.">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="flowSourceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.03} />
            </linearGradient>
            <linearGradient id="flowTargetFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip content={<ChartTooltip />} />
          <Legend />
          <Area
            type="monotone"
            dataKey="source"
            stroke="#06b6d4"
            fill="url(#flowSourceFill)"
            strokeWidth={2.5}
          />
          <Area
            type="monotone"
            dataKey="target"
            stroke="#10b981"
            fill="url(#flowTargetFill)"
            strokeWidth={2.5}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function FindingsTrendTimeline({
  data,
}: {
  data: DashboardChartPoint[];
}) {
  if (!data.length) {
    return (
      <ChartCard title="Findings Trend" description="Findings by category.">
        <EmptyChartState />
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Findings Trend" description="Findings by category.">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12 }} />
          <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} width={120} />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} animationDuration={800}>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={chartColors[index % chartColors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function AIInsightsPanel({
  summary,
}: {
  summary?: {
    project_name?: string;
    compliance_score?: number;
    compliance_grade?: string;
    critical_issues?: number;
    total_findings?: number;
    total_jobs?: number;
    total_components?: number;
    disabled_components?: number;
  };
}) {
  return (
    <motion.article
      className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-violet-500/10 via-fuchsia-500/5 to-cyan-500/10 p-5 shadow-lg backdrop-blur-xl dark:border-white/10 dark:from-violet-500/5 dark:via-fuchsia-500/2 dark:to-cyan-500/5"
      whileHover={{ y: -2 }}
      transition={{ duration: 0.18 }}
    >
      <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br from-violet-500/20 to-cyan-500/20 blur-3xl" />
      <div className="relative">
        <p className="text-xs font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-300">
          AI Insights
        </p>
        <h2 className="mt-2 text-xl font-semibold text-slate-950 dark:text-white">
          {summary?.project_name ?? "Audit Overview"}
        </h2>
        <div className="mt-4 space-y-3">
          {summary ? (
            <>
              <div className="flex items-center justify-between rounded-xl border border-white/60 bg-white/60 px-4 py-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                <span className="text-sm text-slate-600 dark:text-slate-300">Compliance Score</span>
                <span className="text-lg font-bold text-slate-950 dark:text-white">{summary.compliance_score ?? "--"}%</span>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-white/60 bg-white/60 px-4 py-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                <span className="text-sm text-slate-600 dark:text-slate-300">Grade</span>
                <span className="text-lg font-bold text-slate-950 dark:text-white">{summary.compliance_grade ?? "--"}</span>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-white/60 bg-white/60 px-4 py-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                <span className="text-sm text-slate-600 dark:text-slate-300">Critical Issues</span>
                <span className="text-lg font-bold text-red-600 dark:text-red-400">{summary.critical_issues ?? 0}</span>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-white/60 bg-white/60 px-4 py-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                <span className="text-sm text-slate-600 dark:text-slate-300">Total Findings</span>
                <span className="text-lg font-bold text-slate-950 dark:text-white">{summary.total_findings ?? 0}</span>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-white/60 bg-white/60 px-4 py-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                <span className="text-sm text-slate-600 dark:text-slate-300">Jobs / Active Components</span>
                <span className="text-lg font-bold text-slate-950 dark:text-white">{summary.total_jobs ?? 0} / {summary.total_components ?? 0}</span>
              </div>
              {summary.disabled_components ? (
                <div className="flex items-center justify-between rounded-xl border border-amber-200/80 bg-amber-50/80 px-4 py-3 backdrop-blur-sm dark:border-amber-500/20 dark:bg-amber-500/5">
                  <span className="text-sm text-amber-700 dark:text-amber-300">Disabled Components</span>
                  <span className="text-lg font-bold text-amber-700 dark:text-amber-300">{summary.disabled_components}</span>
                </div>
              ) : null}
            </>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white/50 px-4 py-8 text-center text-sm text-slate-500 backdrop-blur-sm dark:border-white/10 dark:bg-white/5 dark:text-slate-400">
              Load an analysis to see insights.
            </div>
          )}
        </div>
      </div>
    </motion.article>
  );
}

export function AnalyticsChartGrid({
  charts,
  insightsSummary,
  onNavigate,
}: {
  charts?: {
    component_distribution: DashboardChartPoint[];
    active_component_distribution: DashboardChartPoint[];
    disabled_component_distribution: DashboardChartPoint[];
    performance_issues: DashboardChartPoint[];
    security_issues: DashboardChartPoint[];
    source_target_systems: DashboardChartPoint[];
    risk_timeline: DashboardChartPoint[];
  };
  insightsSummary?: {
    project_name?: string;
    compliance_score?: number;
    compliance_grade?: string;
    critical_issues?: number;
    total_findings?: number;
    total_jobs?: number;
    total_components?: number;
    disabled_components?: number;
  };
  onNavigate?: (section: "Components" | "Security") => void;
}) {
  const empty: DashboardChartPoint[] = [];

  const severityData = (() => {
    const counts: Record<string, number> = {};
    const securityIssues = charts?.security_issues ?? [];
    const performanceIssues = charts?.performance_issues ?? [];
    const keys = ["critical_risk", "risk", "warning", "advisory"] as const;
    for (const item of [...securityIssues, ...performanceIssues]) {
      for (const key of keys) {
        const val = item[key];
        if (typeof val === "number" && val > 0) {
          counts[key] = (counts[key] ?? 0) + val;
        }
      }
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  })();

  const findingsTrendData = (() => {
    const securityItems = charts?.security_issues ?? [];
    const performanceItems = charts?.performance_issues ?? [];
    const categories: Record<string, number> = {};
    for (const item of [...securityItems, ...performanceItems]) {
      const name = item.name || "Other";
      const total = (item.critical_risk ?? 0) + (item.risk ?? 0) + (item.warning ?? 0) + (item.advisory ?? 0) +
        (item.runtime ?? 0) + (item.memory ?? 0) + (item.retries ?? 0);
      if (total > 0) {
        categories[name] = (categories[name] ?? 0) + total;
      }
    }
    return Object.entries(categories).map(([name, value]) => ({ name, value }));
  })();

  return (
    <section className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-2">
        <RiskSeverityDonutChart data={severityData} />
        <ComponentDistributionChart data={charts?.active_component_distribution ?? empty} onClick={() => onNavigate?.("Components")} />
      </div>
      <div className="grid gap-6 xl:grid-cols-3">
        <SourceTargetFlowDiagram data={charts?.source_target_systems ?? empty} />
        <FindingsTrendTimeline data={findingsTrendData} />
        <AIInsightsPanel summary={insightsSummary} />
      </div>
    </section>
  );
}

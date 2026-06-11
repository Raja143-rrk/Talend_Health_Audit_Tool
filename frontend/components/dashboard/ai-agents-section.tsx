"use client";

import {
  Bot,
  CheckCircle2,
  Clock,
  FileJson,
  Gauge,
  LayoutDashboard,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentInfo } from "@/lib/dashboard";

const agentIcons: Record<string, typeof Bot> = {
  "parser-agent": FileJson,
  "security-agent": ShieldCheck,
  "performance-agent": Gauge,
  "recommendation-agent": Sparkles,
  "dashboard-agent": LayoutDashboard,
};

function statusIcon(status: string) {
  switch (status) {
    case "completed":
      return CheckCircle2;
    case "failed":
      return XCircle;
    default:
      return Clock;
  }
}

function statusLabel(status: string) {
  switch (status) {
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "running":
      return "Running";
    case "retrying":
      return "Retrying";
    default:
      return "Pending";
  }
}

function formatDuration(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const seconds = (ms / 1000).toFixed(1);
  return `${seconds}s`;
}

type AiAgentsSectionProps = {
  agents: AgentInfo[];
};

export function AiAgentsSection({ agents }: AiAgentsSectionProps) {
  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-slate-950">
        <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
          AI Agents
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950 dark:text-white">
          Pipeline agents
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          Overview of the AI agents that processed this analysis and their execution status.
        </p>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {agents.map((agent) => {
          const Icon = agentIcons[agent.name] ?? Bot;
          const StatusIcon = statusIcon(agent.status);
          const isError = agent.status === "failed";
          const isCompleted = agent.status === "completed";

          return (
            <div
              key={agent.name}
              className={cn(
                "group relative overflow-hidden rounded-xl border p-5 transition-shadow hover:shadow-md",
                isError
                  ? "border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-950/20"
                  : "border-slate-200 bg-white dark:border-white/10 dark:bg-white/5",
              )}
            >
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                    isError
                      ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
                      : isCompleted
                        ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
                        : "bg-slate-100 text-slate-500 dark:bg-white/10 dark:text-slate-400",
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-slate-950 dark:text-white">
                      {agent.label}
                    </h3>
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                        isError
                          ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                          : isCompleted
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                            : "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-400",
                      )}
                    >
                      <StatusIcon className="h-3 w-3" />
                      {statusLabel(agent.status)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
                    {agent.description}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex items-center gap-4 border-t border-slate-100 pt-4 text-xs text-slate-500 dark:border-white/5 dark:text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {formatDuration(agent.duration_ms)}
                </span>
                <span
                  className={cn(
                    "flex items-center gap-1",
                    agent.findings_count > 0 && "font-medium text-slate-700 dark:text-slate-300",
                  )}
                >
                  <Bot className="h-3.5 w-3.5" />
                  {agent.findings_count} finding{agent.findings_count !== 1 ? "s" : ""}
                </span>
              </div>

              {agent.errors.length > 0 ? (
                <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-900/50 dark:bg-red-950/30">
                  <p className="text-xs font-medium text-red-700 dark:text-red-400">Errors</p>
                  <ul className="mt-1 space-y-1">
                    {agent.errors.map((error, i) => (
                      <li key={i} className="text-xs text-red-600 dark:text-red-300">
                        {error}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

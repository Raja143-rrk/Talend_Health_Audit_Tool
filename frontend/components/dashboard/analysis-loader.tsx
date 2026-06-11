"use client";

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Loader2, Radar } from "lucide-react";
import { motion } from "framer-motion";

import { getTaskStatus, type AnalysisTaskStatus } from "@/lib/tasks";

const statusLogs = [
  "Reading Talend archive structure",
  "Indexing jobs and shared components",
  "Scanning context variables and credentials",
  "Measuring execution path complexity",
  "Generating health score and recommendations",
];

type AnalysisLoaderProps = {
  taskId?: string | null;
  onComplete: (status?: AnalysisTaskStatus) => void;
};

export function AnalysisLoader({ taskId, onComplete }: AnalysisLoaderProps) {
  const [progress, setProgress] = useState(0);
  const [taskStatus, setTaskStatus] = useState<AnalysisTaskStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeLogIndex = Math.min(
    statusLogs.length - 1,
    Math.floor((progress / 100) * statusLogs.length),
  );
  const visibleLogs = useMemo(
    () =>
      taskStatus?.logs.length
        ? taskStatus.logs.map((log) => log.message).slice(-6)
        : statusLogs.slice(0, activeLogIndex + 1),
    [activeLogIndex, taskStatus],
  );

  useEffect(() => {
    if (taskId) {
      return;
    }

    const interval = window.setInterval(() => {
      setProgress((current) => {
        const next = Math.min(current + 4, 100);
        if (next === 100) {
          window.clearInterval(interval);
          window.setTimeout(onComplete, 650);
        }
        return next;
      });
    }, 120);

    return () => window.clearInterval(interval);
  }, [onComplete, taskId]);

  useEffect(() => {
    if (!taskId) {
      return;
    }

    let cancelled = false;

    const poll = async () => {
      try {
        const nextStatus = await getTaskStatus(taskId);
        if (cancelled) {
          return;
        }
        setTaskStatus(nextStatus);
        setProgress(nextStatus.progress);

        if (["completed", "partial", "failed"].includes(nextStatus.status)) {
          window.setTimeout(() => onComplete(nextStatus), 500);
          return;
        }

        window.setTimeout(poll, 1500);
      } catch (taskError) {
        if (!cancelled) {
          setError(
            taskError instanceof Error
              ? taskError.message
              : "Unable to load task status.",
          );
          window.setTimeout(poll, 3000);
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
    };
  }, [onComplete, taskId]);

  return (
    <motion.div
      className="flex min-h-[calc(100vh-7rem)] items-center justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.35 }}
    >
      <div className="w-full max-w-3xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-slate-950 sm:p-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <div className="relative flex h-28 w-28 shrink-0 items-center justify-center">
            <motion.div
              className="absolute inset-0 rounded-full border border-cyan-300/60"
              animate={{ rotate: 360 }}
              transition={{ duration: 2.4, repeat: Infinity, ease: "linear" }}
            />
            <motion.div
              className="absolute inset-3 rounded-full border border-dashed border-emerald-300/70"
              animate={{ rotate: -360 }}
              transition={{ duration: 3.2, repeat: Infinity, ease: "linear" }}
            />
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-950 text-white dark:bg-white dark:text-slate-950">
              <Radar className="h-7 w-7" />
            </div>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-cyan-700 dark:text-cyan-300">
              <Loader2 className="h-4 w-4 animate-spin" />
            <p className="text-xs font-semibold uppercase">Analysis Running</p>
            </div>
            <h1 className="mt-3 text-3xl font-semibold text-slate-950 dark:text-white">
              {taskStatus?.current_agent
                ? `Running ${taskStatus.current_agent}`
                : "Processing health audit"}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {taskId
                ? `Task ${taskId} is ${taskStatus?.status ?? "queued"}.`
                : "Validating package and generating dashboard output."}
            </p>
          </div>
        </div>

        <div className="mt-8">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-slate-600 dark:text-slate-300">
              Audit progress
            </span>
            <span className="text-lg font-semibold text-slate-950 dark:text-white">
              {progress}%
            </span>
          </div>
          <div className="mt-3 h-3 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-blue-500 to-emerald-400"
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.18 }}
            />
          </div>
        </div>

        {error ? (
          <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200">
            {error}
          </div>
        ) : null}

        <div className="mt-8 rounded-lg border border-slate-200 bg-slate-950 p-4 text-sm text-slate-200 dark:border-white/10">
          <p className="text-xs font-semibold uppercase text-slate-400">
            Status Logs
          </p>
          <div className="mt-4 space-y-3">
            {visibleLogs.map((log, index) => (
              <motion.div
                key={`${log}-${index}`}
                className="flex items-center gap-3"
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
              >
                <CheckCircle2
                  className={
                    index < activeLogIndex || progress === 100
                      ? "h-4 w-4 text-emerald-300"
                      : "h-4 w-4 text-cyan-300"
                  }
                />
                <span>{log}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

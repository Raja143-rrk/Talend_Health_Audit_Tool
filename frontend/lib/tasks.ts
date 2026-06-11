import { appConfig } from "@/lib/config";

export type AnalysisTaskLog = {
  timestamp: string;
  level: string;
  message: string;
  agent?: string | null;
};

export type AnalysisTaskStatus = {
  task_id: string;
  analysis_id: string;
  status: "queued" | "running" | "completed" | "partial" | "failed";
  progress: number;
  current_agent?: string | null;
  active_agents: string[];
  created_at: string;
  started_at?: string | null;
  updated_at: string;
  completed_at?: string | null;
  logs: AnalysisTaskLog[];
  errors: string[];
  status_url: string;
  dashboard_url: string;
};

export async function getTaskStatus(taskId: string): Promise<AnalysisTaskStatus> {
  const response = await fetch(
    `${appConfig.apiBaseUrl.replace(/\/$/, "")}/tasks/${encodeURIComponent(taskId)}/status`,
    { cache: "no-store" },
  );

  if (!response.ok) {
    throw new Error(`Task status request failed with status ${response.status}.`);
  }

  return (await response.json()) as AnalysisTaskStatus;
}

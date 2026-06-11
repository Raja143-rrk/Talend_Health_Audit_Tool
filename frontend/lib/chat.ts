import { appConfig } from "@/lib/config";

export type ChatRole = "user" | "assistant";

export type DashboardChatMessage = {
  role: ChatRole;
  content: string;
};

export type DashboardChatAction = {
  type: "navigate" | "filter" | "open_component";
  label: string;
  target: string;
  filters: Record<string, unknown>;
};

export type DashboardChatSource = {
  title: string;
  source: string;
  snippet: string;
};

export type DashboardChatResponse = {
  analysis_id: string;
  answer: string;
  actions: DashboardChatAction[];
  sources: DashboardChatSource[];
  matched_counts: Record<string, number>;
};

export async function askDashboardChat({
  analysisId,
  message,
  history,
}: {
  analysisId: string;
  message: string;
  history: DashboardChatMessage[];
}): Promise<DashboardChatResponse> {
  const response = await fetch(
    `${appConfig.apiBaseUrl.replace(/\/$/, "")}/chat/dashboard`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis_id: analysisId,
        message,
        history,
      }),
    },
  );

  if (!response.ok) {
    throw new Error(`Chat request failed with status ${response.status}.`);
  }

  return (await response.json()) as DashboardChatResponse;
}

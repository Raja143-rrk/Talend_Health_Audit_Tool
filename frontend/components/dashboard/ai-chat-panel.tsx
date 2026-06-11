"use client";

import { FormEvent, useMemo, useState } from "react";
import { Bot, Loader2, Send, Sparkles, UserCircle } from "lucide-react";

import {
  askDashboardChat,
  type DashboardChatAction,
  type DashboardChatMessage,
  type DashboardChatSource,
} from "@/lib/chat";
import type { DashboardSection } from "@/components/dashboard/dashboard-layout";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ChatTurn = DashboardChatMessage & {
  id: string;
  actions?: DashboardChatAction[];
  sources?: DashboardChatSource[];
  matchedCounts?: Record<string, number>;
};

const starters = [
  "Explain the health score",
  "Summarize project risks",
  "Show critical security findings",
  "What recommendations should we prioritize?",
  "Show component details for the highest risk component",
];

export function AiChatPanel({
  analysisId,
  onAction,
}: {
  analysisId?: string | null;
  onAction: (section: DashboardSection, query?: string) => void;
}) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const history = useMemo<DashboardChatMessage[]>(
    () => turns.map(({ role, content }) => ({ role, content })).slice(-10),
    [turns],
  );

  async function submitMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || !analysisId || loading) {
      return;
    }

    const userTurn: ChatTurn = {
      id: `user-${turns.length + 1}`,
      role: "user",
      content: trimmed,
    };
    setTurns((current) => [...current, userTurn]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await askDashboardChat({
        analysisId,
        message: trimmed,
        history,
      });
      setTurns((current) => [
        ...current,
        {
          id: `assistant-${current.length + 1}`,
          role: "assistant",
          content: response.answer,
          actions: response.actions,
          sources: response.sources,
          matchedCounts: response.matched_counts,
        },
      ]);
    } catch (chatError) {
      setError(
        chatError instanceof Error
          ? chatError.message
          : "Unable to process chat request.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(input);
  }

  function applyAction(action: DashboardChatAction) {
    const section = action.target as DashboardSection;
    const queryValue =
      typeof action.filters.query === "string"
        ? action.filters.query
        : typeof action.filters.component_name === "string"
          ? action.filters.component_name
          : undefined;
    onAction(section, queryValue);
  }

  return (
    <section className="flex flex-1 min-h-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-slate-950">
      <div className="shrink-0 border-b border-slate-200 bg-slate-950 p-6 text-white dark:border-white/10">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-semibold uppercase text-cyan-200">
              <Sparkles className="h-4 w-4" />
              AI Chat Agent
            </p>
            <h1 className="mt-2 text-3xl font-semibold">Ask your Talend audit data</h1>
          </div>
        </div>
      </div>

        <div className="flex flex-1 min-h-0 flex-col">
          <div className="flex-1 min-h-0 space-y-4 overflow-y-auto p-5">
            {!analysisId ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200">
                Load or complete an analysis before using chat. The chat agent does not answer without real dashboard data.
              </div>
            ) : null}

            {turns.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 dark:border-white/10 dark:bg-white/5">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-cyan-600 text-white">
                    <Bot className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="font-semibold">Context-aware dashboard assistant</h2>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      Ask about findings, scores, filters, components, risks, and recommendations.
                    </p>
                  </div>
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  {starters.map((starter) => (
                    <button
                      key={starter}
                      type="button"
                      disabled={!analysisId || loading}
                      onClick={() => void submitMessage(starter)}
                      className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-cyan-300 hover:text-cyan-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/10 dark:bg-slate-950 dark:text-slate-200 dark:hover:text-cyan-200"
                    >
                      {starter}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {turns.map((turn) => (
              <div
                key={turn.id}
                className={cn(
                  "flex gap-3",
                  turn.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                {turn.role === "assistant" ? (
                  <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-cyan-600 text-white">
                    <Bot className="h-4 w-4" />
                  </div>
                ) : null}
                <div
                  className={cn(
                    "max-w-3xl rounded-lg border px-4 py-3 text-sm leading-6 shadow-sm",
                    turn.role === "user"
                      ? "border-slate-900 bg-slate-950 text-white dark:border-white dark:bg-white dark:text-slate-950"
                      : "border-slate-200 bg-white text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200",
                  )}
                >
                  <div className="whitespace-pre-wrap">{turn.content}</div>

                  {turn.actions?.length ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {turn.actions.map((action) => (
                        <button
                          key={`${turn.id}-${action.label}`}
                          type="button"
                          onClick={() => applyAction(action)}
                          className="rounded-md border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-xs font-semibold text-cyan-800 transition hover:bg-cyan-100 dark:border-cyan-400/20 dark:bg-cyan-400/10 dark:text-cyan-200"
                        >
                          {action.label}
                        </button>
                      ))}
                    </div>
                  ) : null}

                  {turn.sources?.length ? (
                    <details className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-slate-950">
                      <summary className="cursor-pointer text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                        RAG sources
                      </summary>
                      <div className="mt-3 space-y-3">
                        {turn.sources.map((source) => (
                          <div key={`${turn.id}-${source.title}`}>
                            <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                              {source.source} / {source.title}
                            </p>
                            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                              {source.snippet}
                            </p>
                          </div>
                        ))}
                      </div>
                    </details>
                  ) : null}
                </div>
                {turn.role === "user" ? (
                  <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-slate-700 dark:bg-white/10 dark:text-slate-200">
                    <UserCircle className="h-5 w-5" />
                  </div>
                ) : null}
              </div>
            ))}

            {loading ? (
              <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin" />
                Reading dashboard data and RAG context...
              </div>
            ) : null}

            {error ? (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200">
                {error}
              </div>
            ) : null}
          </div>

          <form onSubmit={handleSubmit} className="border-t border-slate-200 p-4 dark:border-white/10">
            <div className="flex gap-3">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                disabled={!analysisId || loading}
                placeholder="Ask about scores, findings, filters, components, recommendations..."
                className="h-11 min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-4 text-sm outline-none transition focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-white/5 dark:text-white"
              />
              <Button type="submit" disabled={!analysisId || loading || !input.trim()}>
                <Send className="h-4 w-4" />
                Send
              </Button>
            </div>
          </form>
        </div>
    </section>
  );
}

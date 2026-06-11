import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-screen bg-slate-100 text-slate-950 dark:bg-slate-950 dark:text-white">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between border-b border-slate-200 pb-4 dark:border-white/10">
          <div>
            <p className="text-2xl font-bold text-slate-950 dark:text-white tracking-tight">
              Talend Health Analyzer
            </p>
          </div>
          <div className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-slate-200">
            Audit Platform
          </div>
        </div>
        {children}
      </div>
    </main>
  );
}

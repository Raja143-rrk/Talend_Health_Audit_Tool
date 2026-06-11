import { AppShell } from "@/components/layout/app-shell";
import { ZipUploadPanel } from "@/components/upload/zip-upload-panel";

export default function UploadPage() {
  return (
    <AppShell>
      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.7fr)]">
        <ZipUploadPanel />

        <aside className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-slate-950">
          <div className="border-b border-slate-200 px-5 py-4 dark:border-white/10">
            <p className="text-sm font-semibold text-slate-950 dark:text-white">Intake Policy</p>
          </div>
          <div className="divide-y divide-slate-200 text-sm dark:divide-white/10">
            <div className="px-5 py-4">
              <p className="font-medium text-slate-900 dark:text-slate-100">Archive Type</p>
              <p className="mt-1 text-slate-600 dark:text-slate-400">ZIP only</p>
            </div>
            <div className="px-5 py-4">
              <p className="font-medium text-slate-900 dark:text-slate-100">Processing</p>
              <p className="mt-1 text-slate-600 dark:text-slate-400">Queued analysis workflow</p>
            </div>
            <div className="px-5 py-4">
              <p className="font-medium text-slate-900 dark:text-slate-100">Output</p>
              <p className="mt-1 text-slate-600 dark:text-slate-400">Dashboard and findings</p>
            </div>
          </div>
        </aside>
      </section>
    </AppShell>
  );
}

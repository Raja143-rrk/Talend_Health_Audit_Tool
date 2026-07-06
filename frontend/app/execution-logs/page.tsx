"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FileIcon, UploadCloud, X } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import {
  fetchProjects,
  fetchUploadHistory,
  uploadExecutionLog,
  type ExecutionLogHistoryItem,
  type ProjectInfo,
} from "@/lib/execution-logs";

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

const ALLOWED_EXTENSIONS = [".zip", ".log", ".csv"];

function validateFile(file: File) {
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `Unsupported file type "${ext}". Allowed: ${ALLOWED_EXTENSIONS.join(", ")}.`;
  }
  return null;
}

export default function ExecutionLogsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [selectedProjectName, setSelectedProjectName] = useState<string>("");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [history, setHistory] = useState<ExecutionLogHistoryItem[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(true);

  const loadProjects = useCallback(async () => {
    setProjectsLoading(true);
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch {
      setError("Failed to load projects. Ensure an analysis has been run.");
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await fetchUploadHistory();
      setHistory(data);
    } catch {
      // silently fail
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
    loadHistory();
  }, [loadProjects, loadHistory]);

  const handleProjectChange = (value: string) => {
    setSelectedProject(value);
    const project = projects.find((p) => p.analysis_id === value);
    setSelectedProjectName(project?.project_name ?? "");
    setError(null);
    setSuccessMessage(null);
  };

  const selectFiles = (nextFiles: FileList | null) => {
    setProgress(0);
    setSuccessMessage(null);
    if (!nextFiles || nextFiles.length === 0) {
      setFiles([]);
      setError(null);
      return;
    }
    const validFiles: File[] = [];
    for (const f of Array.from(nextFiles)) {
      const validationError = validateFile(f);
      if (validationError) {
        setFiles([]);
        setError(validationError);
        return;
      }
      validFiles.push(f);
    }
    setFiles(validFiles);
    setError(null);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const submitUpload = async () => {
    if (files.length === 0 || isUploading) return;
    if (!selectedProject) {
      setError("Select a project before uploading.");
      return;
    }
    setIsUploading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await uploadExecutionLog(selectedProject, selectedProjectName, files[0], setProgress);
      const name = files[0].name;
      setSuccessMessage(`${name} uploaded successfully.`);
      setFiles([]);
      await loadHistory();
    } catch (uploadError) {
      setProgress(0);
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Upload failed. Check the API service and try again.",
      );
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-slate-950">
          <div className="border-b border-slate-200 px-6 py-5 dark:border-white/10">
            <h1 className="text-lg font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Execution Logs
            </h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Upload execution log files (.zip, .log, .csv) associated with a project.
            </p>
          </div>

          <div className="p-6 space-y-6">
            <div>
              <label
                htmlFor="project-select"
                className="mb-2 block text-sm font-semibold text-slate-950 dark:text-white"
              >
                Project
              </label>
              <select
                id="project-select"
                value={selectedProject}
                onChange={(e) => handleProjectChange(e.target.value)}
                className="flex h-10 w-full max-w-md rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/15 dark:border-white/10 dark:bg-slate-950 dark:text-white"
              >
                <option value="">{projectsLoading ? "Loading projects..." : "Select a project"}</option>
                {projects.map((p) => (
                  <option key={p.analysis_id} value={p.analysis_id}>
                    {p.project_name}
                  </option>
                ))}
              </select>
            </div>

            <input
              ref={inputRef}
              type="file"
              accept=".zip,.log,.csv"
              className="sr-only"
              onChange={(event) => selectFiles(event.target.files)}
            />

            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              onDragEnter={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setIsDragging(false);
                selectFiles(event.dataTransfer.files);
              }}
              className={`flex min-h-48 w-full flex-col items-center justify-center rounded-lg border border-dashed px-6 text-center transition ${
                isDragging
                  ? "border-cyan-600 bg-cyan-50 dark:border-cyan-300 dark:bg-cyan-400/10"
                  : "border-slate-300 bg-slate-50 hover:border-cyan-600 hover:bg-cyan-50 dark:border-white/10 dark:bg-white/5 dark:hover:border-cyan-300 dark:hover:bg-cyan-400/10"
              }`}
            >
              <span className="flex h-14 w-14 items-center justify-center rounded-lg border border-cyan-200 bg-white text-cyan-700 shadow-sm dark:border-cyan-400/20 dark:bg-slate-950 dark:text-cyan-200">
                <UploadCloud className="h-7 w-7" />
              </span>
              <span className="mt-5 text-base font-semibold text-slate-950 dark:text-white">
                Drop execution logs here
              </span>
              <span className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                or select files from your machine &mdash; .zip, .log, .csv
              </span>
            </button>

            {files.length > 0 ? (
              <div className="space-y-3">
                {files.map((f, index) => (
                  <div
                    key={index}
                    className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5"
                  >
                    <div className="flex items-center gap-3">
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 dark:border-white/10 dark:bg-slate-950 dark:text-slate-300">
                        <FileIcon className="h-5 w-5" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-slate-950 dark:text-white">
                          {f.name}
                        </p>
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                          {formatFileSize(f.size)}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        disabled={isUploading}
                        className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-white/5 dark:text-slate-100"
                      >
                        <X className="h-4 w-4" />
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}

            <div>
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-slate-700 dark:text-slate-300">
                  Upload progress
                </span>
                <span className="font-semibold text-slate-950 dark:text-white">{progress}%</span>
              </div>
              <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
                <div
                  className="h-full rounded-full bg-cyan-600 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {error ? (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200">
                {error}
              </div>
            ) : null}

            {successMessage ? (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-200">
                {successMessage}
              </div>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
              <button
                type="button"
                onClick={() => setFiles([])}
                disabled={isUploading || files.length === 0}
                className="rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-white/5 dark:text-slate-100"
              >
                Clear
              </button>
              <button
                type="button"
                onClick={submitUpload}
                disabled={files.length === 0 || isUploading || !selectedProject}
                className="rounded-md bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
              >
                {isUploading ? "Uploading..." : "Upload"}
              </button>
            </div>
          </div>
        </section>

        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-slate-950">
          <div className="border-b border-slate-200 px-6 py-5 dark:border-white/10">
            <h1 className="text-lg font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Upload History
            </h1>
          </div>

          {historyLoading ? (
            <div className="p-6 text-center text-sm text-slate-500">Loading history...</div>
          ) : history.length === 0 ? (
            <div className="p-6 text-center text-sm text-slate-500">
              No execution logs uploaded yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[650px] text-left text-sm">
                <thead className="bg-slate-100 text-xs uppercase text-slate-500 dark:bg-white/5 dark:text-slate-400">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Project Name</th>
                    <th className="px-4 py-3 font-semibold">File Name</th>
                    <th className="px-4 py-3 font-semibold">Upload Date</th>
                    <th className="px-4 py-3 font-semibold">Processing Status</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr
                      key={item.id}
                      className="border-t border-slate-200 dark:border-white/10"
                    >
                      <td className="px-4 py-4 font-semibold">{item.project_name}</td>
                      <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                        {item.original_filename}
                      </td>
                      <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                        {formatDate(item.upload_date)}
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={`inline-block rounded-md px-2.5 py-0.5 text-xs font-semibold ${
                            item.processing_status === "completed"
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400"
                              : item.processing_status === "failed"
                                ? "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-400"
                                : "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400"
                          }`}
                        >
                          {item.processing_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}

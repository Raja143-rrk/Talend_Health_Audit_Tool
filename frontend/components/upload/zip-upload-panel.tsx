"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileArchive, UploadCloud, X } from "lucide-react";

import { uploadZipAndAnalyze } from "@/lib/upload";

const ZIP_MIME_TYPES = new Set([
  "application/zip",
  "application/x-zip-compressed",
  "multipart/x-zip",
  "application/octet-stream",
  "",
]);

function formatFileSize(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function validateZip(file: File) {
  if (!file.name.toLowerCase().endsWith(".zip")) {
    return "Select a .zip archive.";
  }

  if (!ZIP_MIME_TYPES.has(file.type)) {
    return "The selected file type is not recognized as a ZIP archive.";
  }

  return null;
}

export function ZipUploadPanel() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const selectFile = (nextFile: File | null) => {
    setProgress(0);
    setSuccessMessage(null);

    if (!nextFile) {
      setFile(null);
      setError(null);
      return;
    }

    const validationError = validateZip(nextFile);
    if (validationError) {
      setFile(null);
      setError(validationError);
      return;
    }

    setFile(nextFile);
    setError(null);
  };

  const submitUpload = async () => {
    if (!file || isUploading) {
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await uploadZipAndAnalyze(file, setProgress);
      setSuccessMessage(`${response.upload.original_filename} uploaded and queued.`);
      window.setTimeout(() => {
        router.push(`/dashboard?taskId=${encodeURIComponent(response.task_id)}`);
      }, 700);
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
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-slate-950">
      <div className="border-b border-slate-200 px-6 py-5 dark:border-white/10">
        <h1 className="text-lg font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          Talend project upload
        </h1>
      </div>

      <div className="p-6">
        <input
          ref={inputRef}
          type="file"
          accept=".zip,application/zip,application/x-zip-compressed"
          className="sr-only"
          onChange={(event) => selectFile(event.target.files?.[0] ?? null)}
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
            selectFile(event.dataTransfer.files[0] ?? null);
          }}
          className={[
            "flex min-h-72 w-full flex-col items-center justify-center rounded-lg border border-dashed px-6 text-center transition",
            isDragging
              ? "border-cyan-600 bg-cyan-50 dark:border-cyan-300 dark:bg-cyan-400/10"
              : "border-slate-300 bg-slate-50 hover:border-cyan-600 hover:bg-cyan-50 dark:border-white/10 dark:bg-white/5 dark:hover:border-cyan-300 dark:hover:bg-cyan-400/10",
          ].join(" ")}
        >
          <span className="flex h-14 w-14 items-center justify-center rounded-lg border border-cyan-200 bg-white text-cyan-700 shadow-sm dark:border-cyan-400/20 dark:bg-slate-950 dark:text-cyan-200">
            <UploadCloud className="h-7 w-7" />
          </span>
          <span className="mt-5 text-base font-semibold text-slate-950 dark:text-white">
            Drop ZIP archive here
          </span>
          <span className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            or select a file from your machine
          </span>
        </button>

        {file ? (
          <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 dark:border-white/10 dark:bg-slate-950 dark:text-slate-300">
                  <FileArchive className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-950 dark:text-white">
                    {file.name}
                  </p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => selectFile(null)}
                disabled={isUploading}
                className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-white/5 dark:text-slate-100"
              >
                <X className="h-4 w-4" />
                Remove
              </button>
            </div>
          </div>
        ) : null}

        <div className="mt-5">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-slate-700 dark:text-slate-300">Upload progress</span>
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
          <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200">
            {error}
          </div>
        ) : null}

        {successMessage ? (
          <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-200">
            {successMessage}
          </div>
        ) : null}

        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
          <button
            type="button"
            onClick={() => selectFile(null)}
            disabled={isUploading || !file}
            className="rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-white/5 dark:text-slate-100"
          >
            Clear
          </button>
          <button
            type="button"
            onClick={submitUpload}
            disabled={!file || isUploading}
            className="rounded-md bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
          >
            {isUploading ? "Uploading" : "Submit ZIP"}
          </button>
        </div>
      </div>
    </section>
  );
}

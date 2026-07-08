import { appConfig } from "@/lib/config";

export type ProjectInfo = {
  analysis_id: string;
  project_name: string;
  uploaded_at: string;
};

export type ExecutionLogUploadResponse = {
  id: string;
  project_id: string;
  project_name: string;
  filename: string;
  original_filename: string;
  size_bytes: number;
  status: string;
  entries_count: number;
  execution_records_count: number;
  duplicate_count: number;
  log_date_from: string | null;
  log_date_to: string | null;
  validation_messages: Array<{ field: string; message: string; severity: string }>;
  upload_date: string;
  total_log_lines: number;
  csv_rows_read: number;
  execution_starts_found: number;
  execution_ends_found: number;
  parse_errors: number;
  validation_warnings: number;
};

export type ExecutionRecordData = {
  project_id: string;
  project_name: string;
  workspace_name: string;
  environment_name: string;
  plan_name: string;
  artifact_name: string;
  task_execution_id: string;
  plan_execution_id: string;
  remote_engine_name: string;
  execution_start_time: string | null;
  execution_end_time: string | null;
  execution_status: string;
  execution_duration_seconds: number | null;
  error_message: string;
  original_log_file_name: string;
  upload_date: string | null;
  source_file: string;
};

export type ProjectUploadSummary = {
  project_id: string;
  project_name: string;
  upload_id: string;
  original_filename: string;
  upload_date: string | null;
  status: string;
  entries_count: number;
  execution_records_count: number;
  log_date_from: string | null;
  log_date_to: string | null;
  validation_messages: Array<{ field: string; message: string; severity: string }>;
  total_log_lines: number;
  csv_rows_read: number;
  execution_starts_found: number;
  execution_ends_found: number;
  parse_errors: number;
  validation_warnings: number;
};

export type ExecutionLogHistoryItem = {
  id: string;
  project_name: string;
  project_id: string;
  filename: string;
  original_filename: string;
  upload_date: string;
  processing_status: string;
  size_bytes: number;
};

export async function fetchProjects(): Promise<ProjectInfo[]> {
  const response = await fetch(
    `${appConfig.apiBaseUrl.replace(/\/$/, "")}/execution-logs/projects`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    throw new Error("Failed to fetch projects.");
  }
  return response.json() as Promise<ProjectInfo[]>;
}

export function uploadExecutionLog(
  projectId: string,
  projectName: string,
  file: File,
  onProgress: (progress: number) => void,
): Promise<ExecutionLogUploadResponse> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("project_id", projectId);
    formData.append("project_name", projectName);
    formData.append("file", file, file.name);

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      onProgress(Math.round((event.loaded / event.total) * 100));
    };

    request.onload = () => {
      const responseText = request.responseText || "{}";
      if (request.status === 201) {
        onProgress(100);
        resolve(JSON.parse(responseText) as ExecutionLogUploadResponse);
        return;
      }
      try {
        const parsed = JSON.parse(responseText) as { detail?: string };
        reject(new Error(parsed.detail ?? `Upload failed with status ${request.status}.`));
      } catch {
        reject(new Error(`Upload failed with status ${request.status}.`));
      }
    };

    request.onerror = () => {
      reject(new Error("Unable to reach the upload API."));
    };

    request.open(
      "POST",
      `${appConfig.apiBaseUrl.replace(/\/$/, "")}/execution-logs/upload`,
    );
    request.send(formData);
  });
}

export async function fetchUploadHistory(): Promise<ExecutionLogHistoryItem[]> {
  const response = await fetch(
    `${appConfig.apiBaseUrl.replace(/\/$/, "")}/execution-logs/history`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    throw new Error("Failed to fetch upload history.");
  }
  return response.json() as Promise<ExecutionLogHistoryItem[]>;
}

export async function fetchExecutionRecords(
  projectId: string,
): Promise<ExecutionRecordData[]> {
  try {
    const response = await fetch(
      `${appConfig.apiBaseUrl.replace(/\/$/, "")}/execution-logs/projects/${projectId}/records`,
      { cache: "no-store" },
    );
    if (!response.ok) return [];
    return (await response.json()) as ExecutionRecordData[];
  } catch {
    return [];
  }
}

export async function fetchProjectUploadSummary(
  projectId: string,
): Promise<ProjectUploadSummary | null> {
  try {
    const response = await fetch(
      `${appConfig.apiBaseUrl.replace(/\/$/, "")}/execution-logs/projects/${projectId}/summary`,
      { cache: "no-store" },
    );
    if (!response.ok) return null;
    return (await response.json()) as ProjectUploadSummary;
  } catch {
    return null;
  }
}

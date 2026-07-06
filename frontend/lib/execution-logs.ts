import { appConfig } from "@/lib/config";

export type ProjectInfo = {
  analysis_id: string;
  project_name: string;
  uploaded_at: string;
};

export type ExecutionLogUploadResponse = {
  id: string;
  project_id: string;
  filename: string;
  original_filename: string;
  size_bytes: number;
  status: string;
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

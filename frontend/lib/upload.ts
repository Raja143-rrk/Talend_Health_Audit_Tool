import { appConfig } from "@/lib/config";

type UploadResponse = {
  filename: string;
  original_filename: string;
  size_bytes: number;
  path: string;
};

type AnalysisCreateResponse = {
  task_id: string;
  analysis_id: string;
  status: string;
  message: string;
  upload: UploadResponse;
  task_status_url: string;
  status_url: string;
  dashboard_url: string;
};

type AnalysisExecutionResponse = AnalysisCreateResponse & {
  dashboard: Record<string, unknown> | null;
  workflow: Record<string, unknown>;
};

export function uploadZip(
  file: File,
  onProgress: (progress: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const formData = new FormData();

    formData.append("file", file, file.name);

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        return;
      }

      onProgress(Math.round((event.loaded / event.total) * 100));
    };

    request.onload = () => {
      const responseText = request.responseText || "{}";

      if (request.status === 201) {
        onProgress(100);
        resolve(JSON.parse(responseText) as UploadResponse);
        return;
      }

      try {
        const parsed = JSON.parse(responseText) as { detail?: string };
        const detail = Array.isArray(parsed.detail)
          ? "Upload request is missing the multipart field named file."
          : parsed.detail;
        reject(new Error(detail ?? `Upload failed with status ${request.status}.`));
      } catch {
        reject(new Error(`Upload failed with status ${request.status}.`));
      }
    };

    request.onerror = () => {
      reject(new Error("Unable to reach the upload API."));
    };

    request.open("POST", `${appConfig.apiBaseUrl.replace(/\/$/, "")}/uploads/zip`);
    request.send(formData);
  });
}

export function uploadZipAndAnalyze(
  files: File[],
  onProgress: (progress: number) => void,
): Promise<AnalysisCreateResponse> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const formData = new FormData();

    for (const file of files) {
      formData.append("file", file, file.name);
    }

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        return;
      }

      onProgress(Math.round((event.loaded / event.total) * 100));
    };

    request.onload = () => {
      const responseText = request.responseText || "{}";

      if (request.status === 202) {
        onProgress(100);
        resolve(JSON.parse(responseText) as AnalysisCreateResponse);
        return;
      }

      try {
        const parsed = JSON.parse(responseText) as { detail?: string };
        const detail = Array.isArray(parsed.detail)
          ? "Upload request is missing the multipart field named file."
          : parsed.detail;
        reject(new Error(detail ?? `Analysis request failed with status ${request.status}.`));
      } catch {
        reject(new Error(`Analysis request failed with status ${request.status}.`));
      }
    };

    request.onerror = () => {
      reject(new Error("Unable to reach the analysis API."));
    };

    request.open(
      "POST",
      `${appConfig.apiBaseUrl.replace(/\/$/, "")}/uploads/zip/analyze`,
    );
    request.send(formData);
  });
}

export function uploadZipAndExecute(
  file: File,
  onProgress: (progress: number) => void,
): Promise<AnalysisExecutionResponse> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const formData = new FormData();

    formData.append("file", file, file.name);

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        return;
      }

      onProgress(Math.round((event.loaded / event.total) * 100));
    };

    request.onload = () => {
      const responseText = request.responseText || "{}";

      if (request.status === 200) {
        onProgress(100);
        resolve(JSON.parse(responseText) as AnalysisExecutionResponse);
        return;
      }

      try {
        const parsed = JSON.parse(responseText) as { detail?: string };
        const detail = Array.isArray(parsed.detail)
          ? "Upload request is missing the multipart field named file."
          : parsed.detail;
        reject(new Error(detail ?? `Execution request failed with status ${request.status}.`));
      } catch {
        reject(new Error(`Execution request failed with status ${request.status}.`));
      }
    };

    request.onerror = () => {
      reject(new Error("Unable to reach the execution API."));
    };

    request.open(
      "POST",
      `${appConfig.apiBaseUrl.replace(/\/$/, "")}/uploads/zip/execute`,
    );
    request.send(formData);
  });
}

export type { AnalysisCreateResponse, AnalysisExecutionResponse, UploadResponse };

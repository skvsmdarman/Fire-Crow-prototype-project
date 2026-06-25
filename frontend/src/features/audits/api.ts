import { apiClient, API_BASE_URL } from "../../shared/api/client";
import { ENDPOINTS } from "../../shared/api/endpoints";
import { APIError } from "../../shared/api/errors";
import { Job, JobDetail, SubmitAuditBody, SystemStatus } from "./types";

export async function submitAudit(body: SubmitAuditBody): Promise<Job> {
  return apiClient.post<Job>(ENDPOINTS.audit.submit, body);
}

export async function fetchJobs(): Promise<Job[]> {
  return apiClient.get<Job[]>(ENDPOINTS.audit.jobs);
}

export async function fetchJobDetail(jobId: string): Promise<JobDetail> {
  return apiClient.get<JobDetail>(ENDPOINTS.audit.job(jobId));
}

export async function cancelJob(jobId: string): Promise<void> {
  return apiClient.delete<void>(ENDPOINTS.audit.job(jobId));
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  return apiClient.get<SystemStatus>(ENDPOINTS.system.status);
}

export async function fetchReportBlob(jobId: string): Promise<{ blob: Blob; requestId?: string }> {
  const url = `${API_BASE_URL}${ENDPOINTS.audit.report(jobId)}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      credentials: "include",
    });
  } catch {
    throw new APIError("Network connection failed. Please verify your connection.");
  }

  const requestId = response.headers.get("X-Request-ID") || response.headers.get("x-request-id") || undefined;

  if (!response.ok) {
    let message = `Failed to download report (Status ${response.status})`;
    const contentType = response.headers.get("Content-Type") || "";
    if (contentType.includes("application/json")) {
      try {
        const errObj = await response.json();
        message = errObj?.detail || errObj?.message || message;
      } catch {
        // ignore
      }
    } else {
      try {
        const text = await response.text();
        if (text && text.length < 200) {
          message = text;
        }
      } catch {
        // ignore
      }
    }
    throw new APIError(message, response.status, undefined, requestId);
  }

  const blob = await response.blob();
  if (blob.size === 0) {
    throw new APIError("The downloaded report file was empty.", response.status, undefined, requestId);
  }

  return { blob, requestId };
}

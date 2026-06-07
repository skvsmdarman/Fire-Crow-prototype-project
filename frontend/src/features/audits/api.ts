import { apiClient } from "../../shared/api/client";
import { ENDPOINTS } from "../../shared/api/endpoints";
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

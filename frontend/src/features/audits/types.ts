export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled" | "partial";
export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface Job {
  id: string;
  user_id: string;
  repo_url: string;
  repo_branch: string;
  status: JobStatus;
  created_at: string;
  finished_at: string | null;
  cancel_requested: boolean;
  cancel_requested_at: string | null;
  report_pdf_url: string | null;
  error_message: string | null;
  email_delivered?: boolean;
  github_issues_raised?: boolean;
  github_pr_created?: boolean;
}

export interface Finding {
  id: string;
  agent_source: string;
  title: string;
  description: string;
  severity: Severity;
  cvss_score: number | null;
  cvss_vector: string | null;
  evidence: string | null;
  remediation: string | null;
}

export interface JobDetail {
  job: Job;
  findings: Finding[];
}

export interface SubmitAuditBody {
  repo_url: string;
  repo_branch?: string;
  scanners?: string[];
  sandbox_mode?: "docker" | "simulation";
}

export interface SystemAgent {
  name: string;
  role: string;
  status: string;
}

export interface SystemStatus {
  api: string;
  database: string;
  debug: boolean;
  sandbox_mode: "simulation" | "docker";
  stats: { jobs: number; findings: number };
  integrations: Record<string, boolean>;
  agents: SystemAgent[];
}

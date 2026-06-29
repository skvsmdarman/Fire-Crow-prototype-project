export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled" | "partial";
export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface ProviderAvailability {
  github: boolean;
  google: boolean;
  password: boolean;
}

export interface PolicyContext {
  privacy_policy_version: string;
  terms_version: string;
  providers: ProviderAvailability;
}

export interface AuthUser {
  user_id: string;
  username: string;
  email?: string | null;
  role?: string;
  privacy_policy_version?: string;
  privacy_policy_accepted_at?: string | null;
  providers?: {
    github?: {
      connected: boolean;
      private_repo_access?: boolean;
      workflow_write_access?: boolean;
      org_read_access?: boolean;
      scopes?: string[];
      required_scopes?: string[];
      token_persisted?: boolean;
    };
    google?: {
      connected: boolean;
    };
  };
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  username: string;
  user_id: string;
}

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
  security_score?: number | null;
  email_delivered?: boolean;
  github_issues_raised?: boolean;
  github_pr_created?: boolean;
}

export interface SubmitAuditRequest {
  repo_url: string;
  repo_branch: string;
  attestation_accepted: boolean;
  authorization_scope: string;
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

export interface JobDetailResponse {
  job: Job;
  findings: Finding[];
}

export interface AuditInsightResponse {
  insight: string;
  enabled: boolean;
}

export interface LeaderboardEntry {
  repo_url: string;
  score?: number | null;
  security_score?: number | null;
  completed_at?: string | null;
  finished_at?: string | null;
  critical_count?: number | null;
}

export interface SystemStatus {
  api: string;
  database: string;
  readiness?: string;
  debug?: boolean;
  sandbox_mode?: "simulation" | "docker";
  stats: { jobs: number; findings: number };
  legal?: {
    privacy_policy_version?: string;
    terms_version?: string;
  };
  llm_features?: {
    chat_assistant: boolean;
    dashboard_insight: boolean;
    attack_chain_naming: boolean;
    pr_description: boolean;
  };
  integrations?: Record<string, boolean>;
  agents?: Array<{ name: string; role: string; status: string }>;
}

export interface ChatResponse {
  response?: string;
  answer?: string;
}

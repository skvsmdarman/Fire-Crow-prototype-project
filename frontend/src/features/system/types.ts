export interface RawSystemStatus {
  api: string;
  database: string;
  readiness?: string;
  debug?: boolean;
  sandbox_mode?: "simulation" | "docker";
  stats?: { jobs: number; findings: number };
  integrations?: Record<string, boolean>;
  llm_features?: {
    chat_assistant: boolean;
    dashboard_insight: boolean;
    attack_chain_naming: boolean;
    pr_description: boolean;
  };
  agents?: Array<{ name: string; role: string; status: string }>;
  scanner_capabilities?: Record<string, boolean>;
  github_permissions?: {
    scopes: string[];
    descriptions: Record<string, string>;
  };
}

export type StatusValue = 
  | "loading"
  | "unavailable"
  | "admin_only"
  | "configured"
  | "not_configured"
  | "unknown";

export interface SystemStatusViewModel {
  api: "online" | "offline" | "unknown";
  database: "connected" | "unavailable" | "unknown";
  readiness: "ready" | "degraded" | "unknown";
  debug: boolean | "admin_only" | "unknown";
  sandbox_mode: "simulation" | "docker" | "admin_only" | "unknown";
  stats: { jobs: number; findings: number } | "unknown";
  integrations: Record<string, StatusValue> | "admin_only" | "unknown";
  llm_features: {
    chat_assistant: boolean;
    dashboard_insight: boolean;
    attack_chain_naming: boolean;
    pr_description: boolean;
  } | "unknown";
  agents: Array<{ name: string; role: string; status: string }>;
  scanner_capabilities: Record<string, boolean> | "not_reported";
  github_permissions: {
    scopes: string[];
    descriptions: Record<string, string>;
  } | "unavailable" | "unknown";
}

export interface SystemStatus {
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
}

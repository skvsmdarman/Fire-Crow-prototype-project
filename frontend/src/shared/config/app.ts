/**
 * Application-wide configuration constants.
 * Centralizes hardcoded values that may change across environments.
 */

// Company / Branding
export const COMPANY_NAME = "Nova Devs";
export const COMPANY_NAME_SHORT = "Nova labs";
export const PRODUCT_NAME = "Fire Crow";
export const PRODUCT_VERSION = "FCv1";
export const PRODUCT_TAGLINE = `${PRODUCT_VERSION} security audit`;

// Contact
export const SUPPORT_EMAIL = "security@novadevs.dev";

// Policy versions (update when policies change)
export const PRIVACY_POLICY_VERSION = "2026-06-06";
export const TERMS_VERSION = "2026-06-06";

// Copyright
export const COPYRIGHT_YEAR = 2026;
export const COPYRIGHT_HOLDER = COMPANY_NAME;

// Risk scoring weights (used in dashboard posture calculations)
export const RISK_WEIGHTS = {
  critical: 28,
  high: 18,
  medium: 9,
  low: 4,
  info: 0,
} as const;

// Posture thresholds
export const POSTURE_THRESHOLDS = {
  healthy: 80,
  moderate: 55,
  weak: 25,
} as const;

// Pipeline progress stages (percentage milestones)
export const PIPELINE_STAGES = {
  intake: 0,
  clone: 15,
  sast: 40,
  deps: 50,
  dynamic: 60,
  ai: 75,
  report: 90,
  complete: 100,
} as const;

// Polling intervals (ms)
export const JOB_POLL_INTERVAL_MS = 3500;
export const TERMINAL_ANIMATION_TICK_MS = 2000;

// SSE / Log streaming
export const MAX_LOG_LINES = 500;

// Default git branch
export const DEFAULT_BRANCH = "main";

// GitHub OAuth scope descriptions (for UI display)
export const GITHUB_SCOPE_DESCRIPTIONS: Record<string, string> = {
  repo: "Full control of private repositories (issues, labels, PRs, code)",
  "read:org": "Read organization membership",
  "user:email": "Access user email addresses",
  workflow: "Update GitHub Action workflows",
};

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
export const PRIVACY_POLICY_VERSION = "2026-06-06";
export const TERMS_VERSION = "2026-06-06";

interface PolicyEventInput {
  eventType: "link_click" | "page_view";
  href?: string;
  pagePath?: string;
  policy: "privacy_policy" | "terms";
  policyVersion: string;
  referrerPath?: string;
  source: string;
}

export async function logPolicyEvent(input: PolicyEventInput): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }

  const token = window.localStorage.getItem("fc_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  await fetch(`${API_BASE_URL}/auth/policy-events`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      event_type: input.eventType,
      href: input.href,
      page_path: input.pagePath,
      policy: input.policy,
      policy_version: input.policyVersion,
      referrer_path: input.referrerPath,
      source: input.source,
    }),
    keepalive: true,
  }).catch(() => undefined);
}

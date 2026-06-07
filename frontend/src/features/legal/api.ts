import { ENDPOINTS } from "../../shared/api/endpoints";

export interface PolicyEventInput {
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

  // Weasy, background fire-and-forget request using keepalive
  const headers: Record<string, string> = {};
  const token = window.localStorage.getItem("fc_token");
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  // We can use standard fetch or apiClient. Here we do fetch with keepalive to allow page transitions
  // But using the dynamic API base URL from apiClient
  const baseUrl = window.localStorage.getItem("fc_api_url") || ""; 
  // Let's import API_BASE_URL to resolve it cleanly
  const apiBase = baseUrl || (process.env.NEXT_PUBLIC_API_URL || "/api/v1");

  await fetch(`${apiBase}${ENDPOINTS.auth.policyEvents}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
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

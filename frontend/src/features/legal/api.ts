import { buildApiUrl } from "../../shared/api/baseUrl";
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

  // Background fire-and-forget request using keepalive.
  // The auth cookie (HttpOnly) is sent automatically via credentials: "include" —
  // no token handling needed here.
  const url = buildApiUrl(ENDPOINTS.auth.policyEvents);

  await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
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

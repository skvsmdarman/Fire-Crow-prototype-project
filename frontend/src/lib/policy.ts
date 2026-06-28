import { request } from "./request";

export async function recordPolicyEvent(payload: {
  policy: "terms" | "privacy_policy";
  event_type: "link_click" | "page_view";
  policy_version: string;
  source?: string;
  href?: string;
  page_path?: string;
  referrer_path?: string;
}): Promise<void> {
  try {
    await request<{ status: string }>("/auth/policy-events", {
      method: "POST",
      body: payload,
    });
  } catch {
    // Legal event tracking should never block the user.
  }
}

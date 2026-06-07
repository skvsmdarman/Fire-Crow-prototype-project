"use client";

import { useEffect } from "react";
import { logPolicyEvent } from "../api";

interface PolicyPageTrackerProps {
  policy: "privacy_policy" | "terms";
  policyVersion: string;
  source: string;
}

export default function PolicyPageTracker({
  policy,
  policyVersion,
  source,
}: PolicyPageTrackerProps) {
  useEffect(() => {
    void logPolicyEvent({
      eventType: "page_view",
      pagePath: typeof window !== "undefined" ? window.location.pathname : undefined,
      policy,
      policyVersion,
      source,
    });
  }, [policy, policyVersion, source]);

  return null;
}

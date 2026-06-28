"use client";

import { useEffect } from "react";
import Link, { LinkProps } from "next/link";
import { ReactNode } from "react";
import { recordPolicyEvent } from "../lib/policy";

export function PolicyPageTracker({
  policy,
  version,
  source,
}: {
  policy: "terms" | "privacy_policy";
  version: string;
  source: string;
}) {
  useEffect(() => {
    void recordPolicyEvent({
      policy,
      event_type: "page_view",
      policy_version: version,
      source,
      page_path: window.location.pathname,
      referrer_path: document.referrer,
    });
  }, [policy, source, version]);

  return null;
}

export function PolicyLink({
  href,
  policy,
  version,
  source,
  children,
  className,
}: LinkProps & {
  policy: "terms" | "privacy_policy";
  version: string;
  source: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={className}
      onClick={() => {
        void recordPolicyEvent({
          policy,
          event_type: "link_click",
          policy_version: version,
          source,
          href: typeof href === "string" ? href : href.pathname?.toString(),
          page_path: typeof window !== "undefined" ? window.location.pathname : undefined,
        });
      }}
    >
      {children}
    </Link>
  );
}

"use client";

import Link, { LinkProps } from "next/link";
import { MouseEvent, ReactNode } from "react";

import { logPolicyEvent, PRIVACY_POLICY_VERSION, TERMS_VERSION } from "../lib/policy";

interface PolicyLinkProps extends LinkProps {
  children: ReactNode;
  className?: string;
  onClick?: (event: MouseEvent<HTMLAnchorElement>) => void;
  policy: "privacy_policy" | "terms";
  source: string;
}

export default function PolicyLink({
  children,
  className,
  onClick,
  policy,
  source,
  ...props
}: PolicyLinkProps) {
  const version = policy === "privacy_policy" ? PRIVACY_POLICY_VERSION : TERMS_VERSION;

  return (
    <Link
      {...props}
      className={className}
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented) {
          return;
        }

        void logPolicyEvent({
          eventType: "link_click",
          href: typeof props.href === "string" ? props.href : undefined,
          pagePath: typeof window !== "undefined" ? window.location.pathname : undefined,
          policy,
          policyVersion: version,
          referrerPath: typeof window !== "undefined" ? window.location.pathname : undefined,
          source,
        });
      }}
    >
      {children}
    </Link>
  );
}

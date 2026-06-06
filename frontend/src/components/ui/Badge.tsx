"use client";

import React from "react";
import styles from "./Badge.module.css";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "status" | "severity" | "simple";
  type?: "queued" | "running" | "completed" | "failed" | "cancelled" | "partial" | "cancelling" |
         "critical" | "high" | "medium" | "low" | "info" | "live";
  pulse?: boolean;
}

export default function Badge({
  children,
  className,
  variant = "simple",
  type,
  pulse = false,
  ...props
}: BadgeProps) {
  const badgeClasses = [
    styles.badge,
    styles[variant],
    type ? styles[type] : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <span className={badgeClasses} {...props}>
      {pulse && <span className={styles.pulseDot} />}
      {children}
    </span>
  );
}

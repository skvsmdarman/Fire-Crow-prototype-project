import { ReactNode } from "react";

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "critical" | "info";
}) {
  return <span className={`fc-badge fc-badge-${tone}`}>{children}</span>;
}

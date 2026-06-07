import React from "react";
import Badge from "../../components/ui/Badge";

interface StatusBadgeProps {
  status: "queued" | "running" | "completed" | "failed" | "cancelled" | "partial" | "cancelling";
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const isPulse = status === "running" || status === "cancelling";
  return (
    <Badge variant="status" type={status} pulse={isPulse}>
      {status}
    </Badge>
  );
}

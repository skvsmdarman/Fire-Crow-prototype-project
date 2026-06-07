import React from "react";
import Badge from "../../components/ui/Badge";

interface SeverityBadgeProps {
  severity: "critical" | "high" | "medium" | "low" | "info";
}

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  return (
    <Badge variant="severity" type={severity}>
      {severity}
    </Badge>
  );
}

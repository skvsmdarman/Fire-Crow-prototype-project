import React from "react";

interface EmptyStateProps {
  message: string;
  icon?: React.ReactNode;
}

export function EmptyState({ message, icon }: EmptyStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
        color: "rgba(255, 255, 255, 0.4)",
        border: "1px dashed rgba(255, 255, 255, 0.08)",
        borderRadius: "8px",
        background: "rgba(255, 255, 255, 0.01)",
        gap: "12px",
      }}
    >
      {icon && <div style={{ opacity: 0.6 }}>{icon}</div>}
      <p style={{ fontSize: "13px", margin: 0 }}>{message}</p>
    </div>
  );
}

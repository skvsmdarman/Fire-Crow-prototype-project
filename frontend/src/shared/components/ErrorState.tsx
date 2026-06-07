import React from "react";
import { AlertTriangle } from "lucide-react";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div
      style={{
        padding: "16px 20px",
        borderRadius: "8px",
        background: "rgba(239, 83, 80, 0.08)",
        border: "1px solid rgba(239, 83, 80, 0.25)",
        color: "#ff8a80",
        display: "flex",
        alignItems: "start",
        gap: "12px",
        fontSize: "13px",
        lineHeight: "1.5",
        margin: "12px 0",
      }}
    >
      <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
      <div style={{ flexGrow: 1 }}>
        <p style={{ margin: 0 }}>{message}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            style={{
              background: "none",
              border: "none",
              color: "#ffb4ab",
              textDecoration: "underline",
              padding: 0,
              cursor: "pointer",
              marginTop: "8px",
              fontSize: "12px",
              fontWeight: "600",
            }}
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

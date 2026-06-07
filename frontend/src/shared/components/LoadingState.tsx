import React from "react";
import FireCrowLoader from "../../components/FireCrowLoader";

interface LoadingStateProps {
  message?: string;
  size?: "sm" | "md" | "lg";
}

export function LoadingState({ message = "Loading data...", size = "md" }: LoadingStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        gap: "16px",
        color: "rgba(255, 255, 255, 0.5)",
      }}
    >
      <FireCrowLoader size={size} />
      <span style={{ fontSize: "13px" }}>{message}</span>
    </div>
  );
}

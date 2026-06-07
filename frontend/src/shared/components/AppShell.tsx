import React from "react";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div
      style={{
        position: "relative",
        minHeight: "100vh",
        background: "#0c0c0e",
        color: "#f4f4f5",
        overflowX: "hidden",
      }}
    >
      <div
        className="auth-glow-orb auth-glow-orb-1"
        style={{
          opacity: 0.15,
          position: "fixed",
          pointerEvents: "none",
          zIndex: 0,
        }}
        aria-hidden="true"
      />
      <div
        className="auth-glow-orb auth-glow-orb-2"
        style={{
          opacity: 0.15,
          position: "fixed",
          pointerEvents: "none",
          zIndex: 0,
        }}
        aria-hidden="true"
      />
      <div style={{ position: "relative", zIndex: 1 }}>{children}</div>
    </div>
  );
}
export default AppShell;

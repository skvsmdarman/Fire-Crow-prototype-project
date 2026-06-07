import React from "react";

interface PageHeaderProps {
  title: string;
  kicker?: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, kicker = "Fire Crow console", children }: PageHeaderProps) {
  return (
    <header
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "16px 24px",
        borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
        background: "rgba(255, 255, 255, 0.01)",
        backdropFilter: "blur(8px)",
      }}
    >
      <div>
        <div
          style={{
            fontSize: "10px",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "rgba(255, 255, 255, 0.4)",
            fontWeight: 600,
            marginBottom: "4px",
          }}
        >
          {kicker}
        </div>
        <h1 style={{ fontSize: "20px", fontWeight: 700, color: "#ffffff", margin: 0 }}>
          {title}
        </h1>
      </div>
      {children && <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>{children}</div>}
    </header>
  );
}

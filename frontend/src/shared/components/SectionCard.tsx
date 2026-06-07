import React from "react";
import Card, { CardProps } from "../../components/ui/Card";

interface SectionCardProps extends CardProps {
  title?: string;
  subtitle?: string;
  headerActions?: React.ReactNode;
}

export function SectionCard({
  title,
  subtitle,
  headerActions,
  children,
  ...props
}: SectionCardProps) {
  return (
    <Card variant="surface" {...props}>
      {(title || subtitle || headerActions) && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "start",
            borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
            paddingBottom: "12px",
            marginBottom: "16px",
          }}
        >
          <div>
            {subtitle && (
              <div
                style={{
                  fontSize: "10px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  color: "rgba(255, 255, 255, 0.4)",
                  fontWeight: 600,
                  marginBottom: "2px",
                }}
              >
                {subtitle}
              </div>
            )}
            {title && (
              <h2 style={{ fontSize: "15px", fontWeight: 600, color: "#ffffff", margin: 0 }}>
                {title}
              </h2>
            )}
          </div>
          {headerActions && <div style={{ display: "flex", gap: "8px" }}>{headerActions}</div>}
        </div>
      )}
      {children}
    </Card>
  );
}
export default SectionCard;

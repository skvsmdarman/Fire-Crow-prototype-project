"use client";

import { useEffect } from "react";
import Link from "next/link";
import { SiteHeader, SiteFooter } from "../../components/SiteChrome";
import { Card } from "../../components/ui/Card";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error boundary triggered:", error);
  }, [error]);

  return (
    <div className="fc-page" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <SiteHeader ctaHref="/" ctaLabel="Landing Page" />
      <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 20px" }}>
        <Card className="fc-panel" style={{ maxWidth: 620, width: "100%", padding: 40, textAlign: "center" }}>
          <div className="fc-brand-mark" style={{ margin: "0 auto 24px auto", fontSize: "1.5rem", fontWeight: "bold", background: "linear-gradient(135deg, var(--red), rgba(255, 95, 109, 0.2))" }}>!</div>
          <h1 style={{ fontSize: "2rem", marginBottom: 12, background: "linear-gradient(135deg, var(--red), var(--fire))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Dashboard Error
          </h1>
          <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 20 }}>
            Something went wrong while loading the dashboard console metrics or real-time event streams.
          </p>
          {error.message && (
            <pre style={{
              background: "var(--bg-soft)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "12px",
              fontSize: "0.85rem",
              color: "var(--red)",
              fontFamily: "monospace",
              textAlign: "left",
              overflowX: "auto",
              marginBottom: 30,
              whiteSpace: "pre-wrap"
            }}>
              {error.name}: {error.message}
            </pre>
          )}
          <div style={{ display: "flex", gap: 16, justifyContent: "center" }}>
            <button onClick={() => reset()} className="fc-button fc-button-primary">
              Reload Console
            </button>
            <Link href="/dashboard" className="fc-button" style={{ border: "1px solid var(--border)", background: "transparent" }}>
              Reset View
            </Link>
          </div>
        </Card>
      </main>
      <SiteFooter />
    </div>
  );
}

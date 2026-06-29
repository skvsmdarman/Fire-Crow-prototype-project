"use client";

import { useEffect } from "react";
import Link from "next/link";
import { SiteHeader, SiteFooter } from "../components/SiteChrome";
import { Card } from "../components/ui/Card";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service if needed
    console.error("Global crash boundary triggered:", error);
  }, [error]);

  return (
    <div className="fc-page" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <SiteHeader />
      <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 20px" }}>
        <Card className="fc-panel" style={{ maxWidth: 580, width: "100%", textAlign: "center", padding: 40 }}>
          <div className="fc-brand-mark" style={{ margin: "0 auto 24px auto", fontSize: "1.5rem", fontWeight: "bold", background: "linear-gradient(135deg, var(--red), rgba(255, 95, 109, 0.2))" }}>!</div>
          <h1 style={{ fontSize: "2rem", marginBottom: 12, background: "linear-gradient(135deg, var(--red), var(--fire))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Application Error
          </h1>
          <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 20 }}>
            An unexpected error occurred and has crashed the interface. The system telemetry has recorded this event.
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
              Retry Operation
            </button>
            <Link href="/" className="fc-button" style={{ border: "1px solid var(--border)", background: "transparent" }}>
              Back to Safety
            </Link>
          </div>
        </Card>
      </main>
      <SiteFooter />
    </div>
  );
}

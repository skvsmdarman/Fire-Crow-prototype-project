"use client";

import { useEffect } from "react";
import Link from "next/link";
import { SiteHeader, SiteFooter } from "../../components/SiteChrome";
import { Card } from "../../components/ui/Card";

interface ErrorDetails {
  name: string;
  message: string;
  isChunkLoadError: boolean;
}

function getErrorDetails(error: unknown): ErrorDetails {
  let name = "Error";
  let message = "An unexpected runtime issue occurred while loading the dashboard console.";
  let isChunkLoadError = false;

  if (!error) {
    return { name, message, isChunkLoadError };
  }

  if (error instanceof Error) {
    name = error.name || "Error";
    message = error.message || "No error message provided.";
  } else if (typeof error === "object") {
    const errObj = error as Record<string, unknown>;
    name = String(errObj.name || errObj.type || "EventError");
    
    if (typeof errObj.message === "string") {
      message = errObj.message;
    } else if (errObj.target && typeof errObj.target === "object") {
      const target = errObj.target as Record<string, unknown>;
      const tagName = String(target.tagName || "element").toLowerCase();
      const src = String(target.src || target.href || "");
      message = `Failed to load ${tagName} resource ${src ? `from: ${src}` : ""}`.trim();
      isChunkLoadError = true;
    } else {
      try {
        message = JSON.stringify(error);
      } catch {
        message = String(error);
      }
    }
  } else if (typeof error === "string") {
    message = error;
  }

  if (
    name === "ChunkLoadError" ||
    name === "[object Event]" ||
    message.includes("ChunkLoadError") ||
    message.includes("Loading chunk") ||
    message.includes("chunk") ||
    message === "[object Event]"
  ) {
    isChunkLoadError = true;
    if (name === "[object Event]") {
      name = "AssetLoadError";
    }
    if (message === "[object Event]" || message.includes("ChunkLoadError")) {
      message = "A script chunk or style asset failed to load. This typically happens when the dashboard has been updated and the browser tries to fetch outdated, cached files.";
    }
  }

  return { name, message, isChunkLoadError };
}

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const details = getErrorDetails(error);

  useEffect(() => {
    console.error("Dashboard error boundary triggered:", error);
  }, [error]);

  const handleForceRefresh = () => {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  };

  return (
    <div className="fc-page" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <SiteHeader ctaHref="/" ctaLabel="Landing Page" />
      <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 20px" }}>
        <Card className="fc-panel" style={{ maxWidth: 620, width: "100%", padding: 40, textAlign: "center" }}>
          <div className="fc-brand-mark" style={{ margin: "0 auto 24px auto", fontSize: "1.5rem", fontWeight: "bold", background: "linear-gradient(135deg, var(--red), rgba(255, 95, 109, 0.2))" }}>!</div>
          
          <h1 style={{ fontSize: "2rem", marginBottom: 12, background: "linear-gradient(135deg, var(--red), var(--fire))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            {details.isChunkLoadError ? "Dashboard Update Required" : "Dashboard Error"}
          </h1>
          
          <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 20 }}>
            {details.isChunkLoadError
              ? "A required dashboard component has been updated on the server and must be reloaded to synchronize your session."
              : "Something went wrong while loading the dashboard console metrics or real-time event streams."}
          </p>

          {details.message && (
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
              {details.name}: {details.message}
            </pre>
          )}

          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            {details.isChunkLoadError ? (
              <button onClick={handleForceRefresh} className="fc-button fc-button-primary">
                Reload Dashboard
              </button>
            ) : (
              <>
                <button onClick={() => reset()} className="fc-button fc-button-primary">
                  Reload Console
                </button>
                <button onClick={handleForceRefresh} className="fc-button" style={{ border: "1px solid var(--border)", background: "transparent" }}>
                  Force Refresh
                </button>
              </>
            )}
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

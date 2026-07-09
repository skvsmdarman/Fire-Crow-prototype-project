import type { Metadata } from "next";
import { Suspense } from "react";
import { Card } from "../../components/ui/Card";
import { AuthConsole } from "../../components/auth/AuthConsole";

export const metadata: Metadata = {
  title: "Sign In — Fire Crow",
  description: "Sign in to your Fire Crow workspace with GitHub. Open the backend audit dashboard, findings, and reports through one simple auth path.",
};

export default function SignInPage() {
  return (
    <Suspense fallback={<AuthRouteFallback />}>
      <AuthConsole mode="signin" />
    </Suspense>
  );
}

function AuthRouteFallback() {
  return (
    <div className="fc-page" style={{ display: "grid", minHeight: "100vh", placeItems: "center", padding: "40px 20px" }}>
      <Card className="fc-panel" style={{ maxWidth: 520, width: "100%", textAlign: "center", padding: 34 }}>
        <div className="fc-brand-mark" style={{ margin: "0 auto 20px auto", fontSize: "1.2rem", fontWeight: 700 }}>FC</div>
        <h1 style={{ fontSize: "1.7rem", marginBottom: 10 }}>Loading sign in</h1>
        <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 18 }}>
          Preparing your workspace access form.
        </p>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <span
            aria-hidden="true"
            style={{
              width: 24,
              height: 24,
              borderRadius: "50%",
              border: "3px solid rgba(255,255,255,0.12)",
              borderTopColor: "var(--fire)",
              animation: "fc-spin 1s linear infinite",
            }}
          />
        </div>
      </Card>
    </div>
  );
}

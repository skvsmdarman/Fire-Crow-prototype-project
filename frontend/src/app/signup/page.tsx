import type { Metadata } from "next";
import { Suspense } from "react";
import { Card } from "../../components/ui/Card";
import { AuthConsole } from "../../components/auth/AuthConsole";

export const metadata: Metadata = {
  title: "Create Account — Fire Crow",
  description: "Create your Fire Crow workspace with GitHub. Start the backend audit flow through one simple sign-in path.",
};

export default function SignUpPage() {
  return (
    <Suspense fallback={<AuthRouteFallback />}>
      <AuthConsole mode="signup" />
    </Suspense>
  );
}

function AuthRouteFallback() {
  return (
    <div className="fc-page" style={{ display: "grid", minHeight: "100vh", placeItems: "center", padding: "40px 20px" }}>
      <Card className="fc-panel" style={{ maxWidth: 520, width: "100%", textAlign: "center", padding: 34 }}>
        <div className="fc-brand-mark" style={{ margin: "0 auto 20px auto", fontSize: "1.2rem", fontWeight: 700 }}>FC</div>
        <h1 style={{ fontSize: "1.7rem", marginBottom: 10 }}>Loading account setup</h1>
        <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 18 }}>
          Preparing the workspace creation form.
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

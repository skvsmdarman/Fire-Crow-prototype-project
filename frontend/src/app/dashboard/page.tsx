import { Suspense } from "react";
import { DashboardConsole } from "../../components/dashboard/DashboardConsole";
import { Card } from "../../components/ui/Card";

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardRouteFallback />}>
      <DashboardConsole />
    </Suspense>
  );
}

function DashboardRouteFallback() {
  return (
    <div className="fc-page" style={{ minHeight: "100vh", padding: "40px 20px" }}>
      <main className="fc-shell fc-dashboard-shell">
        <Card className="fc-panel" style={{ maxWidth: 720, margin: "0 auto", padding: 36, textAlign: "center" }}>
          <div className="fc-brand-mark" style={{ margin: "0 auto 20px auto", fontSize: "1.2rem", fontWeight: 700 }}>FC</div>
          <h1 style={{ fontSize: "1.9rem", marginBottom: 10 }}>Loading dashboard</h1>
          <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 18 }}>
            Restoring your session, workspace data, and live audit state.
          </p>
          <div style={{ display: "flex", justifyContent: "center" }}>
            <span
              aria-hidden="true"
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                border: "3px solid rgba(255,255,255,0.12)",
                borderTopColor: "var(--fire)",
                animation: "fc-spin 1s linear infinite",
              }}
            />
          </div>
        </Card>
      </main>
    </div>
  );
}

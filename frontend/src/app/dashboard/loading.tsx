import { Card } from "../../components/ui/Card";

export default function DashboardLoading() {
  return (
    <div className="fc-page" style={{ minHeight: "100vh", padding: "40px 20px" }}>
      <main className="fc-shell fc-dashboard-shell">
        <Card className="fc-panel" style={{ marginBottom: 18, padding: 24 }}>
          <div className="skeleton-box" style={{ width: 120, height: 14, marginBottom: 14 }} />
          <div className="skeleton-box" style={{ width: "55%", height: 34, marginBottom: 14 }} />
          <div className="skeleton-box" style={{ width: "85%", height: 18, marginBottom: 18 }} />
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <div className="skeleton-box" style={{ width: 88, height: 28 }} />
            <div className="skeleton-box" style={{ width: 72, height: 28 }} />
            <div className="skeleton-box" style={{ width: 92, height: 28 }} />
          </div>
        </Card>

        <div className="fc-dashboard-grid">
          <Card className="fc-sidebar">
            <div>
              <div className="skeleton-box" style={{ width: 92, height: 14, marginBottom: 12 }} />
              <div className="skeleton-box" style={{ width: 150, height: 30, marginBottom: 12 }} />
              <div className="skeleton-box" style={{ width: "100%", height: 44 }} />
            </div>

            <div className="fc-sidebar-nav" style={{ display: "grid", gap: 10 }}>
              {[1, 2, 3, 4, 5].map((item) => (
                <div key={item} className="skeleton-box" style={{ width: "100%", height: 40 }} />
              ))}
            </div>

            <div className="skeleton-box" style={{ width: "100%", height: 88, borderRadius: 18 }} />
          </Card>

          <div className="fc-dashboard-main" style={{ display: "grid", gap: 18 }}>
            <Card className="fc-panel">
              <div className="skeleton-box" style={{ width: 140, height: 14, marginBottom: 10 }} />
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
                {[1, 2, 3].map((item) => (
                  <div key={item} style={{ display: "grid", gap: 8 }}>
                    <div className="skeleton-box" style={{ width: 90, height: 12 }} />
                    <div className="skeleton-box" style={{ width: "100%", height: 28 }} />
                    <div className="skeleton-box" style={{ width: "82%", height: 14 }} />
                  </div>
                ))}
              </div>
            </Card>

            {[1, 2, 3].map((item) => (
              <Card key={item} className="fc-panel">
                <div className="skeleton-box" style={{ width: 160, height: 14, marginBottom: 16 }} />
                <div style={{ display: "grid", gap: 12 }}>
                  <div className="skeleton-box" style={{ width: "100%", height: 68 }} />
                  <div className="skeleton-box" style={{ width: "100%", height: 68 }} />
                </div>
              </Card>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

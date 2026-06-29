import { SiteHeader, SiteFooter } from "../../components/SiteChrome";
import { Card } from "../../components/ui/Card";

export default function DashboardLoading() {
  return (
    <div className="fc-page" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <SiteHeader ctaHref="/" ctaLabel="Landing Page" />
      
      <main className="fc-shell fc-dashboard-shell" style={{ flex: 1 }}>
        <div className="fc-dashboard-grid">
          {/* Sidebar Skeleton */}
          <Card className="fc-sidebar">
            <div>
              <div className="skeleton-box" style={{ width: 80, height: 16, marginBottom: 12 }} />
              <div className="skeleton-box" style={{ width: 140, height: 32, marginBottom: 12 }} />
              <div className="skeleton-box" style={{ width: "100%", height: 48 }} />
            </div>

            <div className="fc-sidebar-nav" style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 24 }}>
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="skeleton-box" style={{ width: "100%", height: 40 }} />
              ))}
            </div>

            <Card className="fc-panel" style={{ marginTop: 24, padding: 16 }}>
              <div className="skeleton-box" style={{ width: 60, height: 12, marginBottom: 12 }} />
              <div style={{ display: "flex", gap: 8 }}>
                <div className="skeleton-box" style={{ width: 80, height: 24 }} />
                <div className="skeleton-box" style={{ width: 40, height: 24 }} />
              </div>
            </Card>

            <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
              <div className="skeleton-box" style={{ width: 100, height: 36 }} />
              <div className="skeleton-box" style={{ width: 80, height: 36 }} />
            </div>
          </Card>

          {/* Main Content Skeleton */}
          <div className="fc-dashboard-main" style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Overview Panel Skeleton */}
            <Card className="fc-panel" style={{ padding: 24 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 20 }}>
                {[1, 2, 3].map((i) => (
                  <div key={i} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div className="skeleton-box" style={{ width: 100, height: 14 }} />
                    <div className="skeleton-box" style={{ width: 160, height: 28 }} />
                  </div>
                ))}
              </div>
            </Card>

            {/* Launch Panel Skeleton */}
            <Card className="fc-panel" style={{ padding: 24 }}>
              <div className="skeleton-box" style={{ width: 120, height: 18, marginBottom: 18 }} />
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div className="skeleton-box" style={{ width: "100%", height: 44 }} />
                <div className="skeleton-box" style={{ width: "100%", height: 44 }} />
                <div className="skeleton-box" style={{ width: 150, height: 40, alignSelf: "flex-end" }} />
              </div>
            </Card>

            {/* Jobs Panel Skeleton */}
            <Card className="fc-panel" style={{ padding: 24 }}>
              <div className="skeleton-box" style={{ width: 160, height: 18, marginBottom: 18 }} />
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {[1, 2, 3].map((i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      <div className="skeleton-box" style={{ width: 240, height: 16 }} />
                      <div className="skeleton-box" style={{ width: 100, height: 12 }} />
                    </div>
                    <div className="skeleton-box" style={{ width: 80, height: 24 }} />
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </main>

      <SiteFooter />

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .skeleton-box {
          background: linear-gradient(90deg, rgba(255, 255, 255, 0.03) 25%, rgba(255, 255, 255, 0.07) 50%, rgba(255, 255, 255, 0.03) 75%);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
          border-radius: 8px;
        }
      `}} />
    </div>
  );
}

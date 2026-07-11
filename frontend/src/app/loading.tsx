import { Card } from "../components/ui/Card";

export default function Loading() {
  return (
    <div className="fc-page" style={{ display: "grid", minHeight: "100vh", placeItems: "center", padding: "40px 20px" }}>
      <Card className="fc-panel" style={{ maxWidth: 540, width: "100%", padding: 36, textAlign: "center" }}>
        <div
          className="fc-brand-mark"
          style={{ margin: "0 auto 22px auto", fontSize: "1.3rem", fontWeight: 700, background: "linear-gradient(135deg, var(--red), rgba(255, 95, 109, 0.2))" }}
        >
          FC
        </div>
        <h1 style={{ fontSize: "1.9rem", marginBottom: 12, background: "linear-gradient(135deg, var(--red), var(--fire))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          Loading Fire Crow
        </h1>
        <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 22 }}>
          Preparing the landing, authentication, and workspace routes.
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
    </div>
  );
}

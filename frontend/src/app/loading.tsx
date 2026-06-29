import { SiteHeader, SiteFooter } from "../components/SiteChrome";

export default function Loading() {
  return (
    <div className="fc-page" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <SiteHeader />
      <main style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 20px" }}>
        <div style={{ position: "relative", width: 80, height: 80, marginBottom: 24 }}>
          {/* Outer fire-orange glowing ring */}
          <div style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            border: "3px solid transparent",
            borderTopColor: "var(--fire)",
            borderBottomColor: "var(--fire-soft)",
            animation: "spin 1.5s linear infinite",
            filter: "drop-shadow(0 0 8px var(--fire))"
          }} />
          {/* Inner blue/cyan secondary ring spinning opposite */}
          <div style={{
            position: "absolute",
            inset: 10,
            borderRadius: "50%",
            border: "3px solid transparent",
            borderLeftColor: "var(--cyan)",
            borderRightColor: "rgba(108, 231, 255, 0.2)",
            animation: "spin-reverse 1s linear infinite"
          }} />
        </div>
        <h2 style={{ fontSize: "1.2rem", fontWeight: 600, color: "var(--text)", letterSpacing: "0.05em", textTransform: "uppercase" }}>
          Initializing Platform
        </h2>
        <p className="fc-muted" style={{ fontSize: "0.9rem", marginTop: 8 }}>
          Loading security orchestration components...
        </p>

        {/* Inline CSS animation since we are in a static context or standard layout */}
        <style dangerouslySetInnerHTML={{ __html: `
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          @keyframes spin-reverse {
            0% { transform: rotate(360deg); }
            100% { transform: rotate(0deg); }
          }
        `}} />
      </main>
      <SiteFooter />
    </div>
  );
}

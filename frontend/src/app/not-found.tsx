import Link from "next/link";
import { SiteHeader, SiteFooter } from "../components/SiteChrome";
import { Card } from "../components/ui/Card";

export default function NotFound() {
  return (
    <div className="fc-page" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <SiteHeader />
      <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 20px" }}>
        <Card className="fc-panel" style={{ maxWidth: 540, width: "100%", textAlign: "center", padding: 40 }}>
          <div className="fc-brand-mark" style={{ margin: "0 auto 24px auto", fontSize: "1.5rem", fontWeight: "bold" }}>404</div>
          <h1 style={{ fontSize: "2rem", marginBottom: 12, background: "linear-gradient(135deg, var(--fire), var(--fire-soft))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Endpoint Not Found
          </h1>
          <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 30 }}>
            The page you are looking for does not exist, has been moved, or is temporarily unavailable. Verify the URL or head back to the dashboard.
          </p>
          <div style={{ display: "flex", gap: 16, justifyContent: "center" }}>
            <Link href="/" className="fc-button fc-button-primary">
              Return Home
            </Link>
            <Link href="/dashboard" className="fc-button" style={{ border: "1px solid var(--border)", background: "transparent" }}>
              Go to Dashboard
            </Link>
          </div>
        </Card>
      </main>
      <SiteFooter />
    </div>
  );
}

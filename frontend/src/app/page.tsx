import Link from "next/link";
import { SiteFooter, SiteHeader } from "../components/SiteChrome";
import { Card } from "../components/ui/Card";

const FEATURE_TILES = [
  {
    marker: "01",
    title: "Run the audit",
    copy: "Start an authorized repository scan from one backend flow instead of stitching together separate tools.",
  },
  {
    marker: "02",
    title: "Read the findings",
    copy: "Keep severity, evidence, and remediation in one place so the result is usable without extra translation.",
  },
  {
    marker: "03",
    title: "Ship the report",
    copy: "Open the finished report and hand it to engineering or the client with the same session and audit history.",
  },
];

const TRUST_POINTS = [
  "GitHub sign-in only",
  "Cookie-backed workspace sessions",
  "Transient audit environments",
  "No stored source code",
];

export default function HomePage() {
  return (
    <div className="fc-page page-with-island" style={{ position: "relative", overflow: "hidden" }}>
      <SiteHeader />

      <div className="hero-orb-1" />
      <div className="hero-orb-2" />
      <div className="hero-orb-3" />

      <main>
        <section className="fc-shell fc-hero" style={{ paddingTop: 96, paddingBottom: 54 }}>
          <div className="fc-hero-grid" style={{ alignItems: "center" }}>
            <div>
              <span className="hero-badge">
                <span className="hero-badge-dot" />
                Backend audit workspace
              </span>

              <h1 style={{ maxWidth: 760 }}>
                Clear backend security review
                <br />
                <span className="fc-gradient-text">without noisy UI.</span>
              </h1>

              <p className="fc-copy" style={{ fontSize: "1.04rem", maxWidth: 620, marginTop: 24 }}>
                Fire Crow is built around the backend path that matters: sign in with GitHub, run the audit, inspect
                findings, and open the report.
              </p>

              <div className="hero-cta-row" style={{ justifyContent: "flex-start", marginTop: 30 }}>
                <Link href="/signin" className="fc-button fc-button-primary" style={{ padding: "0 30px" }}>
                  Continue with GitHub
                </Link>
                <Link href="/privacy" className="fc-button fc-button-secondary" style={{ padding: "0 26px" }}>
                  Read privacy policy
                </Link>
              </div>

              <div className="trust-strip" style={{ justifyContent: "flex-start", marginTop: 18 }}>
                {["One auth path", "Live audit stream", "Client-ready reports"].map((item) => (
                  <span key={item} className="trust-chip">
                    <span className="trust-chip-dot" />
                    {item}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ display: "grid", gap: 18 }}>
              <Card className="fc-panel glass-card" style={{ padding: 28 }}>
                <div className="fc-stack-between" style={{ alignItems: "flex-start", marginBottom: 18 }}>
                  <div>
                    <div className="fc-kicker">Current flow</div>
                    <h2 className="fc-panel-title" style={{ marginTop: 10 }}>
                      Simple in the UI. Strict in the backend.
                    </h2>
                  </div>
                  <span className="fc-badge fc-badge-success">GitHub only</span>
                </div>

                <div className="fc-table" style={{ gap: 12 }}>
                  {[
                    { label: "Auth", value: "GitHub OAuth into workspace session" },
                    { label: "Audit", value: "Backend queue, stream, findings, report" },
                    { label: "Scope", value: "Permissions tied to approved GitHub access" },
                  ].map((item) => (
                    <div key={item.label} className="fc-table-row">
                      <div style={{ flex: 1 }}>
                        <div className="fc-muted">{item.label}</div>
                        <div style={{ marginTop: 8, fontWeight: 600 }}>{item.value}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <div className="fc-grid-3">
                {[
                  { label: "Average start", value: "< 5 min" },
                  { label: "Code retained", value: "0 KB" },
                  { label: "Session type", value: "Private" },
                ].map((item) => (
                  <Card key={item.label} className="fc-metric" style={{ padding: 18 }}>
                    <div className="fc-muted">{item.label}</div>
                    <span className="fc-metric-value" style={{ fontSize: "1.4rem" }}>
                      {item.value}
                    </span>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="fc-shell" style={{ paddingBottom: 74 }}>
          <div className="fc-section-head" style={{ marginBottom: 26 }}>
            <div>
              <div className="fc-kicker">Core flow</div>
              <h2 className="fc-section-title fc-title-md" style={{ marginTop: 10 }}>
                The product stays close to the audit pipeline.
              </h2>
            </div>
            <div className="fc-copy" style={{ maxWidth: 540 }}>
              The landing page now speaks in plain terms. It points to the backend audit workflow instead of trying to
              sound bigger than the product.
            </div>
          </div>

          <div className="fc-grid-3">
            {FEATURE_TILES.map((tile) => (
              <article key={tile.title} className="glass-feature">
                <div className="feat-icon feat-icon--fire" style={{ fontFamily: "var(--font-display), sans-serif", fontWeight: 700 }}>
                  {tile.marker}
                </div>
                <h3 style={{ fontFamily: "var(--font-display), sans-serif", fontSize: "1.2rem", margin: "0 0 12px" }}>
                  {tile.title}
                </h3>
                <p className="fc-copy" style={{ margin: 0 }}>
                  {tile.copy}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section id="how-it-works" className="fc-shell" style={{ paddingBottom: 74 }}>
          <Card className="fc-panel glass-card" style={{ padding: 30 }}>
            <div className="fc-section-head" style={{ marginBottom: 24 }}>
              <div>
                <div className="fc-kicker">How it works</div>
                <h2 className="fc-section-title fc-title-md" style={{ marginTop: 10 }}>
                  GitHub in. Audit out.
                </h2>
              </div>
              <div className="fc-copy" style={{ maxWidth: 540 }}>
                The frontend is only the surface. The real product value is in the backend job flow, evidence pipeline,
                and report generation.
              </div>
            </div>

            <div className="fc-grid-3">
              {[
                { step: "01", label: "Use GitHub to open the workspace." },
                { step: "02", label: "Launch an authorized repository audit." },
                { step: "03", label: "Read the findings and open the report." },
              ].map((item) => (
                <div key={item.step} className="fc-table-row" style={{ minHeight: 176 }}>
                  <div style={{ flex: 1 }}>
                    <div className="fc-kicker">{item.step}</div>
                    <p className="fc-copy" style={{ margin: "16px 0 0", fontSize: "1rem" }}>
                      {item.label}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </section>

        <section id="trust" className="fc-shell" style={{ paddingBottom: 86 }}>
          <div className="fc-grid-2">
            <Card className="fc-panel glass-card" style={{ padding: 30 }}>
              <div className="fc-kicker">Trust</div>
              <h2 className="fc-section-title fc-title-md" style={{ marginTop: 10 }}>
                Keep the auth and audit path easy to explain.
              </h2>
              <p className="fc-copy" style={{ marginTop: 16, marginBottom: 24 }}>
                One sign-in route is easier to reason about. The backend keeps the session, consent, scope, and report
                flow aligned.
              </p>
              <div className="fc-data-list">
                {TRUST_POINTS.map((point) => (
                  <div key={point} className="fc-table-row">
                    <span className="fc-badge fc-badge-success">Active</span>
                    <span style={{ fontWeight: 500 }}>{point}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="fc-panel glass-card" style={{ padding: 30 }}>
              <div className="fc-kicker">Start</div>
              <h2 className="fc-section-title fc-title-md" style={{ marginTop: 10 }}>
                Open the workspace and move straight to the backend console.
              </h2>
              <p className="fc-copy" style={{ marginTop: 16 }}>
                This page is intentionally simpler now. It points to the real value of the project instead of layering
                extra product language over it.
              </p>
              <div className="hero-cta-row" style={{ justifyContent: "flex-start", marginTop: 28 }}>
                <Link href="/signin" className="fc-button fc-button-primary">
                  Continue with GitHub
                </Link>
                <Link href="/terms" className="fc-button fc-button-ghost">
                  Terms
                </Link>
              </div>
            </Card>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

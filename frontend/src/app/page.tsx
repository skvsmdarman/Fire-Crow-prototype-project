import Link from "next/link";
import { SiteHeader, SiteFooter } from "../components/SiteChrome";

export default function HomePage() {
  return (
    <div className="fc-page page-with-island" style={{ position: "relative", overflow: "hidden" }}>
      <SiteHeader />

      {/* Ambient background orbs */}
      <div className="hero-orb-1" />
      <div className="hero-orb-2" />
      <div className="hero-orb-3" />

      <main>
        {/* ── HERO ── */}
        <section className="fc-shell fc-hero" style={{ textAlign: "center", paddingTop: 80, paddingBottom: 60 }}>

          {/* Live badge */}
          <div style={{ display: "flex", justifyContent: "center" }}>
            <span className="hero-badge">
              <span className="hero-badge-dot" />
              Nova Devs · AI Security Platform
            </span>
          </div>

          <h1 style={{ fontSize: "clamp(2.6rem, 6.5vw, 5rem)", lineHeight: 1.04, marginBottom: 24, fontWeight: 700, letterSpacing: "-0.02em" }}>
            Code security reviews,{" "}
            <br />
            <span className="fc-gradient-text">made effortless.</span>
          </h1>

          <p className="fc-copy" style={{ fontSize: "1.15rem", maxWidth: 600, margin: "0 auto", color: "var(--text-dim)", lineHeight: 1.75 }}>
            Scan repositories for vulnerabilities, get plain-English explanations,
            and generate client-ready reports — no pipeline config required.
          </p>

          {/* CTAs */}
          <div className="hero-cta-row">
            <Link
              href="/signup"
              className="fc-button fc-button-primary"
              style={{ fontSize: "1rem", padding: "0 32px", minHeight: 50 }}
            >
              Start for free →
            </Link>
            <Link
              href="/signin"
              className="fc-button fc-button-secondary"
              style={{ fontSize: "1rem", padding: "0 28px", minHeight: 50 }}
            >
              Sign in
            </Link>
          </div>

          {/* Trust chips */}
          <div className="trust-strip">
            {["No credit card required", "Sandboxed execution", "End-to-end encrypted"].map((t) => (
              <span key={t} className="trust-chip">
                <span className="trust-chip-dot" />
                {t}
              </span>
            ))}
          </div>

          {/* Stats */}
          <div className="stat-strip">
            {[
              { value: "99%", label: "Uptime SLA" },
              { value: "< 5 min", label: "Avg scan time" },
              { value: "0 KB", label: "Code stored" },
              { value: "SOC2", label: "Compliant" },
            ].map((s) => (
              <div key={s.label} className="stat-item">
                <span className="stat-value">{s.value}</span>
                <span className="stat-label">{s.label}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ── FEATURES ── */}
        <section id="features" className="fc-shell" style={{ paddingBottom: 80 }}>
          <div style={{ textAlign: "center", marginBottom: 52 }}>
            <div className="fc-kicker">What we offer</div>
            <h2 style={{ fontFamily: "var(--font-display), sans-serif", fontSize: "clamp(1.6rem, 3vw, 2.4rem)", marginTop: 10, letterSpacing: "0.01em" }}>
              Real security value, zero complexity
            </h2>
          </div>

          <div className="fc-grid-3">
            {[
              {
                icon: "⚡",
                tone: "feat-icon--fire",
                title: "Scan in One Click",
                copy: "Connect via GitHub or Google. Run checks for vulnerabilities and dangerous secrets instantly — no config files, no setup commands.",
              },
              {
                icon: "🔍",
                tone: "feat-icon--cyan",
                title: "Understandable Findings",
                copy: "We translate dry scanner output into clear, human-readable explanations. Understand the risk and exactly how to fix it.",
              },
              {
                icon: "📄",
                tone: "feat-icon--green",
                title: "Client-Ready Reports",
                copy: "Export clean PDF or HTML reports to share with clients and management. Evidence-backed, prioritised, professional.",
              },
            ].map((f) => (
              <div key={f.title} className="glass-feature">
                <div className={`feat-icon ${f.tone}`}>{f.icon}</div>
                <h3 style={{ fontFamily: "var(--font-display), sans-serif", fontSize: "1.2rem", marginBottom: 12, letterSpacing: "0.01em" }}>
                  {f.title}
                </h3>
                <p className="fc-copy" style={{ fontSize: "0.93rem", margin: 0 }}>{f.copy}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── HOW IT WORKS ── */}
        <section id="how-it-works" className="fc-shell" style={{ paddingBottom: 80 }}>
          <div style={{ textAlign: "center", marginBottom: 52 }}>
            <div className="fc-kicker">How it works</div>
            <h2 style={{ fontFamily: "var(--font-display), sans-serif", fontSize: "clamp(1.6rem, 3vw, 2.4rem)", marginTop: 10 }}>
              Three steps to a secure codebase
            </h2>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 20 }}>
            {[
              { step: "01", title: "Connect your repo", copy: "Sign in with GitHub or Google. Paste your repo URL or select from your connected repos." },
              { step: "02", title: "Run the scan", copy: "Fire Crow spins up a sandboxed environment and runs multi-layer security analysis automatically." },
              { step: "03", title: "Get your report", copy: "Receive a prioritised findings list with plain-English explanations and a client-ready PDF report." },
            ].map((s) => (
              <div key={s.step} className="glass-card" style={{ padding: "32px 28px" }}>
                <div style={{ fontFamily: "var(--font-display), sans-serif", fontSize: "2.8rem", fontWeight: 700, color: "rgba(255,107,26,0.25)", marginBottom: 12, letterSpacing: "-0.02em" }}>
                  {s.step}
                </div>
                <h3 style={{ fontFamily: "var(--font-display), sans-serif", fontSize: "1.15rem", marginBottom: 10, letterSpacing: "0.01em" }}>{s.title}</h3>
                <p className="fc-copy" style={{ fontSize: "0.92rem", margin: 0 }}>{s.copy}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── TRUST ── */}
        <section id="trust" className="fc-shell" style={{ paddingBottom: 100 }}>
          <div className="glass-card" style={{ maxWidth: 900, margin: "0 auto", padding: "48px 44px" }}>
            <div style={{ display: "flex", gap: 32, alignItems: "flex-start", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <div className="fc-kicker" style={{ marginBottom: 12 }}>Privacy First</div>
                <h2 style={{ fontFamily: "var(--font-display), sans-serif", fontSize: "clamp(1.4rem, 2.5vw, 2rem)", marginBottom: 16, letterSpacing: "0.01em" }}>
                  Your code is fully protected
                </h2>
                <p className="fc-copy" style={{ fontSize: "1rem", lineHeight: 1.75, marginBottom: 28 }}>
                  Fire Crow analyses code in transient sandbox environments. We never store copies of your source code, never train on it, and never share it. All reports and credentials are encrypted and scoped strictly to your workspace.
                </p>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                  <Link className="fc-button fc-button-primary" href="/privacy">View Privacy Policy</Link>
                  <Link className="fc-button fc-button-ghost" href="/terms">Terms of Use</Link>
                </div>
              </div>

              <div style={{ display: "grid", gap: 14, minWidth: 220 }}>
                {[
                  { icon: "🔒", label: "End-to-end encryption" },
                  { icon: "🏗️", label: "Sandboxed execution" },
                  { icon: "🚫", label: "Zero code retention" },
                  { icon: "📋", label: "GDPR & DPDPA compliant" },
                ].map((item) => (
                  <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderRadius: 14, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", fontSize: "0.9rem", color: "var(--text-dim)" }}>
                    <span>{item.icon}</span>
                    {item.label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── FINAL CTA ── */}
        <section className="fc-shell" style={{ paddingBottom: 100, textAlign: "center" }}>
          <div style={{ maxWidth: 580, margin: "0 auto" }}>
            <h2 style={{ fontFamily: "var(--font-display), sans-serif", fontSize: "clamp(1.8rem, 4vw, 2.8rem)", marginBottom: 16, letterSpacing: "-0.01em" }}>
              Ready to secure your codebase?
            </h2>
            <p className="fc-copy" style={{ fontSize: "1.05rem", marginBottom: 32 }}>
              Get started free in seconds. No credit card. No setup.
            </p>
            <div className="hero-cta-row" style={{ marginTop: 0 }}>
              <Link href="/signup" className="fc-button fc-button-primary" style={{ fontSize: "1.05rem", padding: "0 36px", minHeight: 52 }}>
                Create free account →
              </Link>
              <Link href="/signin" className="fc-button fc-button-secondary" style={{ fontSize: "1.05rem", padding: "0 28px", minHeight: 52 }}>
                Sign in
              </Link>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

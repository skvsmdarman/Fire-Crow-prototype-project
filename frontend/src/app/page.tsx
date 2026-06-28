import Link from "next/link";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { HeroTerminal, MarketingSection, SiteFooter, SiteHeader } from "../components/SiteChrome";

const capabilities = [
  {
    title: "Reports clients can actually read",
    body: "Turn raw findings into clean summaries, clear severity labels, and next-step guidance your clients can act on quickly.",
  },
  {
    title: "Evidence that backs every claim",
    body: "Give engineering teams the proof behind each issue so remediation starts with confidence instead of debate.",
  },
  {
    title: "One workspace for every stakeholder",
    body: "Keep security leads, developers, and clients aligned around the same live run, report, and status view.",
  },
];

const workflowStages = [
  "Sign in with GitHub or Google",
  "Launch an authorized repository review",
  "Share findings, reports, and remediation priorities",
];

export default function HomePage() {
  return (
    <div className="fc-page">
      <SiteHeader />
      <main>
        <section className="fc-shell fc-hero">
          <div className="fc-hero-grid">
            <Card className="fc-panel">
              <div className="fc-kicker">Security reviews for real client work</div>
              <h1>
                Showcase your security work with <span className="fc-gradient-text">clarity, speed, and proof</span>.
              </h1>
              <p className="fc-copy" style={{ marginTop: 18, maxWidth: 720 }}>
                Fire Crow helps teams review repositories, surface the highest-risk issues, and deliver polished findings without exposing
                clients to internal tooling noise or overly technical dashboards.
              </p>
              <div className="fc-chip-row" style={{ marginTop: 22 }}>
                <Badge tone="success">GitHub + Google sign-in</Badge>
                <Badge tone="info">Live progress</Badge>
                <Badge tone="warning">Client-ready reporting</Badge>
              </div>
              <div className="fc-meta-grid">
                <Card className="fc-metric">
                  <div className="fc-muted">Best for</div>
                  <span className="fc-metric-value">Security teams</span>
                </Card>
                <Card className="fc-metric">
                  <div className="fc-muted">Experience</div>
                  <span className="fc-metric-value">Simple handoff</span>
                </Card>
                <Card className="fc-metric">
                  <div className="fc-muted">Outcome</div>
                  <span className="fc-metric-value">Faster remediation</span>
                </Card>
              </div>
              <div className="fc-chip-row" style={{ marginTop: 24 }}>
                <Link className="fc-button fc-button-primary" href="/signin">
                  Get started
                </Link>
                <Link className="fc-button fc-button-secondary" href="/#features">
                  Explore features
                </Link>
              </div>
            </Card>
            <HeroTerminal />
          </div>
        </section>

        <section id="features">
        <MarketingSection
          kicker="Features"
          title="Built to present value, not backend noise"
          copy="The product story now centers on client outcomes: understandable reports, trustworthy evidence, and a guided path from review kickoff to remediation."
        >
          <div className="fc-card-grid">
            {capabilities.map((item) => (
              <Card className="fc-panel" key={item.title}>
                <div className="fc-panel-title" style={{ fontSize: "1.15rem", marginBottom: 10 }}>
                  {item.title}
                </div>
                <div className="fc-copy">{item.body}</div>
              </Card>
            ))}
          </div>
        </MarketingSection>
        </section>

        <section id="how-it-works">
        <MarketingSection
          kicker="How it works"
          title="A simpler path from sign-in to shared report"
          copy="Clients and internal teams should understand the journey at a glance: connect, review, and share outcomes without learning the whole engine underneath."
        >
          <div className="fc-grid-3">
            {workflowStages.map((stage, index) => (
              <Card className="fc-panel" key={stage}>
                <div className="fc-kicker">Phase {index + 1}</div>
                <div className="fc-panel-title" style={{ marginTop: 10, fontSize: "1.18rem" }}>
                  {stage}
                </div>
              </Card>
            ))}
          </div>
        </MarketingSection>
        </section>

        <section id="trust">
          <MarketingSection
            kicker="Trust"
            title="Designed for polished delivery"
            copy="Behind the scenes Fire Crow keeps the deeper operational detail, but the customer-facing surface stays focused on confidence, accountability, and decision-ready output."
          >
            <div className="fc-grid-3">
              <Card className="fc-panel">
                <div className="fc-kicker">Access</div>
                <div className="fc-panel-title" style={{ marginTop: 10, fontSize: "1.18rem" }}>
                  GitHub and Google sign-in
                </div>
                <div className="fc-copy" style={{ marginTop: 10 }}>
                  Authentication is centered around familiar OAuth providers instead of exposing extra login mechanics to clients.
                </div>
              </Card>
              <Card className="fc-panel">
                <div className="fc-kicker">Collaboration</div>
                <div className="fc-panel-title" style={{ marginTop: 10, fontSize: "1.18rem" }}>
                  One narrative across teams
                </div>
                <div className="fc-copy" style={{ marginTop: 10 }}>
                  Keep security, engineering, and client stakeholders aligned with a shared view of progress and outcomes.
                </div>
              </Card>
              <Card className="fc-panel">
                <div className="fc-kicker">Delivery</div>
                <div className="fc-panel-title" style={{ marginTop: 10, fontSize: "1.18rem" }}>
                  Reports that are ready to present
                </div>
                <div className="fc-copy" style={{ marginTop: 10 }}>
                  Move from audit activity to a presentable output without forcing clients through low-level telemetry first.
                </div>
              </Card>
            </div>
          </MarketingSection>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

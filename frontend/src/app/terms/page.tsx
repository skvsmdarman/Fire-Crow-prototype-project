"use client";

import Link from "next/link";
import { PolicyPageTracker } from "../../components/PolicyTelemetry";
import { SiteFooter, SiteHeader } from "../../components/SiteChrome";
import { Card } from "../../components/ui/Card";
import { termsSections } from "../../lib/legal-content";

const VERSION = "2026-06-06";

export default function TermsPage() {
  return (
    <div className="fc-page">
      <PolicyPageTracker policy="terms" version={VERSION} source="terms_page" />
      <SiteHeader ctaHref="/signin" ctaLabel="Sign in" />
      <main className="fc-shell" style={{ padding: "54px 0 42px" }}>
        <Card className="fc-panel">
          <div className="fc-kicker">Terms of use</div>
          <h1 className="fc-title-xl" style={{ marginTop: 12 }}>
            Only scan what you are authorized to test.
          </h1>
          <p className="fc-copy" style={{ maxWidth: 760 }}>
            Fire Crow’s frontend now treats authorization attestation and workspace accountability as first-class product behavior, not
            fine print. These terms mirror that operating model.
          </p>
          <div className="fc-chip-row" style={{ marginTop: 18 }}>
            <Link className="fc-button fc-button-secondary" href="/privacy">
              Read Privacy Policy
            </Link>
            <Link className="fc-button fc-button-primary" href="/signin">
              Return to console
            </Link>
          </div>
        </Card>

        <section className="fc-section">
          <div className="fc-legal-list">
            {termsSections.map((section) => (
              <Card className="fc-panel" key={section.title}>
                <h2 className="fc-panel-title" style={{ fontSize: "1.2rem", marginBottom: 10 }}>
                  {section.title}
                </h2>
                <div className="fc-copy">{section.body}</div>
              </Card>
            ))}
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

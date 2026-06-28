"use client";

import Link from "next/link";
import { PolicyPageTracker } from "../../components/PolicyTelemetry";
import { SiteFooter, SiteHeader } from "../../components/SiteChrome";
import { Card } from "../../components/ui/Card";
import { privacySections } from "../../lib/legal-content";

const VERSION = "2026-06-06";

export default function PrivacyPage() {
  return (
    <div className="fc-page">
      <PolicyPageTracker policy="privacy_policy" version={VERSION} source="privacy_page" />
      <SiteHeader ctaHref="/signin" ctaLabel="Sign in" />
      <main className="fc-shell" style={{ padding: "54px 0 42px" }}>
        <Card className="fc-panel">
          <div className="fc-kicker">Privacy policy</div>
          <h1 className="fc-title-xl" style={{ marginTop: 12 }}>
            Data handling for authorized scanning.
          </h1>
          <p className="fc-copy" style={{ maxWidth: 760 }}>
            This page is aligned to the current backend model: workspace authentication, policy-event logging, Neon-backed artifacts, and
            database-scoped access controls rather than external object storage assumptions.
          </p>
          <div className="fc-chip-row" style={{ marginTop: 18 }}>
            <Link className="fc-button fc-button-secondary" href="/terms">
              Read Terms
            </Link>
            <Link className="fc-button fc-button-primary" href="/signin">
              Return to console
            </Link>
          </div>
        </Card>

        <section className="fc-section">
          <div className="fc-legal-list">
            {privacySections.map((section) => (
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

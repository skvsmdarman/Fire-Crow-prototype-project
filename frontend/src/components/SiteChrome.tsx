import Link from "next/link";
import { ReactNode } from "react";
import { Badge } from "./ui/Badge";
import { Card } from "./ui/Card";

export function SiteHeader({
  ctaHref = "/signin",
  ctaLabel = "Get Started",
}: {
  ctaHref?: string;
  ctaLabel?: string;
}) {
  return (
    <header className="fc-topbar">
      <div className="fc-shell fc-topbar-inner">
        <Link href="/" className="fc-brand" aria-label="Fire Crow home">
          <span className="fc-brand-mark">FC</span>
          <span>
            <span className="fc-brand-kicker">AI security review</span>
            <span className="fc-brand-title">Fire Crow</span>
          </span>
        </Link>
        <nav className="fc-nav" aria-label="Primary">
          <Link className="fc-nav-link" href="/#features">
            Features
          </Link>
          <Link className="fc-nav-link" href="/#how-it-works">
            How it works
          </Link>
          <Link className="fc-nav-link" href="/#trust">
            Trust
          </Link>
          <Link className="fc-nav-link" href="/terms">
            Terms
          </Link>
          <Link className="fc-nav-link" href="/privacy">
            Privacy
          </Link>
          <Link className="fc-button fc-button-primary" href={ctaHref}>
            {ctaLabel}
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="fc-shell fc-footer">
      <div>
        <div className="fc-brand" style={{ marginBottom: 8 }}>
          <span className="fc-brand-mark">FC</span>
          <span>
            <span className="fc-brand-kicker">Security that ships with clarity</span>
            <span className="fc-brand-title">Fire Crow</span>
          </span>
        </div>
        <div className="fc-muted">Share clear findings, prioritized fixes, and client-ready reports without turning every review into a manual fire drill.</div>
      </div>
      <div className="fc-footer-links">
        <Link href="/signin">Sign in</Link>
        <Link href="/signup">Create account</Link>
        <Link href="/#features">Features</Link>
        <Link href="/#how-it-works">How it works</Link>
        <Link href="/terms">Terms</Link>
        <Link href="/privacy">Privacy</Link>
      </div>
    </footer>
  );
}

export function HeroTerminal() {
  return (
    <Card className="fc-panel">
      <div className="fc-stack-between" style={{ marginBottom: 14 }}>
        <div>
          <div className="fc-kicker">Client snapshot</div>
          <h2 className="fc-panel-title">What teams get in one workspace</h2>
        </div>
        <Badge tone="success">Live</Badge>
      </div>
      <div className="fc-stream" aria-label="Runtime preview">
        <div className="fc-terminal-line">Executive summary: the top risks and what to fix first</div>
        <div className="fc-terminal-line">Evidence-backed findings: every issue tied to concrete proof</div>
        <div className="fc-terminal-line">Shareable reports: ready for engineering, leadership, and clients</div>
        <div className="fc-terminal-line">Team visibility: watch progress as audits move from launch to report</div>
        <div className="fc-terminal-line">OAuth access: sign in with GitHub or Google in a few clicks</div>
      </div>
    </Card>
  );
}

export function MarketingSection({
  kicker,
  title,
  copy,
  children,
}: {
  kicker: string;
  title: string;
  copy: string;
  children: ReactNode;
}) {
  return (
    <section className="fc-section">
      <div className="fc-shell">
        <div className="fc-section-head">
          <div>
            <div className="fc-kicker">{kicker}</div>
            <h2 className="fc-section-title fc-title-md">{title}</h2>
          </div>
          <div className="fc-copy" style={{ maxWidth: 560 }}>
            {copy}
          </div>
        </div>
        {children}
      </div>
    </section>
  );
}

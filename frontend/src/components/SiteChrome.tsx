"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { Badge } from "./ui/Badge";
import { Card } from "./ui/Card";

export function SiteHeader({
  ctaHref = "/signin",
  ctaLabel = "Get Started",
}: {
  ctaHref?: string;
  ctaLabel?: string;
}) {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const links = [
    { href: "/#features", label: "Features" },
    { href: "/#how-it-works", label: "How it works" },
    { href: "/#trust", label: "Privacy" },
  ];

  return (
    <div className={`di-wrapper ${scrolled ? "di-wrapper--scrolled" : ""}`}>
      <nav className={`di-island ${scrolled ? "di-island--compact" : ""}`} aria-label="Primary">
        {/* Brand */}
        <Link href="/" className="di-brand" aria-label="Fire Crow home">
          <span className="di-brand-mark">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" fill="url(#fire-grad-site)" />
              <defs>
                <linearGradient id="fire-grad-site" x1="0" y1="0" x2="24" y2="24">
                  <stop offset="0%" stopColor="#ff9b54" />
                  <stop offset="100%" stopColor="#6ce7ff" />
                </linearGradient>
              </defs>
            </svg>
          </span>
          <span className="di-brand-name">Fire Crow</span>
        </Link>

        {/* Center links */}
        <div className="di-links" role="list">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`di-link ${pathname === l.href ? "di-link--active" : ""}`}
            >
              {l.label}
            </Link>
          ))}
        </div>

        {/* CTA */}
        <div className="di-actions">
          {ctaHref === "/signin" && (
            <Link href="/signin" className="di-cta-ghost">Sign in</Link>
          )}
          <Link href={ctaHref} className="di-cta-pill">
            {ctaLabel}
          </Link>
        </div>

        {/* Mobile burger */}
        <button
          className="di-burger"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
        >
          <span className={`di-burger-bar ${menuOpen ? "di-burger-bar--top-open" : ""}`} />
          <span className={`di-burger-bar ${menuOpen ? "di-burger-bar--mid-open" : ""}`} />
          <span className={`di-burger-bar ${menuOpen ? "di-burger-bar--bot-open" : ""}`} />
        </button>
      </nav>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="di-drawer" onClick={() => setMenuOpen(false)}>
          {links.map((l) => (
            <Link key={l.href} href={l.href} className="di-drawer-link">{l.label}</Link>
          ))}
          <hr className="di-drawer-divider" />
          <Link href="/signin" className="di-drawer-link">Sign in</Link>
          <Link href={ctaHref} className="di-drawer-cta">{ctaLabel} →</Link>
        </div>
      )}
    </div>
  );
}

export function SiteFooter() {
  return (
    <footer className="fc-shell fc-footer" style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 40, marginTop: 60, paddingBottom: 40 }}>
      <div>
        <div className="di-brand" style={{ marginBottom: 8 }}>
          <span className="di-brand-mark">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" fill="url(#footer-fire-site)" />
              <defs>
                <linearGradient id="footer-fire-site" x1="0" y1="0" x2="24" y2="24">
                  <stop offset="0%" stopColor="#ff9b54" />
                  <stop offset="100%" stopColor="#6ce7ff" />
                </linearGradient>
              </defs>
            </svg>
          </span>
          <span className="di-brand-name" style={{ fontSize: "0.95rem" }}>Fire Crow</span>
        </div>
        <div className="fc-muted" style={{ maxWidth: 450, fontSize: "0.9rem", lineHeight: "1.6" }}>
          Automated code security scanning, clear explanations, and client-ready reports built for modern teams by <strong>Nova Devs</strong>.
        </div>
        <div className="fc-muted" style={{ marginTop: 12, fontSize: "0.8rem" }}>
          © {new Date().getFullYear()} Nova Devs. All rights reserved.
        </div>
      </div>
      <div className="fc-footer-links">
        <Link href="/signin">Sign in</Link>
        <Link href="/signup">Create account</Link>
        <Link href="/#features">Features</Link>
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

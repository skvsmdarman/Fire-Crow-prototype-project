"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { persistSession } from "../../lib/auth-session";
import { buildApiUrl } from "../../lib/base-url";
import { useAuthActions, GuestGuard } from "../../lib/auth-context";
import { request, ApiError } from "../../lib/request";
import { PolicyContext, AuthTokenResponse } from "../../lib/types";
import styles from "./AuthConsole.module.css";

const FALLBACK_VERSION = "2026-06-06";

/* ─── helpers ─────────────────────────────────────────────────────── */

function detectRegion(tz: string) {
  if (tz.startsWith("Europe/")) return "eu";
  if (tz.startsWith("Asia/")) return "apac";
  if (tz.startsWith("America/")) return "us";
  return undefined;
}

function buildOAuthUrl(provider: "github" | "google", version: string): string {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const params = new URLSearchParams({
    privacy_policy_accepted: "true",
    privacy_policy_version: version,
  });
  if (tz) params.set("timezone", tz);
  const region = detectRegion(tz);
  if (region) params.set("region", region);
  return `${buildApiUrl(`/auth/${provider}`)}?${params.toString()}`;
}

/* ─── icon SVGs ────────────────────────────────────────────────────── */

function GitHubIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden>
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

function LoaderRing() {
  return <span className={styles.ring} role="status" aria-label="Loading" />;
}

/* ─── main component ───────────────────────────────────────────────── */

export function AuthConsole({ mode }: { mode: "signin" | "signup" }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loadPolicyContext, refresh } = useAuthActions();

  const [ctx, setCtx] = useState<PolicyContext | null>(null);
  const [ctxLoading, setCtxLoading] = useState(true);
  const [accepted, setAccepted] = useState(false);
  const [validating, setValidating] = useState(() => Boolean(searchParams.get("code")));
  const [error, setError] = useState<string | null>(null);
  const [hoveredProvider, setHoveredProvider] = useState<string | null>(null);

  const version = ctx?.privacy_policy_version ?? FALLBACK_VERSION;
  const isSignIn = mode === "signin";

  /* load policy context */
  useEffect(() => {
    let live = true;
    void (async () => {
      const c = await loadPolicyContext();
      if (live) {
        setCtx(c);
        setCtxLoading(false);
      }
    })();
    return () => { live = false; };
  }, [loadPolicyContext]);

  /* handle OAuth code exchange */
  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) return;
    let live = true;
    void (async () => {
      try {
        const res = await request<AuthTokenResponse>("/auth/exchange", { method: "POST", body: { code } });
        if (!live) return;
        persistSession(res);
        await refresh();
        router.replace("/dashboard");
      } catch (err: unknown) {
        if (!live) return;
        setError(err instanceof ApiError ? err.message : "OAuth validation failed. Please try again.");
        setValidating(false);
      }
    })();
    return () => { live = false; };
  }, [router, searchParams, refresh]);

  const providers = [
    {
      id: "github" as const,
      label: "GitHub",
      Icon: GitHubIcon,
      tagline: isSignIn ? "Continue with GitHub" : "Sign up with GitHub",
      description: "For engineering-led teams. Seamlessly connect your repositories.",
      available: Boolean(ctx?.providers.github),
      accentColor: "#6e40c9",
    },
    {
      id: "google" as const,
      label: "Google",
      Icon: GoogleIcon,
      tagline: isSignIn ? "Continue with Google" : "Sign up with Google",
      description: "For organisations using Google Workspace or personal Gmail.",
      available: Boolean(ctx?.providers.google),
      accentColor: "#4285F4",
    },
  ];

  return (
    <GuestGuard>
      <div className={styles.page}>
      {/* ── background blobs ── */}
      <div className={styles.blob1} aria-hidden />
      <div className={styles.blob2} aria-hidden />
      <div className={styles.grid} aria-hidden />

      {/* ── top nav ── */}
      <header className={styles.topbar}>
        <Link href="/" className={styles.brand} aria-label="Fire Crow home">
          <span className={styles.brandMark}>FC</span>
          <span className={styles.brandText}>Fire Crow</span>
        </Link>
        <nav className={styles.topNav}>
          <Link href="/privacy" className={styles.navLink}>Privacy</Link>
          <Link href="/terms" className={styles.navLink}>Terms</Link>
          {isSignIn ? (
            <Link href="/signup" className={styles.navCta}>Create account</Link>
          ) : (
            <Link href="/signin" className={styles.navCta}>Sign in</Link>
          )}
        </nav>
      </header>

      {/* ── main ── */}
      <main className={styles.main}>
        <div className={styles.shell}>

          {/* left: copy */}
          <aside className={styles.aside}>
            <p className={styles.asideKicker}>
              {isSignIn ? "Welcome back" : "Get started free"}
            </p>
            <h1 className={styles.asideTitle}>
              {isSignIn
                ? "Sign in to your workspace"
                : "Create your Fire Crow account"}
            </h1>
            <p className={styles.asideCopy}>
              {isSignIn
                ? "Access your security audits, findings, and client-ready reports in seconds."
                : "Automated code security scanning that speaks plain English. Built for teams."}
            </p>

            <ul className={styles.trustList} role="list">
              {[
                "Code is sandboxed — never stored or trained on",
                "End-to-end encrypted reports",
                "Cancel any time, no commitment",
              ].map((item) => (
                <li key={item} className={styles.trustItem}>
                  <span className={styles.trustCheck}><CheckIcon /></span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            <div className={styles.asideFootnote}>
              <ShieldIcon />
              <span>Privacy-first by design. <Link href="/privacy" className={styles.footLink}>See how →</Link></span>
            </div>
          </aside>

          {/* right: card */}
          <section className={styles.card} aria-label={isSignIn ? "Sign in" : "Create account"}>
            <div className={styles.cardInner}>

              {/* heading */}
              <div className={styles.cardHead}>
                <span className={styles.cardKicker}>
                  {isSignIn ? "Secure access" : "Account setup"}
                </span>
                <h2 className={styles.cardTitle}>
                  {isSignIn ? "Sign In" : "Create Account"}
                </h2>
              </div>

              {/* status banners */}
              {error && (
                <div className={styles.bannerError} role="alert">
                  <span>⚠</span> {error}
                </div>
              )}
              {validating && !error && (
                <div className={styles.bannerSuccess} role="status">
                  <LoaderRing />
                  <span>Verifying with your provider and opening your workspace…</span>
                </div>
              )}

              {/* policy consent */}
              <label className={styles.consent}>
                <span className={styles.checkboxWrap}>
                  <input
                    type="checkbox"
                    checked={accepted}
                    onChange={(e) => setAccepted(e.target.checked)}
                    className={styles.checkbox}
                    id="auth-consent"
                  />
                  <span className={styles.checkboxBox} aria-hidden>
                    {accepted && <CheckIcon />}
                  </span>
                </span>
                <span className={styles.consentText}>
                  I agree to the{" "}
                  <Link href="/terms" className={styles.consentLink} target="_blank" rel="noopener noreferrer">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link href="/privacy" className={styles.consentLink} target="_blank" rel="noopener noreferrer">
                    Privacy Policy
                  </Link>
                </span>
              </label>

              {/* provider buttons */}
              <div className={styles.providers}>
                {ctxLoading ? (
                  <div className={styles.providerSkeleton}>
                    <LoaderRing /> <span className={styles.loadingText}>Loading providers…</span>
                  </div>
                ) : (
                  providers.map((p) => {
                    const canClick = p.available && accepted && !validating;
                    const href = canClick ? buildOAuthUrl(p.id, version) : undefined;
                    const isHovered = hoveredProvider === p.id;

                    return (
                      <div key={p.id} className={styles.providerRow}>
                        {href ? (
                          <a
                            href={href}
                            className={`${styles.providerBtn} ${isHovered ? styles.providerBtnHover : ""}`}
                            onMouseEnter={() => setHoveredProvider(p.id)}
                            onMouseLeave={() => setHoveredProvider(null)}
                            aria-label={p.tagline}
                          >
                            <span className={styles.providerIcon}><p.Icon /></span>
                            <span className={styles.providerLabel}>{p.tagline}</span>
                            <span className={styles.providerArrow}><ArrowIcon /></span>
                          </a>
                        ) : (
                          <span
                            className={`${styles.providerBtn} ${styles.providerBtnDisabled}`}
                            aria-disabled="true"
                            title={
                              !p.available
                                ? `${p.label} sign-in is not configured`
                                : "Accept the terms to continue"
                            }
                          >
                            <span className={styles.providerIcon}><p.Icon /></span>
                            <span className={styles.providerLabel}>
                              {!p.available ? `${p.label} (not configured)` : p.tagline}
                            </span>
                          </span>
                        )}
                        <p className={styles.providerDesc}>{p.description}</p>
                      </div>
                    );
                  })
                )}
              </div>

              {/* divider */}
              <div className={styles.divider}>
                <span>More sign-in options coming soon</span>
              </div>

              {/* alt link */}
              <p className={styles.altText}>
                {isSignIn ? "New to Fire Crow?" : "Already have an account?"}{" "}
                <Link href={isSignIn ? "/signup" : "/signin"} className={styles.altLink}>
                  {isSignIn ? "Create an account →" : "Sign in instead →"}
                </Link>
              </p>
            </div>

            {/* bottom strip */}
            <div className={styles.cardFooter}>
              <ShieldIcon />
              <span>Connection secured · Your code is never stored or shared</span>
            </div>
          </section>
        </div>
      </main>
    </div>
    </GuestGuard>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthProvider, useAuthActions, useAuthState } from "../../lib/auth-context";
import { persistSession } from "../../lib/auth-session";
import { buildApiUrl } from "../../lib/base-url";
import { ApiError, request } from "../../lib/request";
import { AuthTokenResponse, PolicyContext } from "../../lib/types";
import { Card } from "../ui/Card";
import styles from "./AuthConsole.module.css";

const FALLBACK_VERSION = "2026-06-06";

type AuthMode = "signin" | "signup";

interface AuthConsoleProps {
  mode: AuthMode;
}

function detectRegion(tz: string) {
  if (tz.startsWith("Europe/")) return "eu";
  if (tz.startsWith("Asia/")) return "apac";
  if (tz.startsWith("America/")) return "us";
  return undefined;
}

function buildGitHubOAuthUrl(version: string) {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const params = new URLSearchParams({
    privacy_policy_accepted: "true",
    privacy_policy_version: version,
  });

  if (timezone) {
    params.set("timezone", timezone);
  }

  const region = detectRegion(timezone);
  if (region) {
    params.set("region", region);
  }

  return `${buildApiUrl("/auth/github")}?${params.toString()}`;
}

function resolveRedirectTarget(target: string | null): string {
  if (!target) {
    return "/dashboard";
  }

  try {
    const normalized = decodeURIComponent(target);
    if (!normalized.startsWith("/") || normalized.startsWith("//")) {
      return "/dashboard";
    }
    if (normalized.startsWith("/signin") || normalized.startsWith("/signup")) {
      return "/dashboard";
    }
    return normalized;
  } catch {
    return "/dashboard";
  }
}

function GitHubIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
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

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 6L9 17l-5-5" />
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

function LoaderRing() {
  return <span className={styles.ring} role="status" aria-label="Loading" />;
}

function AuthConsoleContent({ mode }: AuthConsoleProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { status } = useAuthState();
  const { loadPolicyContext } = useAuthActions();

  const [ctx, setCtx] = useState<PolicyContext | null>(null);
  const [policyLoading, setPolicyLoading] = useState(true);
  const [accepted, setAccepted] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [validating, setValidating] = useState(Boolean(searchParams.get("code")));

  const isSignIn = mode === "signin";
  const redirectTo = useMemo(() => resolveRedirectTarget(searchParams.get("redirect")), [searchParams]);
  const version = ctx?.privacy_policy_version ?? FALLBACK_VERSION;
  const githubAvailable = Boolean(ctx?.providers.github);

  useEffect(() => {
    let live = true;
    void (async () => {
      const next = await loadPolicyContext();
      if (!live) {
        return;
      }
      setCtx(next);
      setPolicyLoading(false);
    })();
    return () => {
      live = false;
    };
  }, [loadPolicyContext]);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(redirectTo);
    }
  }, [redirectTo, router, status]);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      return;
    }

    let live = true;
    void (async () => {
      try {
        const response = await request<AuthTokenResponse>("/auth/exchange", {
          method: "POST",
          body: { code },
        });
        if (!live) {
          return;
        }
        persistSession(response);
        router.replace(redirectTo);
      } catch (error) {
        if (!live) {
          return;
        }
        setFormError(error instanceof ApiError ? error.message : "GitHub sign-in could not be completed.");
        setValidating(false);
      }
    })();

    return () => {
      live = false;
    };
  }, [redirectTo, router, searchParams]);

  function startGitHubOAuth() {
    setFormError(null);

    if (!accepted) {
      setFormError("Accept the privacy policy and terms before continuing.");
      return;
    }

    if (!githubAvailable) {
      setFormError("GitHub sign-in is not configured on this environment.");
      return;
    }

    window.location.assign(buildGitHubOAuthUrl(version));
  }

  return (
    <div className={styles.page}>
      <div className={styles.blob1} aria-hidden />
      <div className={styles.blob2} aria-hidden />
      <div className={styles.grid} aria-hidden />

      <header className={styles.topbar}>
        <div className={styles.topbarInner}>
          <Link href="/" className={styles.brand} aria-label="Fire Crow home">
            <span className={styles.brandMark}>FC</span>
            <span className={styles.brandText}>Fire Crow</span>
          </Link>
          <nav className={styles.topNav} aria-label="Auth links">
            <Link href="/privacy" className={styles.navLink}>
              Privacy
            </Link>
            <Link href="/terms" className={styles.navLink}>
              Terms
            </Link>
            <Link href={isSignIn ? "/signup" : "/signin"} className={styles.navCta}>
              {isSignIn ? "Create account" : "Sign in"}
            </Link>
          </nav>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.shell}>
          <aside className={styles.aside}>
            <p className={styles.asideKicker}>Backend first</p>
            <h1 className={styles.asideTitle}>
              {isSignIn ? "One GitHub sign-in path." : "Create the workspace through GitHub."}
            </h1>
            <p className={styles.asideCopy}>
              Fire Crow now keeps authentication simple. GitHub is the only sign-in route, and the backend keeps the
              session, consent, and repository access flow in one place.
            </p>

            <div className="fc-grid-3" style={{ marginBottom: 28 }}>
              <Card className="fc-metric" style={{ padding: 18 }}>
                <div className="fc-muted">Auth path</div>
                <span className="fc-metric-value" style={{ fontSize: "1.35rem" }}>
                  GitHub
                </span>
                <div className="fc-copy">One provider, one session model.</div>
              </Card>
              <Card className="fc-metric" style={{ padding: 18 }}>
                <div className="fc-muted">Backend state</div>
                <span className="fc-metric-value" style={{ fontSize: "1.35rem" }}>
                  Live
                </span>
                <div className="fc-copy">Consent and session cookies are enforced server-side.</div>
              </Card>
              <Card className="fc-metric" style={{ padding: 18 }}>
                <div className="fc-muted">Repo access</div>
                <span className="fc-metric-value" style={{ fontSize: "1.35rem" }}>
                  Explicit
                </span>
                <div className="fc-copy">Permissions stay tied to GitHub scopes you approve.</div>
              </Card>
            </div>

            <ul className={styles.trustList} role="list">
              {[
                "No Google sign-in path remains in the auth flow.",
                "Audit access opens through the same backend session contract.",
                "Reports and findings stay scoped to the signed-in workspace.",
              ].map((item) => (
                <li key={item} className={styles.trustItem}>
                  <span className={styles.trustCheck}>
                    <CheckIcon />
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            <div className={styles.asideFootnote}>
              <ShieldIcon />
              <span>
                Plain auth flow. <Link href="/privacy" className={styles.footLink}>Review the policy</Link>
              </span>
            </div>
          </aside>

          <Card className={styles.card} aria-label={isSignIn ? "Sign in" : "Create account"}>
            <div className={styles.cardInner}>
              <div className={styles.cardHead}>
                <span className={styles.cardKicker}>{isSignIn ? "Secure access" : "Workspace setup"}</span>
                <h2 className={styles.cardTitle}>{isSignIn ? "Sign in with GitHub" : "Create workspace with GitHub"}</h2>
                <p className="fc-copy" style={{ margin: 0 }}>
                  {isSignIn
                    ? "Use GitHub to open the dashboard. The backend will exchange the OAuth code into the normal workspace session."
                    : "Use GitHub to create the workspace and move directly into the backend audit flow."}
                </p>
              </div>

              {formError ? (
                <div className={styles.bannerError} role="alert">
                  <span>⚠</span>
                  <span>{formError}</span>
                </div>
              ) : null}

              {validating ? (
                <div className={styles.bannerSuccess} role="status">
                  <LoaderRing />
                  <span>Finishing GitHub sign-in and opening your workspace…</span>
                </div>
              ) : null}

              {status === "loading" && !validating ? (
                <div className={styles.bannerSuccess} role="status">
                  <LoaderRing />
                  <span>Checking your current session…</span>
                </div>
              ) : null}

              <label className="fc-checkline">
                <span className={styles.checkboxWrap}>
                  <input
                    type="checkbox"
                    checked={accepted}
                    onChange={(event) => setAccepted(event.target.checked)}
                    className={styles.checkbox}
                  />
                  <span className={styles.checkboxBox} aria-hidden>
                    {accepted ? <CheckIcon /> : null}
                  </span>
                </span>
                <span>
                  I agree to the{" "}
                  <Link href="/terms" className={styles.consentLink} target="_blank" rel="noreferrer noopener">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link href="/privacy" className={styles.consentLink} target="_blank" rel="noreferrer noopener">
                    Privacy Policy
                  </Link>
                  .
                </span>
              </label>

              <div className={styles.providerRow}>
                <button
                  type="button"
                  className={`${styles.providerBtn} ${!githubAvailable || policyLoading || validating ? styles.providerBtnDisabled : ""}`.trim()}
                  onClick={startGitHubOAuth}
                  disabled={!githubAvailable || policyLoading || validating}
                  aria-label={isSignIn ? "Continue with GitHub" : "Create workspace with GitHub"}
                  title={githubAvailable ? "Continue with GitHub" : "GitHub sign-in is not configured"}
                >
                  <span className={styles.providerIcon}>
                    <GitHubIcon />
                  </span>
                  <span className={styles.providerLabel}>
                    {isSignIn ? "Continue with GitHub" : "Create workspace with GitHub"}
                  </span>
                  <span className={styles.providerArrow}>
                    <ArrowIcon />
                  </span>
                </button>
                <p className={styles.providerDesc}>
                  GitHub is the only sign-in path on this interface now. Google sign-in has been removed.
                </p>
              </div>

              <p className={styles.altText}>
                {isSignIn ? "Need a workspace?" : "Already connected before?"}{" "}
                <Link href={isSignIn ? "/signup" : "/signin"} className={styles.altLink}>
                  {isSignIn ? "Open the create page" : "Open the sign-in page"}
                </Link>
              </p>
            </div>

            <div className={styles.cardFooter}>
              <ShieldIcon />
              <span>GitHub OAuth in, cookie-backed workspace session out.</span>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}

export function AuthConsole({ mode }: AuthConsoleProps) {
  return (
    <AuthProvider>
      <AuthConsoleContent mode={mode} />
    </AuthProvider>
  );
}

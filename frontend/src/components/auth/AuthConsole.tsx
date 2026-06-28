"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { persistSession } from "../../lib/auth-session";
import { buildApiUrl } from "../../lib/base-url";
import { request, ApiError } from "../../lib/request";
import { PolicyContext, AuthTokenResponse } from "../../lib/types";
import { Card } from "../ui/Card";
import { SiteHeader, SiteFooter } from "../SiteChrome";
import { PolicyLink } from "../PolicyTelemetry";

const FALLBACK_PRIVACY_VERSION = "2026-06-06";

function detectRegion(timezone: string): string | undefined {
  if (timezone.startsWith("Europe/")) {
    return "eu";
  }
  if (timezone.startsWith("Asia/")) {
    return "apac";
  }
  if (timezone.startsWith("America/")) {
    return "us";
  }
  return undefined;
}

function buildOAuthUrl(provider: "github" | "google", version: string): string {
  const params = new URLSearchParams({
    privacy_policy_accepted: "true",
    privacy_policy_version: version,
  });

  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  if (timezone) {
    params.set("timezone", timezone);
  }

  const region = detectRegion(timezone);
  if (region) {
    params.set("region", region);
  }

  return `${buildApiUrl(`/auth/${provider}`)}?${params.toString()}`;
}

export function AuthConsole({ mode }: { mode: "signin" | "signup" }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [context, setContext] = useState<PolicyContext | null>(null);
  const [loadingContext, setLoadingContext] = useState(true);
  const [validatingCode, setValidatingCode] = useState(() => Boolean(searchParams.get("code")));

  // Credentials states
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [accepted, setAccepted] = useState(true);

  const activePrivacyVersion = context?.privacy_policy_version ?? FALLBACK_PRIVACY_VERSION;
  const activeTermsVersion = context?.terms_version ?? FALLBACK_PRIVACY_VERSION;

  useEffect(() => {
    let cancelled = false;

    async function loadContext() {
      try {
        const response = await request<PolicyContext>("/auth/policy-context");
        if (!cancelled) {
          setContext(response);
        }
      } catch {
        if (!cancelled) {
          setContext({
            privacy_policy_version: FALLBACK_PRIVACY_VERSION,
            terms_version: FALLBACK_PRIVACY_VERSION,
            providers: { github: false, google: false, password: false },
          });
        }
      } finally {
        if (!cancelled) {
          setLoadingContext(false);
        }
      }
    }

    void loadContext();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      return;
    }

    let cancelled = false;
    void request<AuthTokenResponse>("/auth/exchange", {
      method: "POST",
      body: { code },
    })
      .then((response) => {
        if (cancelled) {
          return;
        }
        persistSession(response);
        router.replace(`/dashboard?workspace=${encodeURIComponent(response.username)}`);
      })
      .catch((err: unknown) => {
        if (cancelled) {
          return;
        }
        const message = err instanceof ApiError ? err.message : "OAuth validation failed.";
        setError(message);
      })
      .finally(() => {
        if (!cancelled) {
          setValidatingCode(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [router, searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!accepted) {
      setError("Please accept the Terms and Privacy Policy to continue.");
      return;
    }

    if (!username.trim()) {
      setError("Workspace Name is required.");
      return;
    }

    if (!password) {
      setError("Password is required.");
      return;
    }

    if (mode === "signup" && password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setSubmitting(true);
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const region = detectRegion(timezone);

      const endpoint = mode === "signin" ? "/auth/login" : "/auth/register";
      const payload: Record<string, string | boolean | undefined> = {
        username: username.trim(),
        password,
        privacy_policy_accepted: true,
        privacy_policy_version: activePrivacyVersion,
      };

      if (timezone) payload.timezone = timezone;
      if (region) payload.region = region;
      if (mode === "signup" && email.trim()) {
        payload.email = email.trim();
      }

      const response = await request<AuthTokenResponse>(endpoint, {
        method: "POST",
        body: payload,
      });

      setSuccess(mode === "signin" ? "Signed in successfully!" : "Account created successfully!");
      persistSession(response);
      router.replace(`/dashboard?workspace=${encodeURIComponent(response.username)}`);
    } catch (err: unknown) {
      const message = err instanceof ApiError ? err.message : "Authentication failed.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const headline = mode === "signin" ? "Sign in to the provider your team already trusts." : "Create your Fire Crow account with one secure sign-in.";
  const description =
    mode === "signin"
      ? "Use GitHub, Google, or your workspace credentials to access your audits, review active tasks, and share outcomes securely."
      : "Start with GitHub, Google, or setup your workspace credentials, and Fire Crow will guide your team into a client-friendly security review experience.";

  const ctaLabel = mode === "signin" ? "Sign In" : "Create Account";
  const altHref = mode === "signin" ? "/signup" : "/signin";
  const altLabel = mode === "signin" ? "Need a new account? Create one" : "Already have access? Sign in";

  const providers = [
    {
      id: "github" as const,
      name: "GitHub",
      tone: "info" as const,
    },
    {
      id: "google" as const,
      name: "Google",
      tone: "success" as const,
    },
  ];

  return (
    <div className="fc-page">
      <SiteHeader />
      <main className="fc-auth-shell">
        <Card className="fc-auth-panel" style={{ paddingBottom: 32 }}>
          <div className="fc-kicker">{mode === "signin" ? "Secure access" : "Account setup"}</div>
          <h1 className="fc-title-xl" style={{ marginTop: 12, marginBottom: 18 }}>
            {headline}
          </h1>
          <p className="fc-copy" style={{ maxWidth: 540 }}>
            {description}
          </p>
          <div className="fc-divider" />
          <div className="fc-grid-2">
            <Card className="fc-metric">
              <div className="fc-muted">Client experience</div>
              <span className="fc-metric-value" style={{ fontSize: "1.5rem", marginTop: 6 }}>Simple Access</span>
              <div className="fc-copy" style={{ fontSize: "0.9rem", marginTop: 6 }}>
                Your clients and teammates start with familiar sign-in choices instead of separate workspace credentials.
              </div>
            </Card>
            <Card className="fc-metric">
              <div className="fc-muted">What happens next</div>
              <span className="fc-metric-value" style={{ fontSize: "1.5rem", marginTop: 6 }}>Guided Onboarding</span>
              <div className="fc-copy" style={{ fontSize: "0.9rem", marginTop: 6 }}>
                After provider verification, Fire Crow restores or creates the workspace session for you automatically.
              </div>
            </Card>
          </div>
        </Card>

        <Card className="fc-auth-panel">
          <div className="fc-panel-head" style={{ marginBottom: 12 }}>
            <div>
              <div className="fc-kicker">{mode === "signin" ? "Welcome back" : "Get started"}</div>
              <h2 className="fc-panel-title" style={{ marginTop: 4 }}>{ctaLabel}</h2>
            </div>
            {loadingContext ? <span className="fc-muted" style={{ fontSize: "0.8rem" }}>Loading...</span> : null}
          </div>

          {error ? <div className="fc-form-error" style={{ marginBottom: 16 }}>{error}</div> : null}
          {success ? <div className="fc-form-success" style={{ marginBottom: 16 }}>{success}</div> : null}
          {validatingCode ? (
            <div className="fc-form-success" style={{ marginBottom: 16 }}>
              Verifying OAuth exchange and restoring the workspace session...
            </div>
          ) : null}

          {/* Form for Credentials */}
          <form onSubmit={handleSubmit} className="fc-auth-form" style={{ display: "grid", gap: 14 }}>
            <div className="fc-field">
              <label className="fc-field-label" htmlFor="username">Workspace Name</label>
              <input
                id="username"
                type="text"
                className="fc-input"
                placeholder="e.g. acme_corp"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={submitting}
              />
            </div>

            {mode === "signup" && (
              <div className="fc-field">
                <label className="fc-field-label" htmlFor="email">Email Address (Optional)</label>
                <input
                  id="email"
                  type="email"
                  className="fc-input"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={submitting}
                />
              </div>
            )}

            <div className="fc-field">
              <label className="fc-field-label" htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                className="fc-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
              />
            </div>

            <label className="fc-checkline" style={{ marginTop: 4, cursor: "pointer" }}>
              <input
                checked={accepted}
                onChange={(event) => setAccepted(event.target.checked)}
                type="checkbox"
                disabled={submitting}
                style={{ cursor: "pointer" }}
              />
              <span>
                I accept the{" "}
                <PolicyLink href="/terms" policy="terms" version={activeTermsVersion} source={`${mode}_terms`}>
                  Terms
                </PolicyLink>{" "}
                and{" "}
                <PolicyLink href="/privacy" policy="privacy_policy" version={activePrivacyVersion} source={`${mode}_privacy`}>
                  Privacy Policy
                </PolicyLink>
                .
              </span>
            </label>

            <button
              type="submit"
              className="fc-button fc-button-primary"
              disabled={submitting || validatingCode}
              style={{ marginTop: 10, width: "100%", fontWeight: "600" }}
            >
              {submitting ? (
                <>
                  <span className="fc-button-spinner" style={{ marginRight: 8 }} />
                  {mode === "signin" ? "Signing In..." : "Creating Account..."}
                </>
              ) : (
                ctaLabel
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="fc-form-divider">
            <span>or continue with OAuth</span>
          </div>

          {/* Social Sign-In Buttons */}
          <div className="fc-oauth-buttons" style={{ display: "grid", gap: 10 }}>
            {providers.map((provider) => {
              const enabled = Boolean(context?.providers[provider.id]);
              const href = enabled && accepted ? buildOAuthUrl(provider.id, activePrivacyVersion) : undefined;

              return (
                <div key={provider.id}>
                  {href ? (
                    <a
                      className="fc-button fc-button-secondary"
                      href={href}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 10,
                        width: "100%",
                        padding: "12px 18px",
                      }}
                    >
                      {provider.id === "github" ? (
                        <svg className="fc-oauth-icon" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                        </svg>
                      ) : (
                        <svg className="fc-oauth-icon" viewBox="0 0 24 24" width="18" height="18">
                          <path
                            fill="#EA4335"
                            d="M12.24 10.285V14.4h6.887c-.648 2.41-2.519 4.114-5.137 4.114-3.355 0-6.075-2.72-6.075-6.075s2.72-6.075 6.075-6.075c1.497 0 2.868.543 3.93 1.44l3.075-3.075C19.065 2.25 15.855 1.05 12.24 1.05 6.045 1.05 1.05 6.045 1.05 12.24s4.995 11.19 11.19 11.19c5.805 0 10.74-4.155 10.74-11.19 0-.645-.06-1.29-.18-1.995H12.24z"
                          />
                        </svg>
                      )}
                      <span>Continue with {provider.name}</span>
                    </a>
                  ) : (
                    <span
                      className="fc-button fc-button-secondary"
                      aria-disabled="true"
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 10,
                        width: "100%",
                        opacity: 0.5,
                        cursor: "not-allowed",
                        padding: "12px 18px",
                      }}
                    >
                      {enabled ? "Accept terms to continue" : `${provider.name} not configured`}
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          <div className="fc-divider" style={{ margin: "20px 0 16px" }} />

          <div className="fc-data-list" style={{ textAlign: "center" }}>
            <div className="fc-muted" style={{ fontSize: "0.9rem" }}>
              {mode === "signin" ? "New to Fire Crow?" : "Already have a workspace?"}
            </div>
            <div style={{ marginTop: 8 }}>
              <Link className="fc-nav-link" href={altHref} style={{ textDecoration: "underline", fontWeight: "600", color: "var(--fire-soft)" }}>
                {altLabel}
              </Link>
            </div>
          </div>
        </Card>
      </main>
      <SiteFooter />
    </div>
  );
}

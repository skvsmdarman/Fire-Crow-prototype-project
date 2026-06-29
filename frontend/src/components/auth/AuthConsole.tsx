"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { persistSession } from "../../lib/auth-session";
import { buildApiUrl } from "../../lib/base-url";
import { request, ApiError } from "../../lib/request";
import { PolicyContext, AuthTokenResponse } from "../../lib/types";
import { Badge } from "../ui/Badge";
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
  const [error, setError] = useState<string | null>(null);
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

  const headline = mode === "signin" ? "Sign in with the provider your team already trusts." : "Create your Fire Crow account with one secure sign-in.";
  const description =
    mode === "signin"
      ? "Use GitHub or Google to access your workspace, review active audits, and share outcomes without exposing clients to extra login friction."
      : "Start with GitHub or Google and Fire Crow will guide your team into a cleaner, more client-friendly security review experience.";

  const ctaLabel = mode === "signin" ? "Sign In" : "Create Account";
  const altHref = mode === "signin" ? "/signup" : "/signin";
  const altLabel = mode === "signin" ? "Need a new account?" : "Already have access?";

  const providers = [
    {
      id: "github" as const,
      name: "GitHub",
      tone: "info" as const,
      copy: "Best for engineering-led teams that want repository context and a familiar developer sign-in flow.",
    },
    {
      id: "google" as const,
      name: "Google",
      tone: "success" as const,
      copy: "Best for organizations that want quick access through the accounts they already use across the business.",
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
          {validatingCode ? (
            <div className="fc-form-success" style={{ marginBottom: 16 }}>
              Verifying OAuth exchange and restoring the workspace session...
            </div>
          ) : null}

          <label className="fc-checkline" style={{ marginTop: 18 }}>
            <input checked={accepted} onChange={(event) => setAccepted(event.target.checked)} type="checkbox" />
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

          <div className="fc-card-grid" style={{ marginTop: 20 }}>
            {providers.map((provider) => {
              const enabled = Boolean(context?.providers[provider.id]);
              const href = enabled && accepted ? buildOAuthUrl(provider.id, activePrivacyVersion) : undefined;

              return (
                <Card className="fc-panel" key={provider.id}>
                  <div className="fc-stack-between" style={{ gap: 16 }}>
                    <div>
                      <div className="fc-kicker">{provider.name}</div>
                      <div className="fc-panel-title" style={{ marginTop: 8, fontSize: "1.24rem" }}>
                        Continue with {provider.name}
                      </div>
                    </div>
                    <Badge tone={enabled ? provider.tone : "neutral"}>{enabled ? "Available" : "Unavailable"}</Badge>
                  </div>
                  <div className="fc-copy" style={{ marginTop: 14 }}>
                    {provider.copy}
                  </div>
                  <div className="fc-chip-row" style={{ marginTop: 18 }}>
                    {href ? (
                      <a className="fc-button fc-button-primary" href={href}>
                        Continue with {provider.name}
                      </a>
                    ) : (
                      <span className="fc-button fc-button-secondary" aria-disabled="true" style={{ opacity: 0.65 }}>
                        {enabled ? "Accept terms to continue" : `${provider.name} not configured`}
                      </span>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>

          <div className="fc-divider" style={{ margin: "20px 0 16px" }} />

          <div className="fc-data-list">
            <div className="fc-muted">Need a different entry point?</div>
            <div className="fc-copy">This frontend now keeps the customer-facing sign-in flow focused on GitHub and Google only.</div>
            <div className="fc-chip-row" style={{ marginTop: 14 }}>
              <Link className="fc-nav-link" href={altHref}>
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

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { motion as framerMotion } from "framer-motion";
import { useAuthSession } from "../../shared/hooks/useAuthSession";
import { usePolicyContext } from "../../features/auth/hooks";
import { exchangeCode } from "../../features/auth/api";
import { detectRegionFromTimezone } from "../../lib/policyData";
import { buildApiUrl, isAbsoluteUrl } from "../../shared/api/baseUrl";
import { PRODUCT_NAME, PRODUCT_TAGLINE } from "../../shared/config/app";

const theme = {
  bg: "var(--bg)",
  surface: "var(--surface)",
  border: "var(--border)",
  borderHover: "var(--borderHover)",
  text: "var(--text)",
  muted: "var(--muted)",
  dim: "var(--dim)",
  orange: "var(--orange)",
  orangeDim: "var(--orangeDim)",
  orangeBorder: "var(--orangeBorder)",
  green: "var(--green)",
  red: "var(--red)",
  blue: "var(--blue)",
  amber: "var(--amber)",
};

function Logo({ centered }: { centered?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: centered ? "center" : "flex-start" }}>
      <div style={{ width: 30, height: 30, borderRadius: 8, background: `linear-gradient(135deg, ${theme.orange}, #ffb347)`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#160800", fontFamily: "'IBM Plex Mono', monospace" }}>FC</span>
      </div>
      <div style={{ textAlign: "left" }}>
        <div style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.01em" }}>{PRODUCT_NAME}</div>
        <div className="mono" style={{ fontSize: 9, color: theme.muted, letterSpacing: "0.12em", textTransform: "uppercase" }}>{PRODUCT_TAGLINE}</div>
      </div>
    </div>
  );
}

export default function SignInPage() {
  const router = useRouter();
  const authSession = useAuthSession();
  const login = authSession.login;
  const { activePrivacyVersion, providerAvailability } = usePolicyContext();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const handledExchangeCodeRef = useRef<string | null>(null);

  useEffect(() => {
    if (authSession.hasDashboardSession && authSession.workspace) {
      router.push(`/dashboard?workspace=${encodeURIComponent(authSession.workspace)}`);
    }
  }, [authSession.hasDashboardSession, authSession.workspace, router]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const code = new URLSearchParams(window.location.search).get("code") ?? "";
    if (!code || handledExchangeCodeRef.current === code) {
      return;
    }

    let active = true;
    handledExchangeCodeRef.current = code;
    setLoading(true);
    setError("");

    async function finishOauthSignIn() {
      try {
        const session = await exchangeCode(code);
        if (!active) {
          return;
        }
        // Only persist non-sensitive metadata. The access token is in an HttpOnly cookie
        // set by the backend during the exchange.
        login({
          user_id: session.user_id,
          username: session.username,
        });
        router.replace(`/dashboard?workspace=${encodeURIComponent(session.username)}`);
      } catch (authError) {
        const err = authError as { message?: string };
        if (!active) {
          return;
        }
        setError(err.message || "Unable to finish sign-in.");
        if (typeof window !== "undefined") {
          const nextUrl = new URL(window.location.href);
          nextUrl.searchParams.delete("code");
          window.history.replaceState({}, "", nextUrl.toString());
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void finishOauthSignIn();

    return () => {
      active = false;
    };
  }, [login, router]);

  const oauthHref = (provider: "github" | "google") => {
    const authUrl = buildApiUrl(`/auth/${provider}`);
    const url = isAbsoluteUrl(authUrl)
      ? new URL(authUrl)
      : new URL(authUrl, typeof window !== "undefined" ? window.location.origin : "https://firecrow.invalid");
    url.searchParams.set("privacy_policy_accepted", "true");
    url.searchParams.set("privacy_policy_version", activePrivacyVersion);
    if (typeof window !== "undefined") {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      url.searchParams.set("timezone", tz);
      url.searchParams.set("region", detectRegionFromTimezone(tz));
    }
    return isAbsoluteUrl(authUrl) ? url.toString() : `${url.pathname}${url.search}`;
  };

  const providerCount = Number(providerAvailability.github) + Number(providerAvailability.google);

  if (authSession.hasDashboardSession) {
    return null; // Will redirect
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 24, background: theme.bg, color: theme.text }}>
      <framerMotion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} style={{ width: "100%", maxWidth: 360 }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <Logo centered />
          <p style={{ color: theme.muted, fontSize: 13, marginTop: 10 }}>Sign in to access your workspace</p>
        </div>

        <div style={{ border: `1px solid ${theme.border}`, borderRadius: 10, overflow: "hidden", background: theme.surface }}>
          <div style={{ height: 2, background: `linear-gradient(90deg, ${theme.orange}, #ffb347)` }} />
          <div style={{ padding: 24 }}>
            <p style={{ fontSize: 12, color: theme.muted, marginBottom: 14, textAlign: "center" }}>Continue with</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {providerAvailability.github && (
                <a href={oauthHref("github")} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, padding: "12px 16px", border: `1px solid ${theme.border}`, borderRadius: 7, background: "transparent", color: theme.text, fontSize: 13, fontWeight: 500, transition: "border-color .2s, background .2s", textDecoration: "none" }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = theme.borderHover; e.currentTarget.style.background = "#1a1a1a"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = theme.border; e.currentTarget.style.background = "transparent"; }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill={theme.muted}><path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.49.5.09.68-.22.68-.48 0-.24-.01-.87-.01-1.7-2.78.6-3.37-1.34-3.37-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.56 9.56 0 0 1 12 6.84c.85.004 1.7.115 2.5.337 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85 0 1.34-.01 2.41-.01 2.74 0 .27.18.58.69.48A10.02 10.02 0 0 0 22 12c0-5.52-4.48-10-10-10z" /></svg>
                  Continue with GitHub
                </a>
              )}
              {providerAvailability.google && (
                <a href={oauthHref("google")} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, padding: "12px 16px", border: `1px solid ${theme.border}`, borderRadius: 7, background: "transparent", color: theme.text, fontSize: 13, fontWeight: 500, transition: "border-color .2s, background .2s", textDecoration: "none" }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = theme.borderHover; e.currentTarget.style.background = "#1a1a1a"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = theme.border; e.currentTarget.style.background = "transparent"; }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill={theme.muted}><path d="M21.35 11.1h-9.17v2.73h6.51c-.33 3.81-3.5 5.44-6.5 5.44C8.36 19.27 5 16.25 5 12c0-4.1 3.2-7.27 7.2-7.27 3.09 0 4.9 1.97 4.9 1.97L19 4.72S16.56 2 12.1 2C6.42 2 2.03 6.8 2.03 12c0 5.05 4.13 10 10.22 10 5.35 0 9.25-3.67 9.25-9.09 0-1.15-.15-1.81-.15-1.81z" /></svg>
                  Continue with Google
                </a>
              )}
            </div>

            {providerCount === 0 && (
              <div style={{ color: theme.red, fontSize: 12, marginTop: 12, textAlign: "center" }}>
                OAuth sign-in is not configured yet.
              </div>
            )}

            {error && (
              <div style={{ color: theme.red, fontSize: 12, marginTop: 12, textAlign: "center" }}>
                {error}
              </div>
            )}

            {loading && (
              <div style={{ color: theme.blue, fontSize: 12, marginTop: 12, textAlign: "center" }}>
                Finishing sign-in...
              </div>
            )}
          </div>
        </div>

        <p style={{ textAlign: "center", fontSize: 11, color: theme.muted, marginTop: 16, lineHeight: 1.6 }}>
          By signing in you agree to our Terms of Use and Privacy Policy
        </p>
      </framerMotion.div>
    </div>
  );
}

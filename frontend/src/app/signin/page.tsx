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
import styles from "./page.module.css";

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
    <div className={styles.page}>
      <div className={styles.backdrop} />
      <div className={styles.gridGlow} />
      <div className={styles.centerContainer}>
        <framerMotion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ width: "100%" }}
        >
          {/* Logo */}
          <div className={styles.logoContainer}>
            <div className={styles.brand}>
              <span className={styles.brandMark}>FC</span>
              <span className={styles.brandText}>
                <strong>{PRODUCT_NAME}</strong>
                <small>{PRODUCT_TAGLINE}</small>
              </span>
            </div>
          </div>

          {/* Card */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <p className={styles.eyebrow}>Welcome</p>
              <h2>Sign in to your workspace</h2>
            </div>

            <div className={styles.providerStack}>
              {providerAvailability.github && (
                <a href={oauthHref("github")} className={styles.providerButton}>
                  <span className={styles.providerIcon}>
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.49.5.09.68-.22.68-.48 0-.24-.01-.87-.01-1.7-2.78.6-3.37-1.34-3.37-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.56 9.56 0 0 1 12 6.84c.85.004 1.7.115 2.5.337 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85 0 1.34-.01 2.41-.01 2.74 0 .27.18.58.69.48A10.02 10.02 0 0 0 22 12c0-5.52-4.48-10-10-10z"/></svg>
                  </span>
                  <span className={styles.providerCopy}>
                    <strong>Continue with GitHub</strong>
                  </span>
                </a>
              )}
              {providerAvailability.google && (
                <a href={oauthHref("google")} className={`${styles.providerButton} ${styles.googleIcon}`}>
                  <span className={styles.providerIcon}>
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.35 11.1h-9.17v2.73h6.51c-.33 3.81-3.5 5.44-6.5 5.44C8.36 19.27 5 16.25 5 12c0-4.1 3.2-7.27 7.2-7.27 3.09 0 4.9 1.97 4.9 1.97L19 4.72S16.56 2 12.1 2C6.42 2 2.03 6.8 2.03 12c0 5.05 4.13 10 10.22 10 5.35 0 9.25-3.67 9.25-9.09 0-1.15-.15-1.81-.15-1.81z"/></svg>
                  </span>
                  <span className={styles.providerCopy}>
                    <strong>Continue with Google</strong>
                  </span>
                </a>
              )}
            </div>

            {providerCount === 0 && (
              <div className={styles.errorNotice}>
                OAuth sign-in is not configured yet.
              </div>
            )}

            {error && (
              <div className={styles.errorNotice}>
                {error}
              </div>
            )}

            {loading && (
              <div className={styles.submitButton} style={{ cursor: "default", pointerEvents: "none" }}>
                <span className={styles.submitSpinner} />
                Finishing sign-in...
              </div>
            )}

            <p className={styles.cardFootnote}>
              By signing in you agree to our <a href="/terms">Terms of Use</a> and <a href="/privacy">Privacy Policy</a>
            </p>
          </div>
        </framerMotion.div>
      </div>
    </div>
  );
}

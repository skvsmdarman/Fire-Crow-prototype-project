"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { motion as framerMotion } from "framer-motion";
import PolicyLink from "../../features/legal/components/PolicyLink";
import { useAuthSession } from "../../shared/hooks/useAuthSession";
import { usePolicyContext } from "../../features/auth/hooks";
import { exchangeCode } from "../../features/auth/api";
import { detectRegionFromTimezone } from "../../lib/policyData";
import { API_BASE_URL } from "../../shared/api/client";
import styles from "./page.module.css";
import { fadeInLeft, fadeInRight } from "../../lib/animations";

const cx = (...args: (string | undefined | false)[]) => args.filter(Boolean).join(" ");

export default function SignInPage() {
  const router = useRouter();
  const authSession = useAuthSession();
  const { activePrivacyVersion, providerAvailability } = usePolicyContext();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const handledExchangeCodeRef = useRef<string | null>(null);

  useEffect(() => {
    if (authSession.token && authSession.workspace) {
      router.push(`/dashboard?workspace=${encodeURIComponent(authSession.workspace)}`);
    }
  }, [authSession.token, authSession.workspace, router]);

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
        authSession.login({
          access_token: session.access_token,
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
  }, [router, authSession]);

  const oauthHref = (provider: "github" | "google") => {
    const base = typeof window !== "undefined" ? window.location.origin : "http://localhost";
    const url = new URL(`${API_BASE_URL}/auth/${provider}`, base);
    url.searchParams.set("privacy_policy_accepted", "true");
    url.searchParams.set("privacy_policy_version", activePrivacyVersion);
    if (typeof window !== "undefined") {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      url.searchParams.set("timezone", tz);
      url.searchParams.set("region", detectRegionFromTimezone(tz));
    }
    return url.toString().replace(base, "");
  };

  const providerCount = Number(providerAvailability.github) + Number(providerAvailability.google);

  if (authSession.token) {
    return (
      <main className={styles.loadingPage}>
        <div className={styles.loadingBackdrop} aria-hidden="true" />
        <section className={styles.loadingCard}>
          <div className="auth-loading-spinner" />
          <p className={styles.eyebrow}>Session</p>
          <h1 className={styles.loadingTitle}>Validating access</h1>
          <p className={styles.loadingCopy}>Checking your existing FireCrow token and preparing the console.</p>
        </section>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <div className="auth-glow-orb auth-glow-orb-1" aria-hidden="true" style={{ background: "radial-gradient(circle, rgba(92, 144, 255, 0.22) 0%, transparent 70%)" }} />
      <div className="auth-glow-orb auth-glow-orb-2" aria-hidden="true" style={{ background: "radial-gradient(circle, rgba(179, 92, 255, 0.16) 0%, transparent 70%)" }} />
      <div className="auth-grid-overlay" aria-hidden="true" />

      <div className={styles.backdrop} aria-hidden="true" />
      <div className={styles.gridGlow} aria-hidden="true" />

      <div className={styles.centerContainer}>
        <framerMotion.div
          variants={fadeInLeft}
          initial="hidden"
          animate="visible"
          className={styles.logoContainer}
        >
          <Link href="/" className={cx(styles.brand, "auth-brand")}>
            <span className={styles.brandMark}>FC</span>
            <span className={styles.brandText}>
              <strong>FireCrow</strong>
              <small>Autonomous security audit</small>
            </span>
          </Link>
        </framerMotion.div>

        <framerMotion.section
          variants={fadeInRight}
          initial="hidden"
          animate="visible"
          className={cx(styles.card, "auth-card")}
        >
          <div className="auth-card-accent" />

          <div className={styles.cardHeader}>
            <p className={styles.eyebrow}>Secure access</p>
            <h2>Sign in with your provider</h2>
            <p>
              FireCrow now uses OAuth-only access. Continue with GitHub or Google to open your dashboard.
            </p>
          </div>

          <div className={styles.providerStack}>
            {providerAvailability.github ? (
              <framerMotion.a
                whileHover={{ scale: 1.01, borderColor: "rgba(255,255,255,0.18)" }}
                whileTap={{ scale: 0.99 }}
                href={oauthHref("github")}
                className={styles.providerButton}
              >
                <span className={styles.providerIcon} aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.579.688.481C19.138 20.164 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                  </svg>
                </span>
                <span className={styles.providerCopy}>
                  <strong>Continue with GitHub</strong>
                </span>
              </framerMotion.a>
            ) : null}

            {providerAvailability.google ? (
              <framerMotion.a
                whileHover={{ scale: 1.01, borderColor: "rgba(255,255,255,0.18)" }}
                whileTap={{ scale: 0.99 }}
                href={oauthHref("google")}
                className={styles.providerButton}
              >
                <span className={cx(styles.providerIcon, styles.googleIcon)} aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path fillRule="evenodd" clipRule="evenodd" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                    <path fillRule="evenodd" clipRule="evenodd" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
                  </svg>
                </span>
                <span className={styles.providerCopy}>
                  <strong>Continue with Google</strong>
                </span>
              </framerMotion.a>
            ) : null}
          </div>

          {providerCount === 0 ? (
            <div className={styles.errorNotice} role="alert">
              OAuth sign-in is not configured yet. Add GitHub and/or Google OAuth credentials in the backend environment before using this page.
            </div>
          ) : null}

          {error && (
            <div className={styles.errorNotice} role="alert">
              {error}
            </div>
          )}

          {loading ? (
            <div className={styles.divider}>Finishing sign-in...</div>
          ) : null}

          <footer className={styles.cardFootnote}>
            <p>
              By signing in, you agree to our{" "}
              <PolicyLink href="/terms" policy="terms" source="signin_footnote">
                Terms of Use
              </PolicyLink>
              {" "}and{" "}
              <PolicyLink href="/privacy-policy" policy="privacy_policy" source="signin_footnote">
                Privacy Policy
              </PolicyLink>
              .
            </p>
            <p style={{ marginTop: "12px" }}>
              Need access?{" "}
              <Link href="/signup" style={{ color: "#5cc8ff", fontWeight: "bold" }}>
                Continue with OAuth
              </Link>
            </p>
          </footer>
        </framerMotion.section>
      </div>
    </main>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { motion } from "framer-motion";
import PolicyLink from "../../components/PolicyLink";
import {
  getServerAuthSessionSnapshot,
  getStoredAuthSessionSnapshot,
  subscribeToAuthSession
} from "../../lib/authSession";
import { API_BASE_URL, PRIVACY_POLICY_VERSION } from "../../lib/policy";
import { detectRegionFromTimezone } from "../../lib/policyData";
import styles from "./page.module.css";
import {
  fadeInLeft,
  fadeInRight
} from "../../lib/animations";

const SIGNUP_PROMISES = [
  {
    title: "GitHub-linked access",
    body: "Use GitHub OAuth when you need repository-linked access and provider scopes for private code review flows.",
  },
  {
    title: "Google-backed access",
    body: "Use Google OAuth for teams that want simple sign-in without managing separate FireCrow passwords.",
  },
  {
    title: "No workspace passwords",
    body: "Workspace username and password registration has been removed from the product surface to avoid broken local-only login paths.",
  },
];

const SIGNUP_METRICS = [
  { value: "OAuth", label: "Only access path" },
  { value: "2", label: "Providers" },
  { value: "Live", label: "Session exchange" },
];

const cx = (...args: (string | undefined | false)[]) => args.filter(Boolean).join(" ");

interface PolicyContext {
  privacy_policy_version: string;
  providers: {
    github: boolean;
    google: boolean;
    password: boolean;
  };
  terms_version: string;
}

export default function SignUpPage() {
  const router = useRouter();

  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  const [error, setError] = useState("");
  const [activePrivacyVersion, setActivePrivacyVersion] = useState(PRIVACY_POLICY_VERSION);
  const [providerAvailability, setProviderAvailability] = useState({
    github: false,
    google: false,
    password: false,
  });

  useEffect(() => {
    let active = true;

    async function loadPolicyContext() {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/policy-context`);
        if (!response.ok) throw new Error("Could not load policy configuration.");
        const data = (await response.json()) as PolicyContext;

        if (active) {
          setActivePrivacyVersion(data.privacy_policy_version || PRIVACY_POLICY_VERSION);
          setProviderAvailability(data.providers);
        }
      } catch (err) {
        console.warn("Using default policy fallback versions:", err);
      }
    }

    loadPolicyContext();
    return () => {
      active = false;
    };
  }, []);

  const browserSession = useSyncExternalStore(
    subscribeToAuthSession,
    getStoredAuthSessionSnapshot,
    getServerAuthSessionSnapshot
  );

  useEffect(() => {
    if (browserSession.hasConsoleSession && browserSession.workspace) {
      router.push(`/dashboard?workspace=${encodeURIComponent(browserSession.workspace)}`);
    }
  }, [browserSession.hasConsoleSession, browserSession.workspace, router]);

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

  const handleProviderClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (!acceptedPrivacy) {
      e.preventDefault();
      setError("You must read and accept the Privacy Policy and Terms of Use first.");
      return;
    }
    setError("");
  };

  const providerCount = Number(providerAvailability.github) + Number(providerAvailability.google);

  if (browserSession.hasConsoleSession) {
    return (
      <main className={styles.loadingPage}>
        <div className={styles.loadingBackdrop} aria-hidden="true" />
        <section className={styles.loadingCard}>
          <div className="auth-loading-spinner" />
          <p className={styles.eyebrow}>Session</p>
          <h1 className={styles.loadingTitle}>Preparing Access</h1>
          <p className={styles.loadingCopy}>Validating active session and loading your FireCrow dashboard...</p>
        </section>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <div className="auth-glow-orb auth-glow-orb-1" aria-hidden="true" style={{ background: "radial-gradient(circle, rgba(255, 77, 8, 0.28) 0%, transparent 70%)" }} />
      <div className="auth-glow-orb auth-glow-orb-2" aria-hidden="true" style={{ background: "radial-gradient(circle, rgba(255, 184, 0, 0.2) 0%, transparent 70%)" }} />
      <div className="auth-grid-overlay" aria-hidden="true" />

      <div className={styles.backdrop} aria-hidden="true" />
      <div className={styles.gridGlow} aria-hidden="true" />

      <div className={styles.shell}>
        <motion.aside
          variants={fadeInLeft}
          initial="hidden"
          animate="visible"
          className={cx(styles.sidebar, "auth-shell")}
        >
          <Link href="/" className={cx(styles.brand, "auth-brand")}>
            <span className={styles.brandMark}>FC</span>
            <span className={styles.brandText}>
              <strong>FireCrow</strong>
              <small>Autonomous security audit</small>
            </span>
          </Link>

          <div className={styles.sidebarIntro}>
            <p className={styles.eyebrow}>Provider access</p>
            <h1 className={styles.sidebarTitle}>Use GitHub or Google to enter FireCrow.</h1>
            <p className={styles.sidebarCopy}>
              Password-based workspace registration has been removed. Choose an OAuth provider and continue into the dashboard with a provider-backed session.
            </p>
          </div>

          <section className={styles.sidebarPanel}>
            <p className={styles.panelLabel}>Access model</p>
            <div className={styles.promiseList}>
              {SIGNUP_PROMISES.map((promise, index) => (
                <motion.article
                  whileHover={{ x: 3 }}
                  className={styles.promiseItem}
                  key={promise.title}
                >
                  <span className={styles.promiseIndex}>{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <h2>{promise.title}</h2>
                    <p>{promise.body}</p>
                  </div>
                </motion.article>
              ))}
            </div>
          </section>

          <section className={styles.readinessRow} aria-label="Platform readiness">
            {SIGNUP_METRICS.map((metric) => (
              <article key={metric.label} className={styles.metricCard}>
                <strong>{metric.value}</strong>
                <span>{metric.label}</span>
              </article>
            ))}
          </section>

          <p className={cx(styles.sidebarFootnote, "auth-footnote")}>
            Privacy notice and terms consent is logged for compliance and security auditing.
          </p>
        </motion.aside>

        <motion.section
          variants={fadeInRight}
          initial="hidden"
          animate="visible"
          className={cx(styles.card, "auth-card")}
        >
          <div className="auth-card-accent" style={{ background: "linear-gradient(90deg, #ff4d08, #ffbf47)" }} />

          <div className={styles.cardHeader}>
            <p className={styles.eyebrow}>Continue</p>
            <h2>Choose your sign-in provider</h2>
            <p>
              Accept the policy terms and continue with GitHub or Google. FireCrow will create or resume your account from that provider flow.
            </p>
          </div>

          <label className={styles.termsCard}>
            <input
              checked={acceptedPrivacy}
              onChange={(event) => {
                setAcceptedPrivacy(event.target.checked);
                setError("");
              }}
              type="checkbox"
            />
            <span>
              I have read and agree to the{" "}
              <PolicyLink href="/privacy-policy" policy="privacy_policy" source="signup_checkbox">
                Privacy Policy
              </PolicyLink>
              {" "}and{" "}
              <PolicyLink href="/terms" policy="terms" source="signup_checkbox">
                Terms of Use
              </PolicyLink>
              . I consent to processing and activity logging.
            </span>
          </label>
          <p className={styles.termsHint}>
            Accepted policy interaction details are logged. Privacy Policy: {activePrivacyVersion}.
          </p>

          <div className={styles.providerStack}>
            {providerAvailability.github ? (
              <motion.a
                whileHover={{ scale: 1.01, borderColor: "rgba(255,255,255,0.18)" }}
                whileTap={{ scale: 0.99 }}
                href={oauthHref("github")}
                className={styles.providerButton}
                onClick={handleProviderClick}
              >
                <span className={styles.providerIcon} aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.579.688.481C19.138 20.164 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                  </svg>
                </span>
                <span className={styles.providerCopy}>
                  <strong>Continue with GitHub</strong>
                  <span>Use your GitHub identity to enter FireCrow.</span>
                </span>
              </motion.a>
            ) : null}

            {providerAvailability.google ? (
              <motion.a
                whileHover={{ scale: 1.01, borderColor: "rgba(255,255,255,0.18)" }}
                whileTap={{ scale: 0.99 }}
                href={oauthHref("google")}
                className={styles.providerButton}
                onClick={handleProviderClick}
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
                  <span>Use your Google identity to enter FireCrow.</span>
                </span>
              </motion.a>
            ) : null}
          </div>

          {providerCount === 0 ? (
            <div className={styles.errorNotice} role="alert">
              No OAuth providers are configured yet. Add GitHub and/or Google OAuth credentials in the backend environment before using this page.
            </div>
          ) : null}

          {error && (
            <div className={styles.errorNotice} role="alert">
              {error}
            </div>
          )}

          <p className={styles.cardFootnote}>
            Already have access?{" "}
            <Link href="/signin" style={{ color: "#ff9c4a", fontWeight: "bold" }}>
              Sign in with OAuth
            </Link>
          </p>
        </motion.section>
      </div>
    </main>
  );
}

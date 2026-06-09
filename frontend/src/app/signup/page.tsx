"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { motion } from "framer-motion";
import PolicyLink from "../../components/PolicyLink";
import {
  getServerAuthSessionSnapshot,
  getStoredAuthSessionSnapshot,
  persistAuthSession,
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
    title: "Continuous SAST & Agent Audits",
    body: "Deploy 6 offensive agents working concurrently to discover secrets, source leaks, and dependency flaws in real time.",
  },
  {
    title: "Secure Workspace Sandboxing",
    body: "Your source code is cloned into an isolated Kali Linux runtime environment with local auto-destruction after verification.",
  },
  {
    title: "Zero-Setup Report Generation",
    body: "Receive direct, comprehensive PDF audit reports sent straight to your mailbox with no external account sign-ups required.",
  },
];

const SIGNUP_METRICS = [
  { value: "6", label: "Security agents" },
  { value: "Sandbox", label: "Isolation" },
  { value: "Neon", label: "Active logging" },
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

interface AuthSession {
  access_token: string;
  user_id: string;
  username: string;
}

export default function SignUpPage() {
  const router = useRouter();

  // Form State
  const [workspace, setWorkspace] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);

  // Status State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Policy Context
  const [activePrivacyVersion, setActivePrivacyVersion] = useState(PRIVACY_POLICY_VERSION);
  const [loadingContext, setLoadingContext] = useState(true);
  const [providerAvailability, setProviderAvailability] = useState({
    github: false,
    google: false,
    password: true,
  });

  // Fetch Policy and Provider Context
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
      } finally {
        if (active) setLoadingContext(false);
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

  const getDashboardRedirectUrl = () => {
    const targetWorkspace = workspace.trim() || "workspace";
    return `/dashboard?workspace=${encodeURIComponent(targetWorkspace)}`;
  };

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

  const submitRegister = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedWorkspace = workspace.trim();

    if (!normalizedWorkspace) {
      setError("Enter a workspace name.");
      return;
    }

    if (email.trim() && !email.includes("@")) {
      setError("Enter a valid work email address.");
      return;
    }

    if (!password) {
      setError("Create a password for the workspace.");
      return;
    }

    if (password.length < 8) {
      setError("Use a password with at least 8 characters.");
      return;
    }

    if (!acceptedPrivacy) {
      setError("Read and accept the Privacy Policy and Terms of Use before continuing.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const tz = typeof window !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "";
      const reg = detectRegionFromTimezone(tz);

      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim() || null,
          password,
          privacy_policy_accepted: acceptedPrivacy,
          privacy_policy_version: activePrivacyVersion,
          username: normalizedWorkspace,
          timezone: tz,
          region: reg,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Unable to create workspace.");
      }

      const session = (await response.json()) as AuthSession;
      persistAuthSession(session);
      router.push(getDashboardRedirectUrl());
    } catch (authError) {
      const errMsg = authError instanceof Error ? authError.message : "";
      if (errMsg.toLowerCase().includes("failed to fetch") || errMsg.toLowerCase().includes("fetch")) {
        setError("Could not connect to workspace services. Please try again later.");
      } else {
        setError(errMsg || "Unable to create workspace.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (browserSession.hasConsoleSession) {
    return (
      <main className={styles.loadingPage}>
        <div className={styles.loadingBackdrop} aria-hidden="true" />
        <section className={styles.loadingCard}>
          <div className="auth-loading-spinner" />
          <p className={styles.eyebrow}>Session</p>
          <h1 className={styles.loadingTitle}>Preparing Workspace</h1>
          <p className={styles.loadingCopy}>Validating active session and provisioning security console environment...</p>
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
            <p className={styles.eyebrow}>Create workspace</p>
            <h1 className={styles.sidebarTitle}>Start your first security review today.</h1>
            <p className={styles.sidebarCopy}>
              Configure your dedicated workspace credentials, invite collaborators, and orchestrate offensive scans on private or public repositories.
            </p>
          </div>

          <section className={styles.sidebarPanel}>
            <p className={styles.panelLabel}>Platform features</p>
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
            <p className={styles.eyebrow}>Registration</p>
            <h2>Create your workspace</h2>
            <p>
              Fill out the details below to create a secure, isolated console for security audits.
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
                  <strong>Register with GitHub</strong>
                  <span>Fast track workspace creation via OAuth profile link.</span>
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
                  <strong>Register with Google</strong>
                  <span>Create space via Google OAuth workflow.</span>
                </span>
              </motion.a>
            ) : null}
          </div>

          {providerAvailability.password ? (
            <>
              <div className={styles.divider}>or register with credentials</div>

              <form className={styles.form} onSubmit={submitRegister}>
                <label className={styles.field}>
                  <span>Workspace name</span>
                  <div className={styles.inputWrap}>
                    <span className={styles.inputIcon} aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                        <path d="M16 3h-8l-2 4h12l-2-4z" />
                      </svg>
                    </span>
                    <input
                      value={workspace}
                      onChange={(event) => {
                        setWorkspace(event.target.value);
                        setError("");
                      }}
                      placeholder="your-security-team"
                    />
                  </div>
                  <p className={styles.fieldHint}>
                    Unique handle for your workspace console. Only alphanumeric characters allowed.
                  </p>
                </label>

                <label className={styles.field}>
                  <span>Work email</span>
                  <div className={styles.inputWrap}>
                    <span className={styles.inputIcon} aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="4" width="20" height="16" rx="2" />
                        <path d="m22 7-10 6L2 7" />
                      </svg>
                    </span>
                    <input
                      value={email}
                      onChange={(event) => {
                        setEmail(event.target.value);
                        setError("");
                      }}
                      placeholder="security@company.in"
                      type="email"
                    />
                  </div>
                </label>

                <label className={styles.field}>
                  <span>Password</span>
                  <div className={styles.inputWrap}>
                    <span className={styles.inputIcon} aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </span>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(event) => {
                        setPassword(event.target.value);
                        setError("");
                      }}
                      placeholder="Create a strong password"
                    />
                    <button
                      type="button"
                      className={styles.togglePassword}
                      onClick={() => setShowPassword((current) => !current)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? (
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                          <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                          <line x1="1" y1="1" x2="23" y2="23" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      )}
                    </button>
                  </div>
                </label>

                {error && (
                  <div className={styles.errorNotice} role="alert">
                    {error}
                  </div>
                )}

                <motion.button
                  whileHover={{ scale: loading ? 1 : 1.01 }}
                  whileTap={{ scale: loading ? 1 : 0.99 }}
                  className={styles.submitButton}
                  disabled={loading || loadingContext}
                  type="submit"
                >
                  {loading && <span className={styles.submitSpinner} />}
                  {loading ? "Registering Workspace..." : "Create workspace"}
                </motion.button>
              </form>
            </>
          ) : null}

          {error && !providerAvailability.password && (
            <div className={styles.errorNotice} role="alert" style={{ marginTop: "16px" }}>
              {error}
            </div>
          )}

          <p className={styles.cardFootnote}>
            Already have a workspace?{" "}
            <Link href="/signin" style={{ color: "#ff9c4a", fontWeight: "bold" }}>
              Sign in
            </Link>
          </p>
        </motion.section>
      </div>
    </main>
  );
}

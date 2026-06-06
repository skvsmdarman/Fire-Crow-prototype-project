"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Cpu, Key, HelpCircle, Lock, Mail, Eye, EyeOff, CheckCircle } from "lucide-react";

import FireCrowLoader from "../../components/FireCrowLoader";
import PolicyLink from "../../components/PolicyLink";
import { API_BASE_URL, PRIVACY_POLICY_VERSION } from "../../lib/policy";
import styles from "./page.module.css";
import {
  fadeInLeft,
  fadeInRight,
  tabTransition
} from "../../lib/animations";

const CONSOLE_PROMISES = [
  {
    title: "Re-open old audits fast",
    body: "Jump back into repository runs, severity shifts, and report exports without rebuilding the story from scratch.",
  },
  {
    title: "Sign in the way your team already works",
    body: "Use GitHub, Google, or workspace credentials depending on how your team actually gets into code review.",
  },
  {
    title: "Keep the proof next to the finding",
    body: "Confirmed findings, runtime notes, and remediation materials stay attached instead of drifting into chat threads.",
  },
];

const READINESS_METRICS = [
  { value: "9", label: "Agents online" },
  { value: "Kali", label: "Sandbox profile" },
  { value: "CVSS", label: "Scoring model" },
];

const ACCESS_HINTS = [
  "Prefer GitHub if you already review code there every day.",
  "Workspace name is usually the slug your team shares in links or screenshots.",
  "Nothing is submitted until you choose a sign-in method or hit the button.",
];

type AuthMode = "login" | "register";

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

const cx = (...tokens: Array<string | false | null | undefined>) => tokens.filter(Boolean).join(" ");

export default function SignInPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("login");
  const [workspace, setWorkspace] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [loadingContext, setLoadingContext] = useState(true);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [policyContext, setPolicyContext] = useState<PolicyContext | null>(null);

  const activePrivacyVersion = policyContext?.privacy_policy_version ?? PRIVACY_POLICY_VERSION;

  const clearSession = () => {
    localStorage.removeItem("fc_token");
    localStorage.removeItem("fc_username");
    localStorage.removeItem("fc_user_id");
  };

  const persistSession = (session: AuthSession) => {
    localStorage.setItem("fc_token", session.access_token);
    localStorage.setItem("fc_username", session.username);
    localStorage.setItem("fc_user_id", session.user_id);
  };

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const loadPolicyContext = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/policy-context`);
        if (!response.ok) {
          throw new Error("Unable to load authentication context.");
        }
        setPolicyContext((await response.json()) as PolicyContext);
      } catch (contextError) {
        setError(
          contextError instanceof Error
            ? contextError.message
            : "Unable to load authentication context.",
        );
      } finally {
        setLoadingContext(false);
      }
    };

    void loadPolicyContext();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get("token");
    const urlUsername = urlParams.get("username");
    const urlUserId = urlParams.get("user_id");

    if (urlToken && urlUsername && urlUserId) {
      persistSession({
        access_token: urlToken,
        user_id: urlUserId,
        username: urlUsername,
      });
      router.replace("/dashboard");
      return;
    }

    const token = localStorage.getItem("fc_token");
    if (!token) {
      queueMicrotask(() => setCheckingSession(false));
      return;
    }

    fetch(`${API_BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((response) => {
        if (!response.ok) {
          clearSession();
          setCheckingSession(false);
          return;
        }
        router.replace("/dashboard");
      })
      .catch(() => setCheckingSession(false));
  }, [router]);

  const providerAvailability = useMemo(
    () => ({
      github: Boolean(policyContext?.providers.github),
      google: Boolean(policyContext?.providers.google),
    }),
    [policyContext],
  );

  const oauthHref = (provider: "github" | "google") =>
    `${API_BASE_URL}/auth/${provider}?privacy_policy_accepted=true&privacy_policy_version=${encodeURIComponent(activePrivacyVersion)}`;

  const handleProviderClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    if (!acceptedPrivacy) {
      event.preventDefault();
      setError("Read and accept the Privacy Policy before continuing.");
      return;
    }

    setError("");
  };

  const submitAuth = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedWorkspace = workspace.trim();

    if (!normalizedWorkspace) {
      setError("Enter your workspace name.");
      return;
    }

    if (mode === "register" && email.trim() && !email.includes("@")) {
      setError("Enter a valid work email address or leave it blank.");
      return;
    }

    if (!password) {
      setError(mode === "register" ? "Create a password for the workspace." : "Enter your workspace password.");
      return;
    }

    if (password.length < 8) {
      setError("Use a password with at least 8 characters.");
      return;
    }

    if (!acceptedPrivacy) {
      setError("Read and accept the Privacy Policy before continuing.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const endpoint = mode === "register" ? "/auth/register" : "/auth/login";
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: mode === "register" ? email.trim() || null : undefined,
          password,
          privacy_policy_accepted: acceptedPrivacy,
          privacy_policy_version: activePrivacyVersion,
          username: normalizedWorkspace,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Unable to complete authentication.");
      }

      const session = (await response.json()) as AuthSession;
      persistSession(session);
      router.push("/dashboard");
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Unable to complete authentication.");
    } finally {
      setLoading(false);
    }
  };

  if (checkingSession) {
    return (
      <main className={styles.loadingPage}>
        <div className={styles.loadingBackdrop} aria-hidden="true" />
        <section className={styles.loadingCard}>
          <div className="auth-loading-spinner" />
          <p className={styles.eyebrow}>Session</p>
          <h1 className={styles.loadingTitle}>Validating workspace access</h1>
          <p className={styles.loadingCopy}>Checking your existing FireCrow token and preparing the console.</p>
        </section>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      {/* Decorative Orbs & Grid */}
      <div className="auth-glow-orb auth-glow-orb-1" aria-hidden="true" />
      <div className="auth-glow-orb auth-glow-orb-2" aria-hidden="true" />
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
            <p className={styles.eyebrow}>Secure workspace access</p>
            <h1 className={styles.sidebarTitle}>Pick up where the last review left off.</h1>
            <p className={styles.sidebarCopy}>
              Open the same workspace your team is already using, rerun a repo, and keep the conversation attached to the evidence instead of starting from zero.
            </p>
          </div>

          <section className={styles.sidebarPanel}>
            <p className={styles.panelLabel}>What people actually use</p>
            <div className={styles.promiseList}>
              {CONSOLE_PROMISES.map((promise, index) => (
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

          <section className={styles.readinessRow} aria-label="Workspace readiness">
            {READINESS_METRICS.map((metric) => (
              <article key={metric.label} className={styles.metricCard}>
                <strong>{metric.value}</strong>
                <span>{metric.label}</span>
              </article>
            ))}
          </section>

          <p className={cx(styles.sidebarFootnote, "auth-footnote")}>
            Privacy notice acknowledgement is stored with timestamp, IP, and user agent to support compliance evidence and security auditing.
          </p>
        </motion.aside>

        <motion.section
          variants={fadeInRight}
          initial="hidden"
          animate="visible"
          className={cx(styles.card, "auth-card")}
        >
          <div className="auth-card-accent" />

          <div className={styles.cardHeader}>
            <p className={styles.eyebrow}>Workspace access</p>
            <h2>{mode === "register" ? "Create your workspace" : "Open your workspace"}</h2>
            <p>
              {mode === "register"
                ? "Create a real workspace credential set here. No mock or auto-provisioned login path is left in the app."
                : "GitHub is usually the fastest path if you already review code there. Credentials are handy for shared workspaces and direct access."}
            </p>
          </div>

          <div className={styles.modeToggle} role="tablist" aria-label="Authentication mode">
            <button
              type="button"
              className={cx(styles.modeButton, mode === "login" && styles.modeButtonActive)}
              role="tab"
              aria-selected={mode === "login"}
              onClick={() => {
                setMode("login");
                setError("");
              }}
            >
              Sign in
            </button>
            <button
              type="button"
              className={cx(styles.modeButton, mode === "register" && styles.modeButtonActive)}
              role="tab"
              aria-selected={mode === "register"}
              onClick={() => {
                setMode("register");
                setError("");
              }}
            >
              Create workspace
            </button>
          </div>

          <aside className={styles.helperNote}>
            <span className={styles.helperNoteLabel}>Quick read before you continue</span>
            <ul className={styles.helperList}>
              {ACCESS_HINTS.map((hint) => (
                <li key={hint}>{hint}</li>
              ))}
            </ul>
          </aside>

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
              I have read the{" "}
              <PolicyLink href="/privacy-policy" policy="privacy_policy" source="signin_checkbox">
                Privacy Policy
              </PolicyLink>
              {" "}and{" "}
              <PolicyLink href="/terms" policy="terms" source="signin_checkbox">
                Terms of Use
              </PolicyLink>
              , and I consent to the processing described in the Privacy Policy.
            </span>
          </label>
          <p className={styles.termsHint}>
            Policy interactions are logged for audit evidence. Current Privacy Policy version: {activePrivacyVersion}.
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
                  <span>Use the same engineering identity your team already uses for code review.</span>
                </span>
              </motion.a>
            ) : (
              <button type="button" className={cx(styles.providerButton, styles.providerDisabled)} disabled>
                <span className={styles.providerIcon} aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.579.688.481C19.138 20.164 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                  </svg>
                </span>
                <span className={styles.providerCopy}>
                  <strong>GitHub OAuth unavailable</strong>
                  <span>Add `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` on the backend to enable this flow.</span>
                </span>
              </button>
            )}

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
                  <span>Use your Google workspace identity if your team runs its reviews that way.</span>
                </span>
              </motion.a>
            ) : (
              <button type="button" className={cx(styles.providerButton, styles.providerDisabled)} disabled>
                <span className={cx(styles.providerIcon, styles.googleIcon)} aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path fillRule="evenodd" clipRule="evenodd" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                    <path fillRule="evenodd" clipRule="evenodd" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
                  </svg>
                </span>
                <span className={styles.providerCopy}>
                  <strong>Google OAuth unavailable</strong>
                  <span>Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` on the backend to enable this flow.</span>
                </span>
              </button>
            )}
          </div>

          <div className={styles.divider}>or use workspace credentials</div>

          <AnimatePresence mode="wait">
            <motion.form
              key={mode}
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={tabTransition}
              className={styles.form}
              onSubmit={submitAuth}
            >
              <label className={styles.field}>
                <span className="auth-label-text">Workspace name</span>
                <div className={cx(styles.inputWrap, "auth-input-wrapper")}>
                  <span className="auth-input-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                      <path d="M16 3h-8l-2 4h12l-2-4z" />
                    </svg>
                  </span>
                  <input
                    autoComplete="username"
                    value={workspace}
                    onChange={(event) => {
                      setWorkspace(event.target.value);
                      setError("");
                    }}
                    placeholder="your-security-team"
                  />
                </div>
                <p className={styles.fieldHint}>
                  Usually the team slug from your invite, a shared link, or the workspace name people mention internally.
                </p>
              </label>

              {mode === "register" && (
                <label className={styles.field}>
                  <span className="auth-label-text">Work email</span>
                  <div className={cx(styles.inputWrap, "auth-input-wrapper")}>
                    <span className="auth-input-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="4" width="20" height="16" rx="2" />
                        <path d="m22 7-10 6L2 7" />
                      </svg>
                    </span>
                    <input
                      autoComplete="email"
                      value={email}
                      onChange={(event) => {
                        setEmail(event.target.value);
                        setError("");
                      }}
                      placeholder="security@company.in"
                      type="email"
                    />
                  </div>
                  <p className={styles.fieldHint}>
                    Optional, but useful if you later connect OAuth or need report delivery and account recovery context.
                  </p>
                </label>
              )}

              <label className={styles.field}>
                <span className="auth-label-text">Password</span>
                <div className={cx(styles.inputWrap, "auth-input-wrapper")}>
                  <span className="auth-input-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                  <input
                    type={showPassword ? "text" : "password"}
                    autoComplete={mode === "register" ? "new-password" : "current-password"}
                    value={password}
                    onChange={(event) => {
                      setPassword(event.target.value);
                      setError("");
                    }}
                    placeholder={mode === "register" ? "Create a workspace password" : "Enter your workspace password"}
                  />
                  <button
                    type="button"
                    className="auth-toggle-pw"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-pressed={showPassword}
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
                <p className={styles.fieldHint}>
                  {mode === "register"
                    ? "This password is stored as a real hash in the backend database. The old mock auto-login path has been removed."
                    : "Password-based login now checks the stored hash in the backend instead of creating a debug user on the fly."}
                </p>
              </label>

              {error && (
                <div className="auth-error-notice" aria-live="polite">
                  {error}
                </div>
              )}

              <motion.button
                whileHover={{ scale: loading ? 1 : 1.01 }}
                whileTap={{ scale: loading ? 1 : 0.99 }}
                className={cx(styles.submitButton, "auth-submit-btn")}
                disabled={loading || loadingContext}
                type="submit"
              >
                {loading && <span className="auth-btn-spinner" />}
                {loading
                  ? mode === "register"
                    ? "Creating workspace..."
                    : "Signing in..."
                  : mode === "register"
                    ? "Create workspace"
                    : "Sign in to console"}
              </motion.button>
            </motion.form>
          </AnimatePresence>

          <p className="auth-card-footer-text">
            {loadingContext
              ? "Loading provider availability and current legal version details."
              : "This screen now uses real backend auth only: register, password login, or configured OAuth."}
          </p>
        </motion.section>
      </div>
    </main>
  );
}

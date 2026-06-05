"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function SignInPage() {
  const router = useRouter();
  const [workspace, setWorkspace] = useState("");
  const [password, setPassword] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(
    () => typeof window !== "undefined" && Boolean(localStorage.getItem("fc_token")),
  );
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  /* Handle OAuth redirect tokens and existing session validation */
  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const urlToken = urlParams.get("token");
      const urlUsername = urlParams.get("username");
      const urlUserId = urlParams.get("user_id");

      if (urlToken && urlUsername && urlUserId) {
        localStorage.setItem("fc_token", urlToken);
        localStorage.setItem("fc_username", urlUsername);
        localStorage.setItem("fc_user_id", urlUserId);
        localStorage.setItem("fc_terms_accepted", "true");
        router.replace("/dashboard");
        return;
      }
    }

    const token = localStorage.getItem("fc_token");
    if (!token) {
      /* Use a microtask to avoid calling setState synchronously inside the effect body */
      queueMicrotask(() => setCheckingSession(false));
      return;
    }

    fetch(`${API_BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((response) => {
        if (!response.ok) {
          localStorage.removeItem("fc_token");
          localStorage.removeItem("fc_username");
          localStorage.removeItem("fc_user_id");
          localStorage.removeItem("fc_terms_accepted");
          setCheckingSession(false);
          return;
        }
        router.replace("/dashboard");
      })
      .catch(() => setCheckingSession(false));
  }, [router]);

  const submitSignIn = useCallback(async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedWorkspace = workspace.trim();

    if (!normalizedWorkspace) {
      setError("Enter your workspace name.");
      return;
    }
    if (!password) {
      setError("Enter your workspace password.");
      return;
    }
    if (!acceptedTerms) {
      setError("You must accept the Terms and Conditions before accessing the console.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: normalizedWorkspace, password }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Unable to create workspace session.");
      }

      const session = await response.json();
      const validation = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!validation.ok) {
        throw new Error("Session validation failed.");
      }

      localStorage.setItem("fc_token", session.access_token);
      localStorage.setItem("fc_username", session.username);
      localStorage.setItem("fc_user_id", session.user_id);
      localStorage.setItem("fc_terms_accepted", "true");
      router.push("/dashboard");
    } catch (signInError) {
      setError(signInError instanceof Error ? signInError.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }, [workspace, password, acceptedTerms, router]);

  /* Session-check loading state */
  if (checkingSession) {
    return (
      <main className="auth-shell">
        <div className="auth-loading-state">
          <div className="auth-loading-spinner" />
          <div className="section-kicker">Session</div>
          <h1 style={{ fontFamily: "var(--font-display), sans-serif", fontSize: "clamp(28px, 5vw, 42px)", letterSpacing: "-0.03em", margin: "8px 0 0" }}>Validating workspace</h1>
          <p style={{ color: "var(--dim)", marginTop: "8px" }}>Verifying your existing FireCrow token…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="auth-shell" id="signin-page">
      {/* ambient decorative elements */}
      <div className="auth-glow-orb auth-glow-orb-1" />
      <div className="auth-glow-orb auth-glow-orb-2" />
      <div className="auth-grid-overlay" />

      {/* top-left brand */}
      <Link className="auth-brand animate-fade-in" href="/" id="auth-brand-link">
        <span className="brand-mark">FC</span>
        <span>
          <strong>FireCrow</strong>
          <small>by Nova Devs</small>
        </span>
      </Link>

      {/* login card */}
      <section className="auth-card animate-fade-in delay-100" id="auth-login-card">
        {/* decorative top bar accent */}
        <div className="auth-card-accent" />

        <div className="auth-card-header">
          <div className="section-kicker">Secure Access</div>
          <h1>Welcome back</h1>
          <p>
            Sign in to your workspace to access the orchestration console, audit history, and agent network.
          </p>
        </div>

        {/* OAuth buttons */}
        <div className="oauth-group">
          <a
            href={`${API_BASE_URL}/auth/github`}
            className="oauth-button oauth-github"
            id="oauth-github-btn"
            onClick={(e) => {
              if (!acceptedTerms) {
                e.preventDefault();
                setError("You must accept the Terms and Conditions before accessing the console.");
              }
            }}
          >
            <svg style={{ width: 18, height: 18 }} viewBox="0 0 24 24" fill="currentColor">
              <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.579.688.481C19.138 20.164 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
            </svg>
            Continue with GitHub
          </a>
          <a
            href={`${API_BASE_URL}/auth/google`}
            className="oauth-button oauth-google"
            id="oauth-google-btn"
            onClick={(e) => {
              if (!acceptedTerms) {
                e.preventDefault();
                setError("You must accept the Terms and Conditions before accessing the console.");
              }
            }}
          >
            <svg style={{ width: 18, height: 18 }} viewBox="0 0 24 24" fill="currentColor">
              <path fillRule="evenodd" clipRule="evenodd" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path fillRule="evenodd" clipRule="evenodd" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path fillRule="evenodd" clipRule="evenodd" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
              <path fillRule="evenodd" clipRule="evenodd" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
            </svg>
            Continue with Google
          </a>
        </div>

        <div className="oauth-divider">or sign in with credentials</div>

        {/* credential form */}
        <form className="auth-form" onSubmit={submitSignIn} id="signin-form">
          <label>
            <span className="auth-label-text">Workspace name</span>
            <div className="auth-input-wrapper">
              <svg className="auth-input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 3h-8l-2 4h12l-2-4z"/></svg>
              <input
                autoComplete="organization"
                value={workspace}
                onChange={(event) => setWorkspace(event.target.value)}
                placeholder="your-security-team"
                id="signin-workspace-input"
              />
            </div>
          </label>

          <label>
            <span className="auth-label-text">Password</span>
            <div className="auth-input-wrapper">
              <svg className="auth-input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <input
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                id="signin-password-input"
              />
              <button type="button" className="auth-toggle-pw" onClick={() => setShowPassword(!showPassword)} tabIndex={-1} aria-label="Toggle password visibility">
                {showPassword ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                )}
              </button>
            </div>
          </label>

          <label className="terms-check">
            <input
              checked={acceptedTerms}
              onChange={(event) => setAcceptedTerms(event.target.checked)}
              type="checkbox"
              id="signin-terms-checkbox"
            />
            <span>
              I agree to the <Link href="/terms">Terms and Conditions</Link> for FireCrow by Nova Devs.
            </span>
          </label>

          {error && <div className="notice notice-error auth-error-notice">{error}</div>}

          <button className="primary-action auth-submit-btn" disabled={loading} type="submit" id="signin-submit-btn">
            {loading && <span className="auth-btn-spinner" />}
            {loading ? "Signing in…" : "Sign in to Console"}
          </button>
        </form>

        <p className="auth-card-footer-text">
          Don&apos;t have a workspace? Credentials are auto-provisioned on first login.
        </p>
      </section>

      {/* bottom footnote */}
      <p className="auth-footnote animate-fade-in delay-300" id="auth-footnote">
        Need to review the product terms? <Link href="/terms">Read the Terms and Conditions</Link>.
      </p>
    </main>
  );
}

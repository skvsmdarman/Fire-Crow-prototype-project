"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { motion as framerMotion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useAuthSession } from "../../shared/hooks/useAuthSession";
import { usePolicyContext } from "../../features/auth/hooks";
import { exchangeCode, loginUser, registerUser } from "../../features/auth/api";
import { detectRegionFromTimezone } from "../../lib/policyData";
import { buildApiUrl } from "../../shared/api/baseUrl";
import { PRODUCT_NAME, PRODUCT_TAGLINE } from "../../shared/config/app";
import styles from "./page.module.css";

type AuthMode = "login" | "register";

function getClientPolicyMeta() {
  if (typeof window === "undefined") {
    return { timezone: undefined, region: undefined };
  }
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return { timezone, region: detectRegionFromTimezone(timezone) };
}

const exchangedCodes = new Set<string>();

export default function SignInPage() {
  const router = useRouter();
  const authSession = useAuthSession();
  const login = authSession.login;
  const { activePrivacyVersion, providerAvailability } = usePolicyContext();

  const [mode, setMode] = useState<AuthMode>("login");
  const [workspaceName, setWorkspaceName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (authSession.hasDashboardSession && authSession.workspace) {
      router.push(`/dashboard?workspace=${encodeURIComponent(authSession.workspace)}`);
    }
  }, [authSession.hasDashboardSession, authSession.workspace, router]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const code = new URLSearchParams(window.location.search).get("code") ?? "";
    if (!code || exchangedCodes.has(code)) return;

    exchangedCodes.add(code);

    async function finishOauthSignIn() {
      try {
        setError("");
        setLoading(true);
        const session = await exchangeCode(code);
        login({ user_id: session.user_id, username: session.username });
        router.replace(`/dashboard?workspace=${encodeURIComponent(session.username)}`);
      } catch (authError) {
        const err = authError as { message?: string };
        setError(err.message || "Unable to finish sign-in.");
        const nextUrl = new URL(window.location.href);
        nextUrl.searchParams.delete("code");
        window.history.replaceState({}, "", nextUrl.toString());
      } finally {
        setLoading(false);
      }
    }

    void finishOauthSignIn();
    return () => {
      // Note: exchangedCodes cleanup is intentionally not done here
      // as it's a global deduplication set for the session
    };
  }, [login, router]);

  const oauthHref = (provider: "github" | "google") => {
    let authUrl = buildApiUrl(`/auth/${provider}?privacy_policy_accepted=true&privacy_policy_version=${activePrivacyVersion}`);
    if (typeof window !== "undefined") {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      authUrl += `&timezone=${encodeURIComponent(tz)}&region=${encodeURIComponent(detectRegionFromTimezone(tz))}`;
    }
    return authUrl;
  };


  const oauthProviderCount = Number(providerAvailability.github) + Number(providerAvailability.google);
  const passwordAvailable = providerAvailability.password || oauthProviderCount === 0;

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const username = workspaceName.trim();
    const trimmedEmail = email.trim();
    if (!username) return setError("Workspace name is required.");
    if (!password) return setError("Workspace password is required.");
    if (mode === "register" && password.length < 8) {
      return setError("Password must be at least 8 characters.");
    }

    setLoading(true);
    setError("");
    const policyMeta = getClientPolicyMeta();

    try {
      const payload = {
        username,
        password,
        privacy_policy_accepted: true,
        privacy_policy_version: activePrivacyVersion,
        timezone: policyMeta.timezone,
        region: policyMeta.region,
        ...(mode === "register" && trimmedEmail ? { email: trimmedEmail } : {}),
      };
      const session = mode === "register" ? await registerUser(payload) : await loginUser(payload);
      login({ user_id: session.user_id, username: session.username });
      router.replace(`/dashboard?workspace=${encodeURIComponent(session.username)}`);
    } catch (authError) {
      const err = authError as { message?: string };
      setError(err.message || "Unable to authenticate workspace.");
    } finally {
      setLoading(false);
    }
  }

  if (authSession.hasDashboardSession) return null;

  return (
    <div className={styles.page}>
      <div className={styles.backdrop} />
      <div className={styles.gridGlow} />
      <div className={styles.centerContainer}>
        <framerMotion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} style={{ width: "100%" }}>
          <div className={styles.logoContainer}>
            <div className={styles.brand}>
              <span className={styles.brandMark}>FC</span>
              <span className={styles.brandText}>
                <strong>{PRODUCT_NAME}</strong>
                <small>{PRODUCT_TAGLINE}</small>
              </span>
            </div>
          </div>

          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <p className={styles.eyebrow}>{mode === "login" ? "Welcome back" : "Create workspace"}</p>
              <h2>{mode === "login" ? "Sign in to Fire Crow" : "Start your workspace"}</h2>
              <p>
                {mode === "login"
                  ? "Use workspace credentials, or continue with a configured OAuth provider."
                  : "Create a workspace to run authorized repository reviews and download reports."}
              </p>
            </div>

            {passwordAvailable && (
              <form className={styles.form} onSubmit={handlePasswordSubmit}>
                <label className={styles.field}>
                  <span>Workspace name</span>
                  <div className={styles.inputWrap}>
                    <span className={styles.inputIcon}>@</span>
                    <input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} placeholder="acme-security" autoComplete="username" required />
                  </div>
                </label>

                {mode === "register" && (
                  <label className={styles.field}>
                    <span>Email optional</span>
                    <div className={styles.inputWrap}>
                      <span className={styles.inputIcon}>✉</span>
                      <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="team@example.com" autoComplete="email" />
                    </div>
                  </label>
                )}

                <label className={styles.field}>
                  <span>Password</span>
                  <div className={styles.inputWrap}>
                    <span className={styles.inputIcon}>••</span>
                    <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={mode === "register" ? "Minimum 8 characters" : "Workspace password"} autoComplete={mode === "register" ? "new-password" : "current-password"} minLength={mode === "register" ? 8 : undefined} required />
                  </div>
                </label>

                <button className={styles.submitButton} type="submit" disabled={loading}>
                  {loading && <span className={styles.submitSpinner} />}
                  {loading ? "Please wait..." : mode === "login" ? "Sign in" : "Create workspace"}
                </button>
              </form>
            )}

            <button type="button" className={styles.modeButton} onClick={() => { setMode((current) => (current === "login" ? "register" : "login")); setError(""); }}>
              {mode === "login" ? "Need a workspace? Create one" : "Already have a workspace? Sign in"}
            </button>

            {oauthProviderCount > 0 && (
              <>
                {passwordAvailable && <div className={styles.divider}>or continue with</div>}
                <div className={styles.providerStack}>
                  {providerAvailability.github && <a href={oauthHref("github")} className={styles.providerButton}><span className={styles.providerIcon}>GH</span><span className={styles.providerCopy}><strong>Continue with GitHub</strong></span></a>}
                  {providerAvailability.google && <a href={oauthHref("google")} className={`${styles.providerButton} ${styles.googleIcon}`}><span className={styles.providerIcon}>G</span><span className={styles.providerCopy}><strong>Continue with Google</strong></span></a>}
                </div>
              </>
            )}

            {!passwordAvailable && oauthProviderCount === 0 && <div className={styles.errorNotice}>No sign-in provider is configured.</div>}
            {error && <div className={styles.errorNotice}>{error}</div>}

            <p className={styles.cardFootnote}>
              By continuing you accept the <a href="/terms">Terms of Use</a> and <a href="/privacy">Privacy Policy</a>.
            </p>
          </div>
        </framerMotion.div>
      </div>
    </div>
  );
}

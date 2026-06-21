"use client";

import Link from "next/link";

import { usePolicyContext } from "../features/auth/hooks";
import { detectRegionFromTimezone } from "../lib/policyData";
import { buildApiUrl, isAbsoluteUrl } from "../shared/api/baseUrl";
import { PRODUCT_NAME, PRODUCT_TAGLINE } from "../shared/config/app";
import styles from "./page.module.css";

const providers = [
  { id: "github", label: "Continue with GitHub", note: "Best for repository access" },
  { id: "google", label: "Continue with Google", note: "Best for workspace identity" },
] as const;

export default function LandingPage() {
  const { activePrivacyVersion, loadingContext, providerAvailability } = usePolicyContext();

  const oauthHref = (provider: "github" | "google") => {
    const authUrl = buildApiUrl(`/auth/${provider}`);
    const url = isAbsoluteUrl(authUrl)
      ? new URL(authUrl)
      : new URL(authUrl, typeof window !== "undefined" ? window.location.origin : "https://firecrow.invalid");

    url.searchParams.set("privacy_policy_accepted", "true");
    url.searchParams.set("privacy_policy_version", activePrivacyVersion);

    if (typeof window !== "undefined") {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      url.searchParams.set("timezone", timezone);
      url.searchParams.set("region", detectRegionFromTimezone(timezone));
    }

    return isAbsoluteUrl(authUrl) ? url.toString() : `${url.pathname}${url.search}`;
  };

  const oauthUnavailable =
    !loadingContext && !providerAvailability.github && !providerAvailability.google;

  return (
    <main className={styles.page}>
      <section className={styles.shell} aria-label="Fire Crow secure sign in">
        <div className={styles.brandBlock}>
          <Link href="/" className={styles.brand} aria-label={`${PRODUCT_NAME} home`}>
            <span className={styles.brandMark}>FC</span>
            <span className={styles.brandText}>
              <strong>{PRODUCT_NAME}</strong>
              <small>{PRODUCT_TAGLINE}</small>
            </span>
          </Link>
        </div>

        <div className={styles.heroCard}>
          <p className={styles.eyebrow}>One tap secure access</p>
          <h1>Enter Fire Crow with a verified identity.</h1>
          <p className={styles.subtitle}>
            Sign in with GitHub or Google. Fire Crow keeps access controlled,
            consent-aware, and backed by server-managed session cookies.
          </p>

          <div className={styles.providerStack} aria-label="Sign in providers">
            {providers.map((provider) => (
              <a
                key={provider.id}
                href={oauthHref(provider.id)}
                className={styles.providerButton}
              >
                <span className={styles.providerIcon}>{provider.id === "github" ? "GH" : "G"}</span>
                <span className={styles.providerCopy}>
                  <strong>{provider.label}</strong>
                  <small>{provider.note}</small>
                </span>
              </a>
            ))}
          </div>

          {oauthUnavailable && (
            <p className={styles.warning}>
              GitHub and Google OAuth are not configured on the backend yet.
            </p>
          )}

          <div className={styles.trustRow} aria-label="Security notes">
            <span>OAuth only</span>
            <span>HttpOnly session</span>
            <span>Policy consent</span>
          </div>
        </div>

        <footer className={styles.footer}>
          <Link href="/terms">Terms</Link>
          <span>/</span>
          <Link href="/privacy">Privacy</Link>
        </footer>
      </section>
    </main>
  );
}

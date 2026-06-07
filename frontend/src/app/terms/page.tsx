"use client";

import Link from "next/link";
import { useState, useSyncExternalStore } from "react";

import PolicyLink from "../../features/legal/components/PolicyLink";
import PolicyPageTracker from "../../features/legal/components/PolicyPageTracker";
import Footer from "../../components/Footer";
import { TERMS_VERSION } from "../../lib/policy";
import {
  TERMS_SECTIONS,
  REGION_OPTIONS,
  detectRegionFromTimezone
} from "../../lib/policyData";
import styles from "./policy-tabs.module.css";

const readClientTimezone = () =>
  (typeof window !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "") || "";
const subscribeToClientTimezone = () => () => undefined;

export default function TermsPage() {
  const timezone = useSyncExternalStore(subscribeToClientTimezone, readClientTimezone, () => "");
  const detectedRegion = detectRegionFromTimezone(timezone);
  const [selectedRegionOverride, setSelectedRegionOverride] = useState<"global" | "in" | "eu" | "us" | null>(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const selectedRegion = selectedRegionOverride ?? detectedRegion;
  const showBanner = detectedRegion !== "global" && !bannerDismissed;

  // Filter clauses: show global clauses + clauses matching the selected region
  const activeClauses = TERMS_SECTIONS.filter(
    (clause) => clause.regions.includes("global") || clause.regions.includes(selectedRegion)
  );

  const detectedRegionOption = REGION_OPTIONS.find((r) => r.code === detectedRegion);

  return (
    <main className="legal-shell">
      <PolicyPageTracker policy="terms" policyVersion={TERMS_VERSION} source="terms_page" />

      <nav className="public-nav legal-nav" aria-label="Terms navigation">
        <Link className="public-brand" href="/">
          <span className="brand-mark">FC</span>
          <span>
            <strong>FireCrow</strong>
            <small>by Nova Devs</small>
          </span>
        </Link>
        <div className="public-nav-links">
          <Link href="/">Home</Link>
          <PolicyLink href="/privacy-policy" policy="privacy_policy" source="terms_nav">
            Privacy Policy
          </PolicyLink>
          <Link className="nav-cta" href="/signin">Sign in</Link>
        </div>
      </nav>

      <section className="legal-hero">
        <div className="section-kicker">Legal Framework</div>
        <h1>Terms of Service</h1>
        <p>
          Governing the subscription, code auditing, and automated defensive security execution boundaries.
        </p>
        <span>Version: {TERMS_VERSION}</span>
      </section>

      {/* Timezone Detection Banner */}
      {showBanner && detectedRegionOption && (
        <div className={styles.timezoneBanner}>
          <div className={styles.bannerLeft}>
            <span className={styles.bannerIcon}>🗺️</span>
            <div className={styles.bannerText}>
              We detected your timezone is <strong>{timezone}</strong>. We have loaded terms compliant with
              {" "}
              <strong>{detectedRegionOption.name}</strong> legal standards ({detectedRegionOption.badge}).
            </div>
          </div>
          <button className={styles.closeBanner} onClick={() => setBannerDismissed(true)} aria-label="Close banner">
            &times;
          </button>
        </div>
      )}

      {/* Regional Selector Tabs */}
      <div className={styles.tabBar} role="tablist" aria-label="Regional compliance clauses">
        {REGION_OPTIONS.map((region) => (
          <button
            key={region.code}
            role="tab"
            aria-selected={selectedRegion === region.code}
            className={`${styles.tabButton} ${selectedRegion === region.code ? styles.activeTab : ""}`}
            onClick={() => setSelectedRegionOverride(region.code)}
          >
            <span>{region.flag}</span>
            <span>{region.name}</span>
            {detectedRegion === region.code && (
              <span className={styles.detectedBadge}>Detected</span>
            )}
          </button>
        ))}
      </div>

      <section className="legal-card" style={{ padding: "8px 24px" }}>
        <div className={styles.clauseList}>
          {activeClauses.map((clause) => {
            const isRegionSpecific = !clause.regions.includes("global");
            return (
              <article
                className={`${styles.clauseCard} ${isRegionSpecific ? styles.highlightedCard : ""}`}
                key={clause.id}
              >
                <div className={styles.clauseCardHeader}>
                  <h2 className={styles.clauseTitle}>{clause.title}</h2>
                  <div className={styles.clauseBadges}>
                    {clause.regions.map((r) => {
                      const regOpt = REGION_OPTIONS.find((o) => o.code === r);
                      if (!regOpt) return null;
                      return (
                        <span
                          key={r}
                          className={`${styles.regionBadge} ${
                            r === "global"
                              ? styles.badgeGlobal
                              : r === "in"
                              ? styles.badgeIn
                              : r === "eu"
                              ? styles.badgeEu
                              : styles.badgeUs
                          }`}
                        >
                          {regOpt.flag} {regOpt.badge.split(" ")[0]}
                        </span>
                      );
                    })}
                  </div>
                </div>
                <p className={styles.clauseBody}>{clause.body}</p>
              </article>
            );
          })}
        </div>
      </section>

      <Footer />
    </main>
  );
}

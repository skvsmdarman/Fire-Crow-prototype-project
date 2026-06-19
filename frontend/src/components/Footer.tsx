"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";
import PolicyLink from "./PolicyLink";
import {
  getServerAuthSessionSnapshot,
  getStoredAuthSessionSnapshot,
  subscribeToAuthSession
} from "../lib/authSession";
import styles from "./Footer.module.css";
import BrandLogo from "./BrandLogo";
import { COMPANY_NAME, COMPANY_NAME_SHORT, SUPPORT_EMAIL, COPYRIGHT_YEAR } from "../shared/config/app";

export default function Footer() {
  const session = useSyncExternalStore(
    subscribeToAuthSession,
    getStoredAuthSessionSnapshot,
    getServerAuthSessionSnapshot
  );
  const isLoggedIn = session.hasConsoleSession;

  return (
    <footer className={styles.footerWrapper}>
      <div className={styles.footerContainer}>
        {/* Brand/Logo Column */}
        <div className={styles.brandCol}>
          <div className={styles.logoWrapper}>
            <BrandLogo isLink={false} />
            <div className={styles.logoSubtitle}>
              AGENTIC SECURITY INTELLIGENCE PLATFORM
            </div>
          </div>
          <p className={styles.brandDescription}>
            Continuous offensive security audits, secret scanning, and automated sandbox validation.
          </p>
          <div className={styles.novalabsBadge}>
            A product from <strong className={styles.highlightText}>{COMPANY_NAME_SHORT}</strong>
          </div>
        </div>

        {/* Links Columns */}
        <div className={styles.linksCol}>
          <h4>Platform</h4>
          <ul>
            <li>
              <Link href="/#capabilities">Capabilities</Link>
            </li>
            <li>
              <Link href="/#workflow">Workflow</Link>
            </li>
            <li>
              <Link href="/#agents">Agent Network</Link>
            </li>
            <li>
              <Link href={isLoggedIn ? "/dashboard" : "/signin"}>
                {isLoggedIn ? "Dashboard" : "Open Console"}
              </Link>
            </li>
          </ul>
        </div>

        <div className={styles.linksCol}>
          <h4>Legal</h4>
          <ul>
            <li>
              <PolicyLink href="/terms" policy="terms" source="footer_legal">
                Terms of Use
              </PolicyLink>
            </li>
            <li>
              <PolicyLink href="/privacy" policy="privacy_policy" source="footer_legal">
                Privacy Policy
              </PolicyLink>
            </li>
          </ul>
        </div>

        <div className={styles.linksCol}>
          <h4>Security Contact</h4>
          <ul>
            <li>
              <span className={styles.footerEmail}>{SUPPORT_EMAIL}</span>
            </li>
            <li>
              <span className={styles.addressLabel}>Address/Operator:</span>
              <span className={styles.addressValue}>{COMPANY_NAME} (an online developer team)</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Bottom Status bar */}
      <div className={styles.footerBottom}>
        <span className={styles.copyrightText}>
          &copy; {COPYRIGHT_YEAR} FireCrow. All rights reserved.
        </span>
        <div className={styles.statusPill}>
          <span className={styles.statusDot} />
          <span>{COMPANY_NAME} Network: Operational</span>
        </div>
      </div>
    </footer>
  );
}

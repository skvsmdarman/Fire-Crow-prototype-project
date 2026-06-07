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
            <div className={styles.logoRow}>
              {/* Flame Silhouette Icon */}
              <svg className={styles.logoFlame} viewBox="0 0 100 100" fill="currentColor" aria-hidden="true">
                <path d="M50 12C50 12 74 38 74 62C74 76.4 62.4 88 48 88C33.6 88 22 76.4 22 62C22 46 36 26 42 16C43 14.5 45 15.5 45 17.5C44 26 49 32 53 37C55 35 54 31 53 28C52.5 26.5 54 25 55 26C59 30 62 36 62 43C62 50.7 55.7 57 48 57C40.3 57 34 50.7 34 43C34 38 37.5 31.5 41 28" />
              </svg>
              {/* Brand Text */}
              <span className={styles.logoTitle}>FIRE CROW</span>
              {/* Crow Silhouette Icon */}
              <svg className={styles.logoCrow} viewBox="0 0 100 100" fill="currentColor" aria-hidden="true">
                <path d="M78 35C74 37 69 35 64 30C59 25 51 25 45 30C43 32 41 35 39 38C31 38 24 43 21 50C20 52 21 54 23 54C27 52 31 52 35 54C34 57 32 60 30 63C29 65 30 67 32 67C37 63 41 58 44 53C45 57 47 61 49 65C50 67 52 67 53 65C57 57 63 50 71 45C74 47 77 50 79 53C80 54 82 54 83 53C85 50 87 45 87 40C87 37 84 35 78 35Z" />
              </svg>
            </div>
            <div className={styles.logoSubtitle}>
              AGENTIC SECURITY INTELLIGENCE PLATFORM
            </div>
          </div>
          <p className={styles.brandDescription}>
            Continuous offensive security audits, secret scanning, and automated sandbox validation.
          </p>
          <div className={styles.novalabsBadge}>
            A product from <strong className={styles.highlightText}>Nova labs</strong>
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
              <PolicyLink href="/privacy-policy" policy="privacy_policy" source="footer_legal">
                Privacy Policy
              </PolicyLink>
            </li>
          </ul>
        </div>

        <div className={styles.linksCol}>
          <h4>Security Contact</h4>
          <ul>
            <li>
              <span className={styles.footerEmail}>security@novadevs.dev</span>
            </li>
            <li>
              <span className={styles.addressLabel}>Address/Operator:</span>
              <span className={styles.addressValue}>Nova Devs (an online developer team)</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Bottom Status bar */}
      <div className={styles.footerBottom}>
        <span className={styles.copyrightText}>
          &copy; {new Date().getFullYear()} FireCrow. All rights reserved.
        </span>
        <div className={styles.statusPill}>
          <span className={styles.statusDot} />
          <span>Nova Devs Network: Operational</span>
        </div>
      </div>
    </footer>
  );
}

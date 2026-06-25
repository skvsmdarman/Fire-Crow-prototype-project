"use client";

import { useState, useRef, useEffect } from "react";
import BrandLogo from "../BrandLogo";
import styles from "./Navbar.module.css";
import { usePolicyContext } from "../../features/auth/hooks";
import { detectRegionFromTimezone } from "../../lib/policyData";
import { buildApiUrl } from "../../shared/api/baseUrl";

interface NavbarProps {
  isLoggedIn: boolean;
  onEnter: () => void;
}

export default function Navbar({ isLoggedIn, onEnter }: NavbarProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { activePrivacyVersion, providerAvailability } = usePolicyContext();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getOauthHref = (provider: "github" | "google") => {
    let authUrl = buildApiUrl(`/auth/${provider}?privacy_policy_accepted=true&privacy_policy_version=${activePrivacyVersion}`);
    if (typeof window !== "undefined") {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      authUrl += `&timezone=${encodeURIComponent(tz)}&region=${encodeURIComponent(detectRegionFromTimezone(tz))}`;
    }
    return authUrl;
  };

  const handleSignInClick = () => {
    if (isLoggedIn) {
      onEnter();
    } else {
      setIsDropdownOpen(!isDropdownOpen);
    }
  };

  return (
    <nav className={styles.nav}>
      <BrandLogo className={styles.brand} isLink={true} />
      <div className={styles.navLinks}>
        <a href="#platform" className={styles.navLink}>
          Platform
        </a>
        <a href="#capabilities" className={styles.navLink}>
          Capabilities
        </a>
        <a href="#pipeline" className={styles.navLink}>
          Pipeline
        </a>
        <a href="#agents" className={styles.navLink}>
          Agents
        </a>
        
        <div className={styles.ctaWrapper} ref={dropdownRef}>
          <button onClick={handleSignInClick} className={styles.navCta}>
            {isLoggedIn ? "Dashboard" : "Sign in"}
          </button>
          
          {!isLoggedIn && isDropdownOpen && (
            <div className={styles.dropdown}>
              <div className={styles.dropdownHeader}>
                Sign in to workspace
              </div>
              <div className={styles.dropdownBody}>
                {providerAvailability.github && (
                  <a href={getOauthHref("github")} className={styles.providerButton}>
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                    <span>Continue with GitHub</span>
                  </a>
                )}
                {providerAvailability.google && (
                  <a href={getOauthHref("google")} className={`${styles.providerButton} ${styles.google}`}>
                    <svg viewBox="0 0 24 24" width="16" height="16">
                      <path fill="#EA4335" d="M12 5.04c1.66 0 3.2.57 4.38 1.69l3.27-3.27C17.67 1.54 14.98 0 12 0 7.35 0 3.37 2.67 1.39 6.56l3.87 3a7.18 7.18 0 0 1 6.74-4.52z"/>
                      <path fill="#4285F4" d="M23.49 12.27c0-.81-.07-1.59-.2-2.36H12v4.51h6.43a5.5 5.5 0 0 1-2.39 3.61l3.71 2.88c2.17-2 3.74-4.94 3.74-8.64z"/>
                      <path fill="#FBBC05" d="M5.26 14.12a7.15 7.15 0 0 1 0-4.24l-3.87-3a11.96 11.96 0 0 0 0 10.24l3.87-3z"/>
                      <path fill="#34A853" d="M12 24c3.24 0 5.97-1.07 7.96-2.91l-3.71-2.88a7.14 7.14 0 0 1-10.99-3.69l-3.87 3C3.37 21.33 7.35 24 12 24z"/>
                    </svg>
                    <span>Continue with Google</span>
                  </a>
                )}
                <button onClick={onEnter} className={styles.passwordLink}>
                  or use workspace credentials
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

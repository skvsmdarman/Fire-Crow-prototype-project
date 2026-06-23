"use client";

import BrandLogo from "../BrandLogo";
import styles from "./Navbar.module.css";

interface NavbarProps {
  isLoggedIn: boolean;
  onEnter: () => void;
}

export default function Navbar({ isLoggedIn, onEnter }: NavbarProps) {
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
        <button onClick={onEnter} className={styles.navCta}>
          {isLoggedIn ? "Dashboard" : "Sign in"}
        </button>
      </div>
    </nav>
  );
}

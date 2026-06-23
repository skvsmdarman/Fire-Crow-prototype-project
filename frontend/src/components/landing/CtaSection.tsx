"use client";

import styles from "./CtaSection.module.css";

interface CtaSectionProps {
  isLoggedIn: boolean;
  onEnter: () => void;
}

export default function CtaSection({ isLoggedIn, onEnter }: CtaSectionProps) {
  return (
    <section className={styles.section}>
      <div className={styles.content}>
        <span className={styles.eyebrow}>GET STARTED</span>
        <h2 className={styles.title}>Ready to secure your repository?</h2>
        <p className={styles.copy}>
          Connect your codebase and receive a comprehensive, evidence-backed security assessment within minutes. Stop guessing and start securing with automated sandbox validation.
        </p>
        <button onClick={onEnter} className={styles.ctaButton}>
          {isLoggedIn ? "Go to Dashboard" : "Start a Free Audit →"}
        </button>
      </div>
      <div className={styles.glow} />
    </section>
  );
}

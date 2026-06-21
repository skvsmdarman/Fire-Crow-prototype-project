import Link from "next/link";

import { PRODUCT_TAGLINE } from "../shared/config/app";
import styles from "./page.module.css";

export default function LandingPage() {
  return (
    <main className={styles.page}>
      <section className={styles.shell}>
        <nav className={styles.nav} aria-label="Primary navigation">
          <Link href="/" className={styles.brand} aria-label="Fire Crow home">
            <span className={styles.brandMark}>FC</span>
            <span className={styles.brandText}>
              <strong>Fire Crow</strong>
              <small>{PRODUCT_TAGLINE}</small>
            </span>
          </Link>

          <div className={styles.navActions}>
            <Link href="/workflow" className={styles.textLink}>
              Workflow
            </Link>
            <Link href="/signin" className={styles.navButton}>
              Sign in
            </Link>
          </div>
        </nav>

        <div className={styles.hero}>
          <p className={styles.eyebrow}>FCv1 · Authorization-only security audits</p>
          <h1 className={styles.title}>
            Audit your repository without the noise.
          </h1>
          <p className={styles.subtitle}>
            Fire Crow runs evidence-backed repository checks, streams execution logs,
            and prepares remediation-ready reports for teams that are authorized to test their code.
          </p>

          <div className={styles.actions}>
            <Link href="/signin" className={styles.primaryAction}>
              Start audit
            </Link>
            <Link href="/dashboard" className={styles.secondaryAction}>
              Open dashboard
            </Link>
          </div>
        </div>

        <div className={styles.trustGrid} aria-label="Platform principles">
          <article className={styles.trustCard}>
            <span>01</span>
            <h2>Authorized only</h2>
            <p>Users must confirm they own or are permitted to test the target repository.</p>
          </article>
          <article className={styles.trustCard}>
            <span>02</span>
            <h2>Evidence first</h2>
            <p>Findings are built around reproducible evidence, logs, and remediation guidance.</p>
          </article>
          <article className={styles.trustCard}>
            <span>03</span>
            <h2>Report ready</h2>
            <p>Completed audits can produce downloadable reports through authenticated routes.</p>
          </article>
        </div>
      </section>
    </main>
  );
}

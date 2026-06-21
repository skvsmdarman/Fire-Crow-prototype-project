import Link from "next/link";

import { PRODUCT_NAME, PRODUCT_TAGLINE } from "../shared/config/app";
import styles from "./page.module.css";

const capabilities = [
  {
    title: "Repository review",
    copy: "Collect code, dependency, and configuration signals into one structured workspace.",
  },
  {
    title: "Clear authorization",
    copy: "Keep the product flow explicit about repository ownership and permitted review scope.",
  },
  {
    title: "Readable reports",
    copy: "Organize findings with severity, evidence notes, and remediation guidance.",
  },
];

const flow = ["Authorize", "Review", "Validate", "Report"];

export default function LandingPage() {
  return (
    <main className={styles.page}>
      <section className={styles.shell}>
        <nav className={styles.nav} aria-label="Primary navigation">
          <Link href="/" className={styles.brand} aria-label={`${PRODUCT_NAME} home`}>
            <span className={styles.brandMark}>FC</span>
            <span className={styles.brandText}>
              <strong>{PRODUCT_NAME}</strong>
              <small>{PRODUCT_TAGLINE}</small>
            </span>
          </Link>

          <div className={styles.navActions}>
            <Link href="/workflow" className={styles.textLink}>
              Workflow
            </Link>
            <Link href="/agents" className={styles.textLink}>
              Agents
            </Link>
            <Link href="/signin" className={styles.navButton}>
              Sign in
            </Link>
          </div>
        </nav>

        <section className={styles.hero} aria-labelledby="hero-title">
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>Fire Crow · FCv1</p>
            <h1 id="hero-title" className={styles.title}>
              Serious repository review without a noisy interface.
            </h1>
            <p className={styles.subtitle}>
              Fire Crow turns an authorized repository into a clean review workspace:
              scanner signals, validation notes, risk scoring, and a remediation report.
            </p>

            <div className={styles.actions}>
              <Link href="/signin" className={styles.primaryAction}>
                Start review
              </Link>
              <Link href="/dashboard" className={styles.secondaryAction}>
                Open dashboard
              </Link>
            </div>
          </div>

          <aside className={styles.panel} aria-label="Workflow preview">
            <div className={styles.panelHeader}>
              <span>Workflow</span>
              <strong>Clean and controlled</strong>
            </div>
            <div className={styles.flowList}>
              {flow.map((item, index) => (
                <div key={item} className={styles.flowItem}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <strong>{item}</strong>
                </div>
              ))}
            </div>
            <p className={styles.panelNote}>
              The dashboard keeps authorization, repository scope, progress, and report actions visible before work starts.
            </p>
          </aside>
        </section>

        <section className={styles.capabilitySection} aria-label="Core capabilities">
          <div className={styles.sectionHeader}>
            <p className={styles.eyebrow}>Platform</p>
            <h2>Minimal interface. Serious backend.</h2>
          </div>

          <div className={styles.cardGrid}>
            {capabilities.map((capability) => (
              <article key={capability.title} className={styles.card}>
                <h3>{capability.title}</h3>
                <p>{capability.copy}</p>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

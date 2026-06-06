import Link from "next/link";

import PolicyLink from "../../components/PolicyLink";
import PolicyPageTracker from "../../components/PolicyPageTracker";
import { PRIVACY_POLICY_VERSION } from "../../lib/policy";

const PRIVACY_SECTIONS = [
  {
    title: "1. Why This Policy Exists",
    body: "This Privacy Policy explains how FireCrow handles personal data and security-related information connected with workspace authentication, policy acknowledgement, repository audit workflows, and generated reports. It is structured to support the publication and notice expectations reflected in the Information Technology Act, 2000 and the Information Technology (Reasonable Security Practices and Procedures and Sensitive Personal Data or Information) Rules, 2011.",
  },
  {
    title: "2. Data We Collect",
    body: "Depending on the feature used, FireCrow may process workspace names, hashed passwords, OAuth provider identifiers, email addresses, IP addresses, user-agent strings, repository URLs, branch names, generated findings, audit evidence, and access/log records for legal, operational, and security review.",
  },
  {
    title: "3. Purpose of Collection",
    body: "We process this data to authenticate users, authorize workspace access, run security audits, generate reports, preserve compliance evidence, detect misuse, investigate incidents, and maintain the integrity of the FireCrow service.",
  },
  {
    title: "4. Consent and Notice Logging",
    body: "When a user opens the Privacy Policy or Terms of Use, clicks those links, or submits authentication after acknowledging the Privacy Policy, FireCrow records timestamps, IP address, user agent, policy version, and related event metadata in the database to preserve an auditable compliance trail.",
  },
  {
    title: "5. Disclosure and Sharing",
    body: "FireCrow may disclose data only to authorized operators, cloud/service providers, or legal/regulatory recipients who need it for hosting, authentication, storage, support, incident response, or compliance. Repository findings and reports should be shared only within the authorized scope of the audit.",
  },
  {
    title: "6. Security Practices",
    body: "Passwords are stored as hashes, authentication and policy events are logged, and access tokens are validated by the backend before protected actions are allowed. Operators should still review infrastructure, transport security, storage controls, and retention settings before production use.",
  },
  {
    title: "7. Retention",
    body: "Authentication records, audit jobs, findings, and policy logs are retained for operational history, security review, and legal/compliance evidence until deleted under the operator's retention rules or applicable legal obligations.",
  },
  {
    title: "8. Review, Correction, and Contact",
    body: "If you need to review or correct your account information, or have a privacy or grievance request, contact the designated Grievance Officer / privacy contact at security@novadevs.dev. Production operators should replace this with the real grievance officer name, postal address, and contact details used by the service operator.",
  },
  {
    title: "9. Policy Updates",
    body: "When this policy changes, FireCrow should publish the revised version and record the new version string when users next acknowledge it through the application.",
  },
];

export default function PrivacyPolicyPage() {
  return (
    <main className="legal-shell">
      <PolicyPageTracker policy="privacy_policy" policyVersion={PRIVACY_POLICY_VERSION} source="privacy_page" />

      <nav className="public-nav legal-nav" aria-label="Privacy navigation">
        <Link className="public-brand" href="/">
          <span className="brand-mark">FC</span>
          <span>
            <strong>FireCrow</strong>
            <small>by Nova Devs</small>
          </span>
        </Link>
        <div className="public-nav-links">
          <Link href="/">Home</Link>
          <PolicyLink href="/terms" policy="terms" source="privacy_nav">
            Terms of Use
          </PolicyLink>
          <Link className="nav-cta" href="/signin">Sign in</Link>
        </div>
      </nav>

      <section className="legal-hero">
        <div className="section-kicker">Privacy</div>
        <h1>Privacy Policy</h1>
        <p>
          This policy explains what FireCrow records, why it records it, and how the application preserves evidence of notice and consent.
        </p>
        <span>Version: {PRIVACY_POLICY_VERSION}</span>
      </section>

      <section className="legal-card">
        {PRIVACY_SECTIONS.map((section) => (
          <article className="legal-clause" key={section.title}>
            <h2>{section.title}</h2>
            <p>{section.body}</p>
          </article>
        ))}
      </section>

      <footer className="public-footer">
        <div>
          <strong>Nova Devs</strong>
          <p>FireCrow FCv1 security audit orchestration.</p>
        </div>
        <div className="footer-links">
          <Link href="/">Home</Link>
          <PolicyLink href="/terms" policy="terms" source="privacy_footer">
            Terms of Use
          </PolicyLink>
          <Link href="/signin">Sign in</Link>
          <a href="mailto:security@novadevs.dev">security@novadevs.dev</a>
        </div>
      </footer>
    </main>
  );
}

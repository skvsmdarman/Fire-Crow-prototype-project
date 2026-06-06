import Link from "next/link";

import PolicyLink from "../../components/PolicyLink";
import PolicyPageTracker from "../../components/PolicyPageTracker";
import { TERMS_VERSION } from "../../lib/policy";

const TERMS = [
  {
    title: "1. Service Scope",
    body: "FireCrow provides repository security audit orchestration, including repository intake, scanner execution, runtime validation workflows, report generation, and operational logging needed to show audit history and security events.",
  },
  {
    title: "2. Authorized Use Only",
    body: "You may only submit repositories, systems, applications, endpoints, or environments that you own or are explicitly authorized to test. You remain responsible for ensuring each audit request is lawful and contractually permitted.",
  },
  {
    title: "3. Security Testing Boundaries",
    body: "FireCrow is intended for controlled defensive security work. You must not use it to gain unauthorized access, exfiltrate data, overload services, or interfere with systems outside the scope of your authorization.",
  },
  {
    title: "4. Workspace Authentication",
    body: "Access to FireCrow depends on real workspace credentials or configured OAuth providers. You are responsible for protecting passwords, provider accounts, access tokens, and report artifacts associated with your workspace.",
  },
  {
    title: "5. Reports and Remediation Output",
    body: "Audit findings, evidence, remediation notes, and generated reports may contain sensitive security information. Review outputs carefully before sharing them outside the approved team or customer context.",
  },
  {
    title: "6. No Warranty of Complete Detection",
    body: "Security tooling can reduce risk but cannot guarantee detection of every vulnerability, misconfiguration, dependency issue, exploit path, or secret exposure. Findings should be reviewed by qualified personnel before remediation decisions are finalized.",
  },
  {
    title: "7. Service Changes",
    body: "Nova Devs may modify, suspend, replace, or improve FireCrow components, authentication flows, legal notices, integrations, reports, or agent behavior to improve reliability, security, and compliance.",
  },
  {
    title: "8. Liability Limits",
    body: "To the maximum extent permitted by law, Nova Devs is not liable for indirect, incidental, special, consequential, or punitive damages arising from use of FireCrow, including losses connected with data, revenue, business opportunity, or security posture.",
  },
  {
    title: "9. Contact and Grievance Channel",
    body: "Questions about these terms, privacy, security concerns, or workspace access can be sent to the designated Grievance Officer / operator contact at security@novadevs.dev. Production deployments should replace this with the real grievance officer name, postal address, and contact details used by the operator.",
  },
];

export default function TermsPage() {
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
        <div className="section-kicker">Legal</div>
        <h1>Terms of Use</h1>
        <p>
          These terms govern how FireCrow may be accessed and used for authorized security audit work.
        </p>
        <span>Version: {TERMS_VERSION}</span>
      </section>

      <section className="legal-card">
        {TERMS.map((term) => (
          <article className="legal-clause" key={term.title}>
            <h2>{term.title}</h2>
            <p>{term.body}</p>
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
          <PolicyLink href="/privacy-policy" policy="privacy_policy" source="terms_footer">
            Privacy Policy
          </PolicyLink>
          <Link href="/signin">Sign in</Link>
          <a href="mailto:security@novadevs.dev">security@novadevs.dev</a>
        </div>
      </footer>
    </main>
  );
}

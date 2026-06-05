import Link from "next/link";

const TERMS = [
  {
    title: "1. Service Scope",
    body: "FireCrow provides security audit orchestration for repositories and related runtime analysis workflows. The service may clone submitted repositories, execute scanners, generate findings, create reports, and retain operational logs required to show audit history.",
  },
  {
    title: "2. Authorized Use",
    body: "You may only submit repositories, applications, systems, or targets that you own or are explicitly authorized to test. You are responsible for ensuring that each audit request complies with applicable law, internal policy, and third-party platform rules.",
  },
  {
    title: "3. Security Testing Boundaries",
    body: "FireCrow is designed for controlled defensive security work. You must not use the platform to attack, disrupt, overload, exfiltrate from, or gain unauthorized access to systems outside the scope of your authorization.",
  },
  {
    title: "4. Workspace Sessions",
    body: "Workspace sessions identify the tenant context used to access audit jobs and reports. Keep access tokens and workstation sessions secure. Notify Nova Devs if you believe a workspace token or report artifact has been exposed.",
  },
  {
    title: "5. Data and Artifacts",
    body: "Audit inputs, findings, logs, cloned repository metadata, and generated reports may contain sensitive security information. You are responsible for reviewing outputs before sharing them and for protecting downloaded report artifacts.",
  },
  {
    title: "6. No Guarantee of Complete Coverage",
    body: "Security tooling can reduce risk but cannot guarantee that every vulnerability, misconfiguration, dependency issue, exploit path, or secret exposure will be detected. FireCrow findings should be reviewed by qualified personnel before remediation decisions are finalized.",
  },
  {
    title: "7. Availability and Changes",
    body: "Nova Devs may modify, suspend, or improve FireCrow components, agent behavior, reports, authentication flows, or integrations to improve reliability, security, or compliance.",
  },
  {
    title: "8. Limitation of Liability",
    body: "To the maximum extent permitted by law, Nova Devs is not liable for indirect, incidental, special, consequential, or punitive damages arising from use of FireCrow, including loss of data, revenue, profits, business opportunity, or security posture.",
  },
  {
    title: "9. Contact",
    body: "Questions about these terms, responsible disclosure, security concerns, or workspace access can be sent to security@novadevs.dev.",
  },
];

export default function TermsPage() {
  return (
    <main className="legal-shell">
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
          <Link className="nav-cta" href="/signin">Sign in</Link>
        </div>
      </nav>

      <section className="legal-hero">
        <div className="section-kicker">Legal</div>
        <h1>Terms and Conditions</h1>
        <p>
          These terms govern access to FireCrow FCv1, a security audit orchestration platform provided by Nova Devs.
        </p>
        <span>Effective date: June 5, 2026</span>
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
          <Link href="/signin">Sign in</Link>
          <a href="mailto:security@novadevs.dev">security@novadevs.dev</a>
        </div>
      </footer>
    </main>
  );
}

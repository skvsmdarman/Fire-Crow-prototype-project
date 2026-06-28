import { Card } from "../../components/ui/Card";
import { MarketingSection, SiteFooter, SiteHeader } from "../../components/SiteChrome";

const phases = [
  ["Intake", "Policy context, workspace authentication, attestation capture, and job queue handoff."],
  ["Execution", "Recon, API surface, secret history, dependency, IaC, CI/CD, authz, and sandbox-compatible branches."],
  ["Correlation", "Scoring, attack graph assembly, remediation planning, and report generation."],
];

export default function WorkflowPage() {
  return (
    <div className="fc-page">
      <SiteHeader ctaHref="/dashboard" ctaLabel="Go to Dashboard" />
      <main>
        <section className="fc-shell fc-hero">
          <Card className="fc-panel">
            <div className="fc-kicker">Workflow map</div>
            <h1 className="fc-title-xl" style={{ marginTop: 12 }}>
              From authorization to report retrieval.
            </h1>
            <p className="fc-copy" style={{ maxWidth: 760 }}>
              This frontend now mirrors the documented orchestration pipeline instead of marketing abstractions. The workspace flow is
              centered on authenticated intake, real pipeline telemetry, and evidence-backed artifact access.
            </p>
          </Card>
        </section>

        <MarketingSection
          kicker="Runtime"
          title="Three operator checkpoints"
          copy="The dashboard is optimized for the moments operators actually need: launching with authorization, monitoring live work, and inspecting the completed artifact set."
        >
          <div className="fc-grid-3">
            {phases.map(([title, copy]) => (
              <Card className="fc-panel" key={title}>
                <div className="fc-panel-title" style={{ fontSize: "1.2rem", marginBottom: 10 }}>
                  {title}
                </div>
                <div className="fc-copy">{copy}</div>
              </Card>
            ))}
          </div>
        </MarketingSection>
      </main>
      <SiteFooter />
    </div>
  );
}

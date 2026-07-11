import { Badge } from "../../components/ui/Badge";
import { Card } from "../../components/ui/Card";
import { MarketingSection, SiteFooter, SiteHeader } from "../../components/SiteChrome";

const agentRows = [
  ["Maestro", "Coordinates graph order, fan-out, fan-in, and cleanup fallback."],
  ["Recon + API Surface", "Maps repository shape and reachable service exposure."],
  ["Secret / Dependency / IaC", "Builds evidence from code history, dependencies, and infrastructure files."],
  ["Attack Graph / Reporter", "Correlates findings into graph-ready evidence and report artifacts."],
];

export default function AgentsPage() {
  return (
    <div className="fc-page">
      <SiteHeader ctaHref="/dashboard" ctaLabel="Inspect live agents" />
      <main>
        <section className="fc-shell fc-hero">
          <Card className="fc-panel">
            <div className="fc-kicker">Agent surfaces</div>
            <h1 className="fc-title-xl" style={{ marginTop: 12 }}>
              A calmer view of the scanning graph.
            </h1>
            <p className="fc-copy" style={{ maxWidth: 760 }}>
              Instead of overstating the system, this page frames the agent groups around the documented orchestration pipeline and the
              live system-status endpoint.
            </p>
          </Card>
        </section>

        <MarketingSection
          kicker="Groups"
          title="Operator-readable capabilities"
          copy="The dashboard reads these from live system status during authenticated use. This page simply explains what those groups mean."
        >
          <div className="fc-data-list">
            {agentRows.map(([title, copy]) => (
              <Card className="fc-panel" key={title}>
                <div className="fc-stack-between">
                  <div className="fc-panel-title" style={{ fontSize: "1.1rem" }}>
                    {title}
                  </div>
                  <Badge tone="info">Runtime-aware</Badge>
                </div>
                <div className="fc-copy" style={{ marginTop: 10 }}>
                  {copy}
                </div>
              </Card>
            ))}
          </div>
        </MarketingSection>
      </main>
      <SiteFooter />
    </div>
  );
}

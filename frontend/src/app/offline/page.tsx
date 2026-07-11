import Link from "next/link";
import { Card } from "../../components/ui/Card";

export default function OfflinePage() {
  return (
    <div className="fc-page">
      <main className="fc-shell" style={{ padding: "80px 0" }}>
        <Card className="fc-panel" style={{ maxWidth: 740, margin: "0 auto" }}>
          <div className="fc-kicker">Offline mode</div>
          <h1 className="fc-title-xl" style={{ marginTop: 12 }}>
            The app shell is cached. Private audit data is not.
          </h1>
          <p className="fc-copy">
            Fire Crow keeps the shell lightweight offline, but authenticated audit timelines, findings, reports, and graph data are not
            stored for offline access. Reconnect to resume the live console.
          </p>
          <div className="fc-chip-row" style={{ marginTop: 18 }}>
            <Link className="fc-button fc-button-primary" href="/signin">
              Return to sign in
            </Link>
            <Link className="fc-button fc-button-secondary" href="/">
              Back to landing page
            </Link>
          </div>
        </Card>
      </main>
    </div>
  );
}

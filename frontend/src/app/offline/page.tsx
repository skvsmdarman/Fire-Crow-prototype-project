import Link from "next/link";

export default function OfflinePage() {
  return (
    <main className="fc-offline-shell">
      <section className="fc-offline-card" aria-labelledby="offline-title">
        <div className="fc-offline-mark">FC</div>
        <p className="fc-offline-kicker">Secure connection required</p>
        <h1 id="offline-title">You are offline.</h1>
        <p>
          Fire Crow can show the app shell, but live audits require a secure connection.
          Private audit results, findings, reports, repository data, and authentication responses are never cached offline.
        </p>
        <Link href="/dashboard" className="fc-offline-action">
          Return to console
        </Link>
      </section>
    </main>
  );
}

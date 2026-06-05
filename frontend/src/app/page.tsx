"use client";

import Link from "next/link";
import { useEffect, useState, useRef, useCallback } from "react";

/* ─── data ─── */

const AGENTS = [
  { id: "MAESTRO", role: "Orchestration", desc: "Coordinates and schedules multi-agent pipeline runs end-to-end." },
  { id: "RECON", role: "Repository Intel", desc: "Clones targets, fingerprints tech stacks, maps dependency trees." },
  { id: "SAST", role: "Static Analysis", desc: "Scans source for hardcoded secrets, injection sinks, and misconfigurations." },
  { id: "SANDBOX", role: "Runtime Isolation", desc: "Provisions ephemeral Kali containers with memory caps and PID limits." },
  { id: "NETWORK", role: "Port Scanning", desc: "Discovers open services, maps exposed API surfaces and protocols." },
  { id: "ATTACK", role: "Active Validation", desc: "Runs safe injection payloads and boundary fuzzing against live endpoints." },
  { id: "EXPLOIT", role: "Proof Generation", desc: "Generates proof-of-concept evidence and reproduces confirmed weaknesses." },
  { id: "SCORING", role: "CVSS Prioritization", desc: "Assigns CVSS 3.1 vectors, deduplicates findings, and ranks by risk." },
  { id: "REPORTER", role: "Report Generation", desc: "Compiles executive PDF reports and submits remediation Pull Requests." },
];

const STATS = [
  { value: "9", label: "Autonomous agents" },
  { value: "< 5min", label: "Full audit cycle" },
  { value: "99.7%", label: "Detection accuracy" },
  { value: "0", label: "False positive tolerance" },
];

const PIPELINE_LABELS = ["RECON", "SAST", "SANDBOX", "NETWORK", "ATTACK", "EXPLOIT", "SCORING", "REPORTER"];

interface TerminalLine {
  text: string;
  type: "info" | "success" | "warning" | "error" | "prompt";
}

const INITIAL_LINES: TerminalLine[] = [
  { text: "FireCrow Security Orchestrator v1.0.0", type: "info" },
  { text: "All 9 agent nodes online. Awaiting target.", type: "success" },
  { text: "Enter a repository URL below and press Launch Audit to begin.", type: "prompt" },
];

const SIM_STEPS: { text: string; type: TerminalLine["type"]; delay: number }[] = [
  { text: "[RECON] Cloning target repository metadata…", type: "info", delay: 700 },
  { text: "[RECON] Discovered Python (FastAPI) backend & React frontend", type: "success", delay: 900 },
  { text: "[SAST] Running 47 static analysis signatures…", type: "info", delay: 1100 },
  { text: "[SAST] WARNING: Hardcoded database credentials found in config.py:L14", type: "warning", delay: 1000 },
  { text: "[SAST] WARNING: Potential SQL injection in routes/audit.py:L48", type: "warning", delay: 1100 },
  { text: "[SANDBOX] Spawning secure Kali execution context (cap_drop=ALL)…", type: "info", delay: 1400 },
  { text: "[NETWORK] Scanning external API endpoints on ports 80, 443, 8080…", type: "info", delay: 1200 },
  { text: "[ATTACK] Initiating safe validation injection payloads…", type: "info", delay: 1300 },
  { text: "[ATTACK] EXPLOIT CONFIRMED: Password constraint bypassed via raw SQL", type: "error", delay: 1500 },
  { text: "[SCORING] Final severity: CVSS 8.8 (HIGH)", type: "error", delay: 900 },
  { text: "[REPORTER] Generating executive PDF report…", type: "info", delay: 1100 },
  { text: "[REPORTER] Created branch 'fix/security-remediations' & submitted PR #4", type: "success", delay: 1300 },
  { text: "[SYSTEM] Audit completed. Review full trace inside dashboard.", type: "prompt", delay: 700 },
];

/* ─── component ─── */

export default function LandingPage() {
  /* terminal state */
  const [scanUrl, setScanUrl] = useState("github.com/nova-devs/vulnerable-app");
  const [scanning, setScanning] = useState(false);
  const [terminalLines, setTerminalLines] = useState<TerminalLine[]>(INITIAL_LINES);
  const [activePipelineIdx, setActivePipelineIdx] = useState(-1);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  /* newsletter */
  const [newsEmail, setNewsEmail] = useState("");
  const [newsSubscribed, setNewsSubscribed] = useState(false);

  /* intersection observer for scroll-triggered reveals */
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
          }
        });
      },
      { threshold: 0.12 },
    );
    document.querySelectorAll(".reveal-on-scroll").forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  /* terminal auto-scroll */
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [terminalLines]);

  /* audit simulator */
  const simulateAudit = useCallback(async () => {
    if (scanning) return;
    setScanning(true);
    setActivePipelineIdx(0);
    setTerminalLines([{ text: `[SYSTEM] Initializing audit for: ${scanUrl}`, type: "info" }]);

    for (let i = 0; i < SIM_STEPS.length; i++) {
      const step = SIM_STEPS[i];
      await new Promise((r) => setTimeout(r, step.delay));
      setTerminalLines((prev) => [...prev, { text: step.text, type: step.type }]);
      /* advance pipeline indicator when a new agent tag appears */
      const agentMatch = step.text.match(/^\[(\w+)]/);
      if (agentMatch) {
        const idx = PIPELINE_LABELS.indexOf(agentMatch[1]);
        if (idx >= 0) setActivePipelineIdx(idx);
      }
    }
    setActivePipelineIdx(PIPELINE_LABELS.length);
    setScanning(false);
  }, [scanning, scanUrl]);

  const handleNewsSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newsEmail.trim()) {
      setNewsSubscribed(true);
      setTimeout(() => { setNewsSubscribed(false); setNewsEmail(""); }, 5000);
    }
  };

  return (
    <main className="public-shell" style={{ position: "relative", overflow: "hidden" }}>
      {/* ambient blobs */}
      <div className="glowing-bg-blob" />
      <div className="glowing-bg-blob-2" />
      <div className="glowing-bg-blob-3" />

      {/* ── NAV ── */}
      <nav className="public-nav animate-fade-in" aria-label="Primary navigation" id="nav-primary">
        <Link className="public-brand" href="/">
          <span className="brand-mark">FC</span>
          <span>
            <strong>FireCrow</strong>
            <small>by Nova Devs</small>
          </span>
        </Link>
        <div className="public-nav-links">
          <a href="#platform">Platform</a>
          <a href="#agents">Agents</a>
          <a href="#sandbox">Live Demo</a>
          <Link href="/terms">Terms</Link>
          <Link className="nav-cta" href="/signin" id="nav-signin-cta">Open Console</Link>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="hero-section animate-fade-in delay-100" id="hero">
        <div className="hero-copy">
          <div className="section-kicker">AI-Powered Security Audit Platform</div>
          <h1>Ship code that<br /><span className="hero-gradient-text">attackers can&apos;t break.</span></h1>
          <p>
            FireCrow orchestrates 9 autonomous security agents to clone, analyze, sandbox, attack, score,
            and remediate vulnerabilities in your GitHub repositories — end to end, in under five minutes.
          </p>
          <div className="hero-actions">
            <Link className="primary-action public-action hero-primary-btn" href="/signin" id="hero-cta">
              Start Free Audit
              <svg className="hero-cta-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
            </Link>
            <a className="ghost-action public-action" href="#sandbox">Watch Demo</a>
          </div>

          {/* stats row */}
          <div className="hero-stats">
            {STATS.map((s) => (
              <div className="hero-stat" key={s.label}>
                <strong>{s.value}</strong>
                <span>{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* console preview */}
        <div className="hero-console animate-fade-in delay-200" aria-label="FireCrow pipeline preview" id="hero-pipeline-preview">
          <div className="hero-console-top">
            <span>MAESTRO PIPELINE</span>
            <strong style={{ color: "var(--green)" }}>● ACTIVE</strong>
          </div>
          <div className="hero-pipeline">
            {PIPELINE_LABELS.map((phase, index) => (
              <div className={`hero-pipeline-step${activePipelineIdx > index ? " hero-step-done" : ""}${activePipelineIdx === index ? " hero-step-active" : ""}`} key={phase}>
                <span>{String(index).padStart(2, "0")}</span>
                <strong>{phase}</strong>
                <div className="pipeline-indicator">
                  {activePipelineIdx > index && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>}
                  {activePipelineIdx === index && <span className="pipeline-pulse" />}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TRUSTED BY BANNER ── */}
      <section className="trusted-banner reveal-on-scroll" id="trusted-bar">
        <span className="trusted-label">TRUSTED BY SECURITY TEAMS AT</span>
        <div className="trusted-logos">
          {["Stripe", "Vercel", "Supabase", "Linear", "Resend"].map((name) => (
            <span className="trusted-logo" key={name}>{name}</span>
          ))}
        </div>
      </section>

      {/* ── PLATFORM PILLARS ── */}
      <section className="public-section reveal-on-scroll" id="platform">
        <div>
          <div className="section-kicker">Platform</div>
          <h2>Security infrastructure,<br />not security theater.</h2>
        </div>
        <div className="pillar-grid">
          {[
            { icon: "🔗", title: "Orchestrated audits", body: "FireCrow coordinates repository intake, static analysis, sandbox execution, network probing, attack simulation, scoring, reporting, and cleanup through one auditable workflow." },
            { icon: "📋", title: "Operational evidence", body: "Every audit keeps a live trace of agent activity, terminal status, findings, CVSS context, and report artifacts so teams can review what happened after the run." },
            { icon: "🛡️", title: "Local-first reliability", body: "The platform runs with lightweight local services for development while preserving the same API contracts used by the production orchestration path." },
            { icon: "⚡", title: "Automated remediation", body: "Generate fix branches, submit Pull Requests with inline code patches, and open GitHub Issues — all without leaving the console." },
            { icon: "📊", title: "Executive-ready reports", body: "Compiled PDF reports include CVSS scores, evidence screenshots, remediation guidance, and severity distribution charts for stakeholder review." },
            { icon: "🔒", title: "Zero-trust sandbox", body: "Every scan runs inside ephemeral containers with dropped capabilities, memory limits, and auto-delete timers to prevent lateral movement." },
          ].map((p) => (
            <article className="pillar-card" key={p.title}>
              <span className="pillar-icon">{p.icon}</span>
              <h3>{p.title}</h3>
              <p>{p.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ── AGENTS GRID ── */}
      <section className="public-section reveal-on-scroll" id="agents">
        <div>
          <div className="section-kicker">Agent Network</div>
          <h2>9 specialized agents.<br />One unified pipeline.</h2>
        </div>
        <div className="agents-showcase-grid">
          {AGENTS.map((agent, i) => (
            <div className="agent-showcase-card" key={agent.id} style={{ animationDelay: `${i * 60}ms` }}>
              <div className="agent-showcase-header">
                <span className="agent-idx">{String(i + 1).padStart(2, "0")}</span>
                <span className="agent-status-dot" />
              </div>
              <h3>{agent.id}</h3>
              <span className="agent-role">{agent.role}</span>
              <p>{agent.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── INTERACTIVE SANDBOX ── */}
      <section className="public-section reveal-on-scroll" id="sandbox" style={{ scrollMarginTop: "24px" }}>
        <div style={{ marginBottom: "24px" }}>
          <div className="section-kicker">Live Demo</div>
          <h2>Experience the orchestration pipeline.</h2>
          <p style={{ color: "var(--dim)", marginTop: "8px", maxWidth: "640px" }}>
            Watch FireCrow coordinate multi-stage static analysis, dynamic sandbox payloads, and automated
            pull request generation in real time.
          </p>
        </div>

        <div className="simulator-card">
          <div className="simulator-header">
            <div className="simulator-dots">
              <span className="simulator-dot red" />
              <span className="simulator-dot yellow" />
              <span className="simulator-dot green" />
            </div>
            <div className="simulator-title">security-agent@firecrow: ~/maestro-audit</div>
            <div style={{ width: 42 }} />
          </div>

          <div className="simulator-body" id="simulator-terminal">
            {terminalLines.map((line, idx) => (
              <div className="terminal-line" key={idx}>
                <span className="terminal-prompt">&gt;</span>
                <span className={`terminal-output terminal-${line.type}`}>{line.text}</span>
              </div>
            ))}
            <div ref={terminalEndRef} />
          </div>

          <div className="simulator-footer">
            <input
              type="text"
              className="simulator-input"
              value={scanUrl}
              onChange={(e) => setScanUrl(e.target.value)}
              placeholder="e.g. github.com/user/vulnerable-repo"
              disabled={scanning}
              id="simulator-url-input"
            />
            <button className="simulator-btn" onClick={simulateAudit} disabled={scanning} id="simulator-launch-btn">
              {scanning ? "Auditing…" : "Launch Audit"}
            </button>
          </div>
        </div>
      </section>

      {/* ── CTA BAND ── */}
      <section className="cta-band reveal-on-scroll" id="cta-final">
        <div className="cta-band-content">
          <div className="section-kicker">Get Started</div>
          <h2>Start securing your repositories today.</h2>
          <p>Create a workspace, connect your GitHub, and run your first audit in under two minutes.</p>
          <div className="hero-actions" style={{ marginTop: "16px" }}>
            <Link className="primary-action public-action hero-primary-btn" href="/signin">
              Open Console
              <svg className="hero-cta-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
            </Link>
            <Link className="ghost-action public-action" href="/terms">Review Terms</Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="footer-container animate-fade-in delay-400" id="site-footer">
        <div className="footer-brand-col">
          <Link className="public-brand" href="/">
            <span className="brand-mark">FC</span>
            <span>
              <strong>FireCrow</strong>
              <small>by Nova Devs</small>
            </span>
          </Link>
          <p>
            AI-powered repository security auditing. Vulnerability verification, sandbox automation, and secure code remediation — all from one console.
          </p>
          <div className="system-status-pill">
            <span className="status-dot" />
            ALL SYSTEMS OPERATIONAL
          </div>
        </div>

        <div className="footer-col">
          <h4>Platform</h4>
          <ul>
            <li><Link href="/signin">Access Console</Link></li>
            <li><a href="#platform">Audit Pipeline</a></li>
            <li><a href="#agents">Agent Network</a></li>
            <li><a href="#sandbox">Demo Sandbox</a></li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Resources</h4>
          <ul>
            <li><a href="#docs">API Documentation</a></li>
            <li><a href="#handbook">Security Handbook</a></li>
            <li><a href="#threats">Threat Database</a></li>
            <li><a href="#status">System Health</a></li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Stay Informed</h4>
          <p style={{ color: "var(--dim)", fontSize: 13, margin: "0 0 8px" }}>
            Subscribe to security advisories and release updates.
          </p>
          <form className="newsletter-form" onSubmit={handleNewsSubmit}>
            <input
              type="email"
              className="newsletter-input"
              placeholder="security@company.com"
              value={newsEmail}
              onChange={(e) => setNewsEmail(e.target.value)}
              required
              disabled={newsSubscribed}
              id="newsletter-email-input"
            />
            <button className="newsletter-btn" type="submit" disabled={newsSubscribed} id="newsletter-submit-btn">
              {newsSubscribed ? "✓" : "Join"}
            </button>
          </form>
          {newsSubscribed && (
            <span style={{ color: "var(--green)", fontSize: 12, marginTop: 6, display: "block" }}>
              Successfully registered!
            </span>
          )}
        </div>
      </footer>

      <div className="footer-bottom">
        <span>© {new Date().getFullYear()} Nova Devs. All rights reserved.</span>
        <div style={{ display: "flex", gap: 20 }}>
          <Link href="/terms">Terms of Service</Link>
          <Link href="/terms">Privacy Policy</Link>
          <a href="mailto:security@novadevs.dev">Responsible Disclosure</a>
        </div>
      </div>
    </main>
  );
}

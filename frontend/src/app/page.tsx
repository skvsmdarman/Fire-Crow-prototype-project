"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Cpu, RefreshCw, Layers, ArrowRight, Activity } from "lucide-react";

import PolicyLink from "../components/PolicyLink";
import styles from "./page.module.css";
import {
  fadeInUp,
  fadeInRight,
  fadeInLeft,
  staggerContainer,
  scaleUp
} from "../lib/animations";

const HERO_METRICS = [
  { value: "9", label: "Specialist agents", icon: Cpu },
  { value: "<5 min", label: "Audit loop", icon: RefreshCw },
  { value: "CVSS 3.1", label: "Risk scoring", icon: Shield },
  { value: "PR-ready", label: "Fix output", icon: Layers },
];

const CONTROL_BOARD = [
  { label: "Repository intake", hint: "Stack fingerprint and branch context", state: "Ready" },
  { label: "Static analysis", hint: "Secret leaks and sink discovery", state: "Watching" },
  { label: "Runtime validation", hint: "Sandboxed payload execution", state: "Contained" },
  { label: "Reporting", hint: "Evidence trail and remediation handoff", state: "Exporting" },
];

const FIRST_RUN_HINTS = [
  {
    title: "Start with a repo the team already knows",
    body: "A smaller service, staging branch, or recent hotfix usually makes the first audit feel grounded instead of abstract.",
  },
  {
    title: "Treat the first report like calibration",
    body: "The first pass should start a useful conversation. Teams almost always tighten scope after they see one real run.",
  },
  {
    title: "Pull one engineer into the first review",
    body: "Findings move faster when the person reading them can map the trace back to code they touched recently.",
  },
];

const CAPABILITIES = [
  {
    title: "Evidence before opinion",
    stat: "Live trace",
    body: "Every audit keeps the stream of agent actions, confirmed findings, and report artifacts so the team can review the why, not just the result.",
  },
  {
    title: "Safe runtime validation",
    stat: "Ephemeral sandbox",
    body: "Dynamic checks execute inside isolated Kali containers with dropped capabilities, bounded resources, and automatic teardown after each run.",
  },
  {
    title: "Remediation with momentum",
    stat: "Fix branch",
    body: "When issues are confirmed, FireCrow can package severity context, evidence, and patch guidance into a handoff your engineers can act on immediately.",
  },
  {
    title: "Designed for busy teams",
    stat: "One console",
    body: "Repository intake, findings, scorecards, and exports stay in one operational surface instead of living across disconnected scripts and spreadsheets.",
  },
];

const PIPELINE = [
  {
    id: "01",
    title: "Intake and stack mapping",
    body: "Clone the target, resolve dependencies, and understand the application shape before any validation begins.",
    output: "Stack map + branch context",
  },
  {
    id: "02",
    title: "Static pressure test",
    body: "Sweep the codebase for secrets, risky sinks, auth drift, and framework-specific patterns that deserve deeper validation.",
    output: "Candidate findings",
  },
  {
    id: "03",
    title: "Sandboxed runtime checks",
    body: "Replay safe payloads against the live surface inside a constrained environment to separate noise from confirmed weaknesses.",
    output: "Validated evidence",
  },
  {
    id: "04",
    title: "Risk and severity scoring",
    body: "Normalize duplicate findings, add CVSS context, and rank what needs engineering attention first.",
    output: "Prioritized queue",
  },
  {
    id: "05",
    title: "Executive-ready delivery",
    body: "Publish the final trace, issue summary, and remediation materials for operators, developers, and stakeholders.",
    output: "Report + handoff package",
  },
];

const AGENTS = [
  { id: "MAESTRO", role: "Orchestrates jobs, timing, and clean-up." },
  { id: "RECON", role: "Builds repository and dependency context." },
  { id: "SAST", role: "Flags secrets, sinks, and code risk." },
  { id: "SANDBOX", role: "Maintains isolated runtime execution." },
  { id: "NETWORK", role: "Maps ports, protocols, and exposure." },
  { id: "ATTACK", role: "Runs safe validation payloads." },
  { id: "EXPLOIT", role: "Generates reproducible evidence." },
  { id: "SCORING", role: "Ranks findings with CVSS context." },
  { id: "REPORTER", role: "Packages reports and remediation handoff." },
];

type TerminalTone = "info" | "success" | "warning" | "error";

interface TerminalLine {
  text: string;
  tone: TerminalTone;
}

const INITIAL_LINES: TerminalLine[] = [
  { text: "FireCrow orchestration room online.", tone: "success" },
  { text: "Agents standing by for repository intake.", tone: "info" },
  { text: "Launch a sample run to preview the audit flow.", tone: "warning" },
];

const SIMULATION_STEPS: Array<TerminalLine & { delay: number; phase: number }> = [
  { text: "[INTAKE] Cloning repository metadata and branch state...", tone: "info", delay: 550, phase: 0 },
  { text: "[RECON] FastAPI backend and Next.js frontend identified.", tone: "success", delay: 800, phase: 0 },
  { text: "[SAST] 47 signatures loaded for static pressure test.", tone: "info", delay: 950, phase: 1 },
  { text: "[SAST] Warning: database credentials appear hardcoded in config.", tone: "warning", delay: 950, phase: 1 },
  { text: "[SANDBOX] Ephemeral validation environment sealed and ready.", tone: "success", delay: 1100, phase: 2 },
  { text: "[ATTACK] Safe boundary payload confirms auth bypass path.", tone: "error", delay: 1150, phase: 2 },
  { text: "[SCORING] Severity normalized to CVSS 8.8 (HIGH).", tone: "warning", delay: 850, phase: 3 },
  { text: "[REPORTER] Evidence package and remediation brief generated.", tone: "success", delay: 900, phase: 4 },
];

const cx = (...tokens: Array<string | false | null | undefined>) => tokens.filter(Boolean).join(" ");

export default function LandingPage() {
  const [scanUrl, setScanUrl] = useState("github.com/nova-devs/vulnerable-app");
  const [scanning, setScanning] = useState(false);
  const [activePhase, setActivePhase] = useState(-1);
  const [terminalLines, setTerminalLines] = useState(INITIAL_LINES);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = localStorage.getItem("fc_token");
    const username = localStorage.getItem("fc_username");
    const userId = localStorage.getItem("fc_user_id");
    if (token && username && userId) {
      queueMicrotask(() => setIsLoggedIn(true));
    }
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      const totalScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (totalScroll > 0) {
        setScrollProgress(window.scrollY / totalScroll);
      }
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [terminalLines]);

  const runSimulation = async () => {
    if (scanning) {
      return;
    }

    setScanning(true);
    setActivePhase(0);
    setTerminalLines([{ text: `[SYSTEM] Preparing audit for ${scanUrl}`, tone: "info" }]);

    for (const step of SIMULATION_STEPS) {
      await new Promise((resolve) => window.setTimeout(resolve, step.delay));
      setTerminalLines((current) => [...current, { text: step.text, tone: step.tone }]);
      setActivePhase(step.phase);
    }

    setTerminalLines((current) => [
      ...current,
      { text: "[SYSTEM] Preview complete. Open the console to run the real pipeline.", tone: "success" },
    ]);
    setActivePhase(PIPELINE.length - 1);
    setScanning(false);
  };

  return (
    <main className={styles.page}>
      {/* Scroll Progress Indicator */}
      <motion.div
        className="scroll-progress-bar"
        style={{
          scaleX: scrollProgress,
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: "linear-gradient(90deg, #ff4d08, #ffbf47, #00e676)",
          transformOrigin: "0%",
          zIndex: 1000,
        }}
      />

      <div className={styles.backdrop} aria-hidden="true" />
      <div className={styles.noise} aria-hidden="true" />

      {/* Decorative Blob */}
      <div className="glowing-bg-blob-3" />

      <div className={styles.container}>
        <motion.nav
          variants={fadeInUp}
          initial="hidden"
          animate="visible"
          className={styles.nav}
          aria-label="Primary navigation"
        >
          <Link href="/" className={styles.brand}>
            <span className={styles.brandMark}>FC</span>
            <span className={styles.brandText}>
              <strong>FireCrow</strong>
              <small>Autonomous security audit</small>
            </span>
          </Link>

          <div className={styles.navLinks}>
            <a href="#capabilities" className={styles.navLink}>Platform</a>
            <a href="#live-demo" className={styles.navLink}>Live Demo</a>
            <a href="#agents" className={styles.navLink}>Agents</a>
            <PolicyLink href="/privacy-policy" policy="privacy_policy" source="landing_nav" className={styles.navLink}>
              Privacy
            </PolicyLink>
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }}>
              <Link href={isLoggedIn ? "/dashboard" : "/signin"} className={styles.navCta}>
                {isLoggedIn ? "Dashboard" : "Open Console"}
              </Link>
            </motion.div>
          </div>
        </motion.nav>

        <section className={styles.hero}>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className={styles.heroCopy}
          >
            <motion.p variants={fadeInUp} className={styles.eyebrow}>
              For the moment before “can someone sanity-check this?”
            </motion.p>
            <motion.h1 variants={fadeInUp} className={styles.heroTitle}>
              Catch the risky path,{" "}
              <span className="hero-gradient-text">keep the proof,</span>{" "}
              hand your team something useful.
            </motion.h1>
            <motion.p variants={fadeInUp} className={styles.heroBody}>
              FireCrow helps teams run a serious first pass on a repo without turning the process
              into screenshots, shell scripts, and a week of back-and-forth.
            </motion.p>

            <motion.div variants={fadeInUp} className={styles.heroActions}>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Link href={isLoggedIn ? "/dashboard" : "/signin"} className={cx(styles.primaryButton, "hero-primary-btn")}>
                  {isLoggedIn ? "Go to Dashboard" : "Start an audit"} <ArrowRight size={16} className="hero-cta-arrow" />
                </Link>
              </motion.div>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <a href="#live-demo" className={styles.secondaryButton}>See the live run</a>
              </motion.div>
            </motion.div>

            <motion.aside variants={fadeInUp} className={styles.heroNote}>
              <span className={styles.heroNoteLabel}>Good first run</span>
              <p>
                Start with a service your team already talks about by name. Familiar context makes the
                first audit feel a lot more trustworthy.
              </p>
            </motion.aside>

            <motion.div variants={fadeInUp} className={styles.heroFootnotes}>
              <span className={styles.heroFootnote}>Start with staging or a hotfix branch</span>
              <span className={styles.heroFootnote}>GitHub and workspace auth</span>
              <span className={styles.heroFootnote}>Reports people can actually read</span>
            </motion.div>

            <motion.div variants={staggerContainer} className={styles.heroMetrics}>
              {HERO_METRICS.map((metric) => {
                const IconComponent = metric.icon;
                return (
                  <motion.article
                    key={metric.label}
                    variants={scaleUp}
                    whileHover={{ scale: 1.02, borderColor: "rgba(255, 114, 0, 0.2)" }}
                    className={styles.metricCard}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                      <strong className={styles.metricValue}>{metric.value}</strong>
                      <IconComponent size={18} className="infoTone" style={{ opacity: 0.8 }} />
                    </div>
                    <span className={styles.metricLabel}>{metric.label}</span>
                  </motion.article>
                );
              })}
            </motion.div>
          </motion.div>

          <motion.aside
            variants={fadeInUp}
            initial="hidden"
            animate="visible"
            className={styles.heroBoard}
            aria-label="Operational preview"
          >
            <div className={styles.boardHeader}>
              <div>
                <p className={styles.boardLabel}>Control room preview</p>
                <h2 className={styles.boardTitle}>What the first audit actually gives you</h2>
              </div>
              <span className={styles.boardBadge}>All systems ready</span>
            </div>

            <motion.div variants={staggerContainer} className={styles.boardList}>
              {CONTROL_BOARD.map((row, index) => (
                <motion.article
                  key={row.label}
                  variants={fadeInUp}
                  whileHover={{ x: 4, background: "rgba(255, 255, 255, 0.05)" }}
                  className={styles.boardItem}
                >
                  <span className={styles.boardIndex}>{String(index + 1).padStart(2, "0")}</span>
                  <div className={styles.boardBody}>
                    <strong>{row.label}</strong>
                    <span>{row.hint}</span>
                  </div>
                  <span className={styles.boardState}>{row.state}</span>
                </motion.article>
              ))}
            </motion.div>

            <div className={styles.boardFooter}>
              <div>
                <span className={styles.boardFooterLabel}>Default output</span>
                <p className={styles.boardFooterValue}>Trace logs, finding evidence, CVSS ranking, and a remediation handoff package.</p>
              </div>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Link href={isLoggedIn ? "/dashboard" : "/signin"} className={styles.boardFooterLink}>
                  {isLoggedIn ? "Go to Dashboard" : "Launch workspace"}
                </Link>
              </motion.div>
            </div>
          </motion.aside>
        </section>

        {/* Capabilities Section */}
        <motion.section
          id="capabilities"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={staggerContainer}
          className={styles.section}
        >
          <motion.div variants={fadeInUp} className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Why it feels tighter</p>
              <h2 className={styles.sectionTitle}>Less dashboard theater. More useful context.</h2>
            </div>
            <p className={styles.sectionIntro}>
              The UI should explain itself in plain language, especially when someone from engineering opens it for the first time.
            </p>
          </motion.div>

          <div className={styles.capabilityGrid}>
            {CAPABILITIES.map((item) => (
              <motion.article
                key={item.title}
                variants={fadeInUp}
                whileHover={{ y: -4, borderColor: "rgba(255,114,0,0.2)", background: "rgba(255,255,255,0.03)" }}
                className={styles.capabilityCard}
              >
                <div className={styles.capabilityMeta}>
                  <span>{item.stat}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </motion.article>
            ))}
          </div>
        </motion.section>

        {/* Hints Section */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={staggerContainer}
          className={cx(styles.section, styles.hintsSection)}
        >
          <motion.div variants={fadeInUp} className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Helpful hints</p>
              <h2 className={styles.sectionTitle}>A few cues that make the first run land better.</h2>
            </div>
            <p className={styles.sectionIntro}>
              These are the little things a real teammate would tell you before asking you to trust a new security tool.
            </p>
          </motion.div>

          <div className={styles.hintGrid}>
            {FIRST_RUN_HINTS.map((hint) => (
              <motion.article
                key={hint.title}
                variants={fadeInUp}
                whileHover={{ y: -4, borderColor: "rgba(255,184,0,0.25)", background: "rgba(255,255,255,0.03)" }}
                className={styles.hintCard}
              >
                <span className={styles.hintMarker}>Note</span>
                <h3>{hint.title}</h3>
                <p>{hint.body}</p>
              </motion.article>
            ))}
          </div>
        </motion.section>

        {/* Live Demo Section */}
        <motion.section
          id="live-demo"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={staggerContainer}
          className={cx(styles.section, styles.demoSection)}
        >
          <motion.div variants={fadeInUp} className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Live walkthrough</p>
              <h2 className={styles.sectionTitle}>Preview the audit flow before you ever open the dashboard.</h2>
            </div>
            <p className={styles.sectionIntro}>
              A tighter marketing page should still prove the interaction model. This sample run shows how the pipeline moves from repo intake to report delivery.
            </p>
          </motion.div>

          <div className={styles.demoSplit}>
            <div className={styles.pipelinePanel}>
              {PIPELINE.map((step, index) => (
                <motion.article
                  key={step.id}
                  variants={fadeInLeft}
                  className={cx(
                    styles.pipelineCard,
                    activePhase === index && styles.pipelineCardActive,
                    activePhase > index && styles.pipelineCardDone,
                    "hero-pipeline-step",
                    activePhase === index && "hero-step-active",
                    activePhase > index && "hero-step-done"
                  )}
                  layout
                >
                  <div className={styles.pipelineHeader}>
                    <span>{step.id}</span>
                    <strong style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      {activePhase === index && (
                        <span className="pipeline-indicator">
                          <span className="pipeline-pulse" />
                        </span>
                      )}
                      {step.output}
                    </strong>
                  </div>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </motion.article>
              ))}
            </div>

            <motion.div variants={fadeInRight} className={styles.simulator}>
              <div className={styles.simulatorHeader}>
                <div className={styles.simulatorDots} aria-hidden="true">
                  <span className={styles.simulatorDotRed} />
                  <span className={styles.simulatorDotAmber} />
                  <span className={styles.simulatorDotGreen} />
                </div>
                <span className={styles.simulatorTitle}>firecrow@maestro / live-preview</span>
              </div>

              <div className={styles.simulatorBody}>
                <AnimatePresence mode="popLayout">
                  {terminalLines.map((line, index) => (
                    <motion.div
                      className={styles.terminalLine}
                      key={`${line.text}-${index}`}
                      initial={{ opacity: 0, y: 12, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      transition={{ duration: 0.25, ease: "easeOut" }}
                    >
                      <span className={styles.terminalPrompt}>&gt;</span>
                      <span
                        className={cx(
                          styles.terminalText,
                          line.tone === "info" && styles.infoTone,
                          line.tone === "success" && styles.successTone,
                          line.tone === "warning" && styles.warningTone,
                          line.tone === "error" && styles.errorTone,
                        )}
                      >
                        {line.text}
                      </span>
                    </motion.div>
                  ))}
                </AnimatePresence>
                <div ref={terminalEndRef} />
              </div>

              <div className={styles.simulatorFooter}>
                <input
                  type="text"
                  value={scanUrl}
                  onChange={(event) => setScanUrl(event.target.value)}
                  className={styles.urlInput}
                  placeholder="github.com/team/repository"
                  disabled={scanning}
                />
                <motion.button
                  whileHover={{ scale: scanning ? 1 : 1.02 }}
                  whileTap={{ scale: scanning ? 1 : 0.98 }}
                  type="button"
                  onClick={runSimulation}
                  className={styles.launchButton}
                  disabled={scanning}
                >
                  {scanning ? (
                    <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Activity size={16} className="auth-btn-spinner" />
                      Running preview...
                    </span>
                  ) : (
                    "Run preview"
                  )}
                </motion.button>
              </div>
            </motion.div>
          </div>
        </motion.section>

        {/* Agents Showcase Grid */}
        <motion.section
          id="agents"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={staggerContainer}
          className={styles.section}
        >
          <motion.div variants={fadeInUp} className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Agent network</p>
              <h2 className={styles.sectionTitle}>Each agent has one clear job.</h2>
            </div>
            <p className={styles.sectionIntro}>
              No mystery roles, no sci-fi flavor text. Just a readable pipeline with responsibilities your team can follow.
            </p>
          </motion.div>

          <div className="agents-showcase-grid">
            {AGENTS.map((agent, index) => (
              <motion.article
                key={agent.id}
                variants={fadeInUp}
                className="agent-showcase-card"
              >
                <div className="agent-showcase-header">
                  <span className="agent-idx">{String(index + 1).padStart(2, "0")}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span className="agent-status-dot" />
                    <span className="agent-idx">Online</span>
                  </div>
                </div>
                <h3>{agent.id}</h3>
                <span className="agent-role">{agent.role.split(",")[0]}</span>
                <p>{agent.role}</p>
              </motion.article>
            ))}
          </div>
        </motion.section>

        {/* CTA section */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={fadeInUp}
          className="cta-band"
        >
          <div className="cta-band-content">
            <p className={styles.eyebrow}>Next step</p>
            <h2>Run it on a repo your team already knows.</h2>
            <p>
              That first pass is where trust gets built. Keep the scope familiar, keep the language human, and the review moves faster.
            </p>
            <div className={styles.heroActions} style={{ marginTop: 24 }}>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Link href={isLoggedIn ? "/dashboard" : "/signin"} className={styles.primaryButton}>
                  {isLoggedIn ? "Go to Dashboard" : "Go to sign in"}
                </Link>
              </motion.div>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <PolicyLink href="/privacy-policy" policy="privacy_policy" source="landing_cta" className={styles.secondaryButton}>
                  Review privacy policy
                </PolicyLink>
              </motion.div>
            </div>
          </div>
        </motion.section>

        <footer className={styles.footer}>
          <div className={styles.footerBrand}>
            <Link href="/" className={styles.brand}>
              <span className={styles.brandMark}>FC</span>
              <span className={styles.brandText}>
                <strong>FireCrow</strong>
                <small>Autonomous security audit</small>
              </span>
            </Link>
            <p>
              Repository intake, runtime validation, CVSS scoring, and remediation handoff in a single security workflow.
            </p>
          </div>

          <div className={styles.footerLinks}>
            <a href="#capabilities">Platform</a>
            <a href="#live-demo">Live demo</a>
            <a href="#agents">Agents</a>
            <Link href={isLoggedIn ? "/dashboard" : "/signin"}>{isLoggedIn ? "Dashboard" : "Sign in"}</Link>
            <PolicyLink href="/terms" policy="terms" source="landing_footer">Terms</PolicyLink>
            <PolicyLink href="/privacy-policy" policy="privacy_policy" source="landing_footer">
              Privacy
            </PolicyLink>
          </div>
        </footer>
      </div>
    </main>
  );
}


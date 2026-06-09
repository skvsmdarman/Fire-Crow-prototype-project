"use client";

import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Cpu, Layers, RefreshCw, Shield } from "lucide-react";

import PolicyLink from "../components/PolicyLink";
import Footer from "../components/Footer";
import BrandLogo from "../components/BrandLogo";
import { fadeInLeft, fadeInRight, fadeInUp, scaleUp, staggerContainer } from "../lib/animations";
import {
  getServerAuthSessionSnapshot,
  getStoredAuthSessionSnapshot,
  subscribeToAuthSession
} from "../lib/authSession";
import styles from "./page.module.css";

const HERO_METRICS = [
  { value: "Owned", label: "Authorized repositories", icon: Shield },
  { value: "Scoped", label: "Defensive review", icon: RefreshCw },
  { value: "Evidence", label: "Finding context", icon: Cpu },
  { value: "Reports", label: "Founder-ready handoff", icon: Layers },
];

const TRUST_CARDS = [
  { label: "Sandbox-first", hint: "Runtime checks stay bounded by the backend sandbox configuration.", state: "Controlled" },
  { label: "Authorization-only", hint: "Start audits only for systems you own or are explicitly allowed to test.", state: "Required" },
  { label: "Evidence-backed", hint: "Findings stay attached to supporting context instead of floating as vague alerts.", state: "Traceable" },
  { label: "Remediation-focused", hint: "The output points teams toward impact, priority, and fix direction.", state: "Actionable" },
];

const ONBOARDING_STRATEGY = [
  { title: "Select a familiar target service", body: "Auditing a smaller microservice or a staging branch first makes findings simpler to analyze and verify." },
  { title: "Establish an operational baseline", body: "The initial audit establishes baseline metrics. Use findings to refine configuration and scope in subsequent runs." },
  { title: "Involve engineering stakeholders early", body: "Integrate engineering leads during the first report review to map security traces directly to active codebases." },
];

const CAPABILITIES = [
  { title: "Evidence before opinion", stat: "Traceable", body: "Every audit keeps agent notes, confirmed findings, and report artifacts in one review surface." },
  { title: "Safe runtime validation", stat: "Bounded", body: "Dynamic checks follow the configured sandbox and remain authorization-first and remediation-oriented." },
  { title: "Remediation with momentum", stat: "Actionable", body: "Confirmed issues include severity context, evidence, and fix guidance that engineers can act on." },
  { title: "Designed for busy teams", stat: "One console", body: "Repository intake, findings, scorecards, and exports stay in one operational surface." },
];

const PIPELINE = [
  { id: "01", title: "Intake and authorization check", body: "Connect a repository through the protected console and confirm the review boundary before starting.", output: "Target + branch context" },
  { id: "02", title: "Static code review", body: "Review dependency risk, secret/config exposure, auth/session patterns, and framework-specific code risk.", output: "Candidate findings" },
  { id: "03", title: "Sandbox-controlled validation", body: "Use the backend-configured sandbox path when supported to reduce noise without expanding the safety boundary.", output: "Evidence notes" },
  { id: "04", title: "Risk and severity scoring", body: "Prioritize confirmed findings with readable severity labels, confidence, and business impact.", output: "Prioritized queue" },
  { id: "05", title: "Executive-ready delivery", body: "Generate remediation-focused reports for founders, operators, and engineering stakeholders.", output: "Report handoff" },
];

const AGENTS = [
  { id: "MAESTRO", role: "Coordinates audit jobs, status, and cleanup." },
  { id: "RECON", role: "Builds repository and dependency context." },
  { id: "SAST", role: "Flags secrets, sinks, and code-level risk." },
  { id: "SANDBOX", role: "Maintains isolated validation boundaries." },
  { id: "AUTH", role: "Reviews authentication and session behavior." },
  { id: "API", role: "Reviews API security and configuration exposure." },
  { id: "SCORING", role: "Ranks findings with severity context." },
  { id: "REPORTER", role: "Packages reports and remediation handoff." },
];

const CONSOLE_LINES = [
  { text: "[BOUNDARY] Only audit systems you own or are authorized to test.", tone: "warning" },
  { text: "[INTAKE] Open the protected console to connect a real repository.", tone: "info" },
  { text: "[OUTPUT] Review evidence-backed findings and remediation guidance.", tone: "success" },
];

type TerminalTone = "info" | "success" | "warning" | "error";
interface TerminalLine { text: string; tone: TerminalTone }

const cx = (...tokens: Array<string | false | null | undefined>) => tokens.filter(Boolean).join(" ");

export default function LandingPage() {
  const [scrollProgress, setScrollProgress] = useState(0);
  const session = useSyncExternalStore(
    subscribeToAuthSession,
    getStoredAuthSessionSnapshot,
    getServerAuthSessionSnapshot
  );
  const isLoggedIn = session.hasDashboardSession;

  useEffect(() => {
    const handleScroll = () => {
      const totalScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (totalScroll > 0) setScrollProgress(window.scrollY / totalScroll);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const consoleLines = CONSOLE_LINES as TerminalLine[];

  return (
    <main className={styles.page}>
      <motion.div className="scroll-progress-bar" style={{ scaleX: scrollProgress, position: "fixed", top: 0, left: 0, right: 0, height: 3, background: "linear-gradient(90deg, var(--fire), var(--orange), var(--purple), var(--blue))", transformOrigin: "0%", zIndex: 1000 }} />
      <div className={styles.backdrop} aria-hidden="true" />
      <div className={styles.noise} aria-hidden="true" />
      <div className="glowing-bg-blob-3" aria-hidden="true" />

      <div className={styles.container}>
        <motion.nav variants={fadeInUp} initial="hidden" animate="visible" className={styles.nav} aria-label="Primary navigation">
          <BrandLogo />
          <div className={styles.navLinks}>
            <a href="#capabilities" className={styles.navLink}>Platform</a>
            <a href="#workflow" className={styles.navLink}>Workflow</a>
            <a href="#agents" className={styles.navLink}>Agents</a>
            <PolicyLink href="/privacy-policy" policy="privacy_policy" source="landing_nav" className={styles.navLink}>Privacy</PolicyLink>
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }}><Link href={isLoggedIn ? "/dashboard" : "/signin"} className={styles.navCta}>{isLoggedIn ? "Dashboard" : "Open Console"}</Link></motion.div>
          </div>
        </motion.nav>

        <section className={styles.hero}>
          <motion.div variants={staggerContainer} initial="hidden" animate="visible" className={styles.heroCopy}>
            <motion.p variants={fadeInUp} className={styles.eyebrow}>Fire Crow</motion.p>
            <motion.h1 variants={fadeInUp} className={styles.heroTitle}>Agentic security audits for <span className="hero-gradient-text">modern SaaS teams.</span></motion.h1>
            <motion.p variants={fadeInUp} className={styles.heroBody}>Run authorization-only audits, review evidence-backed findings, and generate founder-ready security reports.</motion.p>
            <motion.div variants={fadeInUp} className={styles.heroActions}>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}><Link href={isLoggedIn ? "/dashboard" : "/signin"} className={cx(styles.primaryButton, "hero-primary-btn")}>Start Audit <ArrowRight size={16} className="hero-cta-arrow" /></Link></motion.div>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}><Link href="/dashboard" className={styles.secondaryButton}>View Reports</Link></motion.div>
            </motion.div>
            <motion.aside variants={fadeInUp} className={styles.heroNote}><span className={styles.heroNoteLabel}>Safety note</span><p>Only audit systems you own or are authorized to test.</p></motion.aside>
            <motion.div variants={fadeInUp} className={styles.heroFootnotes}><span className={styles.heroFootnote}>Sandbox-first</span><span className={styles.heroFootnote}>Authorization-only</span><span className={styles.heroFootnote}>Evidence-backed</span><span className={styles.heroFootnote}>Remediation-focused</span></motion.div>
            <motion.div variants={staggerContainer} className={styles.heroMetrics}>{HERO_METRICS.map((metric) => { const IconComponent = metric.icon; return <motion.article key={metric.label} variants={scaleUp} whileHover={{ scale: 1.02, borderColor: "rgba(255, 114, 0, 0.2)" }} className={styles.metricCard}><div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}><strong className={styles.metricValue}>{metric.value}</strong><IconComponent size={18} className="infoTone" style={{ opacity: 0.8 }} /></div><span className={styles.metricLabel}>{metric.label}</span></motion.article>; })}</motion.div>
          </motion.div>

          <motion.aside variants={fadeInUp} initial="hidden" animate="visible" className={styles.heroBoard} aria-label="Trust model preview">
            <div className={styles.boardHeader}><div><p className={styles.boardLabel}>Trust model</p><h2 className={styles.boardTitle}>Built for defensive review workflows</h2></div><span className={styles.boardBadge}>Consent-based</span></div>
            <motion.div variants={staggerContainer} className={styles.boardList}>{TRUST_CARDS.map((row, index) => <motion.article key={row.label} variants={fadeInUp} whileHover={{ x: 4, background: "rgba(255, 255, 255, 0.05)" }} className={styles.boardItem}><span className={styles.boardIndex}>{String(index + 1).padStart(2, "0")}</span><div className={styles.boardBody}><strong>{row.label}</strong><span>{row.hint}</span></div><span className={styles.boardState}>{row.state}</span></motion.article>)}</motion.div>
            <div className={styles.boardFooter}><div><span className={styles.boardFooterLabel}>Default output</span><p className={styles.boardFooterValue}>Trace logs, finding evidence, severity ranking, and a remediation handoff package.</p></div><motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}><Link href={isLoggedIn ? "/dashboard" : "/signin"} className={styles.boardFooterLink}>{isLoggedIn ? "Go to Dashboard" : "Launch workspace"}</Link></motion.div></div>
          </motion.aside>
        </section>

        <motion.section id="capabilities" initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={staggerContainer} className={styles.section}>
          <motion.div variants={fadeInUp} className={styles.sectionHeader}><div><p className={styles.eyebrow}>Platform Posture</p><h2 className={styles.sectionTitle}>Executive security context with actionable insights.</h2></div><p className={styles.sectionIntro}>Our platform reports provide deep visibility into vulnerability boundaries, detailed evidence, and clear remediation guidance.</p></motion.div>
          <div className={styles.capabilityGrid}>{CAPABILITIES.map((item) => <motion.article key={item.title} variants={fadeInUp} whileHover={{ y: -4, borderColor: "rgba(255,114,0,0.2)", background: "rgba(255,255,255,0.03)" }} className={styles.capabilityCard}><div className={styles.capabilityMeta}><span>{item.stat}</span></div><h3>{item.title}</h3><p>{item.body}</p></motion.article>)}</div>
        </motion.section>

        <motion.section initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={staggerContainer} className={cx(styles.section, styles.hintsSection)}>
          <motion.div variants={fadeInUp} className={styles.sectionHeader}><div><p className={styles.eyebrow}>Onboarding</p><h2 className={styles.sectionTitle}>Best practices for your first security audit.</h2></div><p className={styles.sectionIntro}>Optimize initial baseline reviews by defining scope, targeting familiar components, and coordinating reviews.</p></motion.div>
          <div className={styles.hintGrid}>{ONBOARDING_STRATEGY.map((strategy) => <motion.article key={strategy.title} variants={fadeInUp} whileHover={{ y: -4, borderColor: "rgba(255,184,0,0.25)", background: "rgba(255,255,255,0.03)" }} className={styles.hintCard}><span className={styles.hintMarker}>Guideline</span><h3>{strategy.title}</h3><p>{strategy.body}</p></motion.article>)}</div>
        </motion.section>

        <motion.section id="workflow" initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={staggerContainer} className={cx(styles.section, styles.demoSection)}>
          <motion.div variants={fadeInUp} className={styles.sectionHeader}><div><p className={styles.eyebrow}>Workflow</p><h2 className={styles.sectionTitle}>From authorized intake to remediation report.</h2></div><p className={styles.sectionIntro}>Secure audits run within a sandbox environment. Connect your repository in the console to initiate scanning.</p></motion.div>
          <div className={styles.demoSplit}>
            <div className={styles.pipelinePanel}>{PIPELINE.map((step) => <motion.article key={step.id} variants={fadeInLeft} className={cx(styles.pipelineCard, "hero-pipeline-step")} layout><div className={styles.pipelineHeader}><span>{step.id}</span><strong style={{ display: "flex", alignItems: "center", gap: 6 }}>{step.output}</strong></div><h3>{step.title}</h3><p>{step.body}</p></motion.article>)}</div>
            <motion.div variants={fadeInRight} className={styles.simulator}><div className={styles.simulatorHeader}><div className={styles.simulatorDots} aria-hidden="true"><span className={styles.simulatorDotRed} /><span className={styles.simulatorDotAmber} /><span className={styles.simulatorDotGreen} /></div><span className={styles.simulatorTitle}>firecrow@maestro / safety-brief</span></div><div className={styles.simulatorBody}>{consoleLines.map((line, index) => <motion.div className={styles.terminalLine} key={`${line.text}-${index}`} initial={{ opacity: 0, y: 12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.25, ease: "easeOut" }}><span className={styles.terminalPrompt}>&gt;</span><span className={cx(styles.terminalText, line.tone === "info" && styles.infoTone, line.tone === "success" && styles.successTone, line.tone === "warning" && styles.warningTone, line.tone === "error" && styles.errorTone)}>{line.text}</span></motion.div>)}</div><div className={styles.simulatorFooter}><Link href={isLoggedIn ? "/dashboard" : "/signin"} className={styles.launchButton}>Start an authorized audit</Link></div></motion.div>
          </div>
        </motion.section>

        <motion.section id="agents" initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={staggerContainer} className={styles.section}>
          <motion.div variants={fadeInUp} className={styles.sectionHeader}><div><p className={styles.eyebrow}>Agent network</p><h2 className={styles.sectionTitle}>Each role has one clear job.</h2></div><p className={styles.sectionIntro}>Readable responsibilities keep the security workflow understandable for founders, operators, and engineers.</p></motion.div>
          <div className="agents-showcase-grid">{AGENTS.map((agent, index) => <motion.article key={agent.id} variants={fadeInUp} className="agent-showcase-card"><div className="agent-showcase-header"><span className="agent-idx">{String(index + 1).padStart(2, "0")}</span><div style={{ display: "flex", alignItems: "center", gap: 6 }}><span className="agent-status-dot" /><span className="agent-idx">Ready</span></div></div><h3>{agent.id}</h3><span className="agent-role">{agent.role.split(",")[0]}</span><p>{agent.role}</p></motion.article>)}</div>
        </motion.section>

        <motion.section initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={fadeInUp} className="cta-band"><div className="cta-band-content"><p className={styles.eyebrow}>Next step</p><h2>Deploy continuous security intelligence today.</h2><p>Establish baseline safety configurations, evaluate package vulnerabilities, and implement validated security controls.</p><div className={styles.heroActions} style={{ marginTop: 24 }}><motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}><Link href={isLoggedIn ? "/dashboard" : "/signin"} className={styles.primaryButton}>{isLoggedIn ? "Go to Dashboard" : "Go to sign in"}</Link></motion.div><motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}><PolicyLink href="/privacy-policy" policy="privacy_policy" source="landing_cta" className={styles.secondaryButton}>Review privacy policy</PolicyLink></motion.div></div></div></motion.section>

        <Footer />
      </div>
    </main>
  );
}

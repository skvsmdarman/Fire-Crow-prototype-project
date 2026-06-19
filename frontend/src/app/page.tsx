"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  getServerAuthSessionSnapshot,
  getStoredAuthSessionSnapshot,
  subscribeToAuthSession,
} from "../lib/authSession";
import { COMPANY_NAME, PRODUCT_VERSION, COPYRIGHT_YEAR, PRODUCT_TAGLINE } from "../shared/config/app";

const theme = {
  bg: "var(--bg)",
  surface: "var(--surface)",
  border: "var(--border)",
  borderHover: "var(--borderHover)",
  text: "var(--text)",
  muted: "var(--muted)",
  dim: "var(--dim)",
  orange: "var(--orange)",
  orangeDim: "var(--orangeDim)",
  orangeBorder: "var(--orangeBorder)",
  green: "var(--green)",
  red: "var(--red)",
  blue: "var(--blue)",
  amber: "var(--amber)",
};

function Logo({ centered }: { centered?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: centered ? "center" : "flex-start" }}>
      <div style={{ width: 30, height: 30, borderRadius: 8, background: `linear-gradient(135deg, ${theme.orange}, #ffb347)`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#160800", fontFamily: "'IBM Plex Mono', monospace" }}>FC</span>
      </div>
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.01em" }}>Fire Crow</div>
        <div className="mono" style={{ fontSize: 9, color: theme.muted, letterSpacing: "0.12em", textTransform: "uppercase" }}>FCv1 security audit</div>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const router = useRouter();
  const session = useSyncExternalStore(
    subscribeToAuthSession,
    getStoredAuthSessionSnapshot,
    getServerAuthSessionSnapshot
  );
  const isLoggedIn = session.hasDashboardSession;

  const [url, setUrl] = useState("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setTick((p) => p + 1), 2000);
    return () => clearInterval(t);
  }, []);

  const handleEnter = () => {
    if (isLoggedIn) {
      router.push("/dashboard");
    } else {
      router.push("/signin");
    }
  };

  const termLines = [
    { txt: "→ cloning acme/backend-api@main", tone: theme.muted },
    { txt: "✓ SAST scan complete — 47 patterns checked", tone: theme.green },
    { txt: "! hardcoded secret detected at config.py:16", tone: theme.red },
    { txt: "→ running dependency audit (osv-scanner)", tone: theme.muted },
    { txt: "! CVE-2021-23337 lodash@4.17.15", tone: theme.amber },
    { txt: "✓ CVSS scoring complete — max 9.8", tone: theme.green },
    { txt: "→ generating report", tone: theme.muted },
  ];
  const visible = termLines.slice(0, Math.min(tick + 1, termLines.length));

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Nav */}
      <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 40px", borderBottom: `1px solid ${theme.border}` }}>
        <Logo />
        <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
          {["Platform", "Workflow", "Agents"].map((l) => (
            <span key={l} style={{ color: theme.muted, fontSize: 13, fontWeight: 400, cursor: "pointer", transition: "color .2s" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = theme.text)}
              onMouseLeave={(e) => (e.currentTarget.style.color = theme.muted)}>{l}</span>
          ))}
          <button onClick={handleEnter} style={{ padding: "7px 16px", border: `1px solid ${theme.orangeBorder}`, borderRadius: 6, background: theme.orangeDim, color: theme.orange, fontSize: 13, fontWeight: 500 }}>
            {isLoggedIn ? "Dashboard" : "Sign in"}
          </button>
        </div>
      </nav>

      {/* Hero */}
      <div style={{ flex: 1, maxWidth: 1100, margin: "0 auto", width: "100%", padding: "80px 40px 60px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 60, alignItems: "start" }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <p className="mono" style={{ fontSize: 11, letterSpacing: "0.2em", color: theme.orange, textTransform: "uppercase", marginBottom: 20 }}>Fire Crow · FCv1</p>
          <h1 style={{ fontSize: "clamp(38px, 5vw, 58px)", fontWeight: 300, lineHeight: 1.1, letterSpacing: "-0.03em", marginBottom: 20 }}>
            Security audits<br />
            <span style={{ color: theme.muted }}>that don&apos;t guess.</span>
          </h1>
          <p style={{ fontSize: 15, color: theme.muted, lineHeight: 1.7, maxWidth: 420, marginBottom: 36 }}>
            Authorization-only agentic scans with evidence-backed findings. Connect a repository and receive a remediation-ready report in minutes.
          </p>

          {/* Intake strip */}
          <div style={{ border: `1px solid ${theme.border}`, borderRadius: 8, overflow: "hidden", marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/your-org/repository"
                style={{ flex: 1, background: "transparent", border: "none", outline: "none", padding: "13px 16px", fontSize: 13, color: theme.text }}
              />
              <button onClick={handleEnter} style={{ padding: "13px 20px", background: theme.orange, color: "#160800", fontSize: 13, fontWeight: 600, borderLeft: `1px solid ${theme.border}`, flexShrink: 0, letterSpacing: "0.02em" }}>
                Audit →
              </button>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {["Authorization-only", "Evidence-backed", "Sandbox-first", "Remediation-focused"].map((t) => (
              <span key={t} className="mono" style={{ fontSize: 10, letterSpacing: "0.08em", color: theme.muted, border: `1px solid ${theme.border}`, padding: "4px 10px", borderRadius: 4 }}>{t}</span>
            ))}
          </div>
        </motion.div>

        {/* Terminal preview */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.15 }}>
          <div style={{ border: `1px solid ${theme.border}`, borderRadius: 8, overflow: "hidden", background: theme.surface }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderBottom: `1px solid ${theme.border}`, background: theme.bg }}>
              <div style={{ display: "flex", gap: 6 }}>
                {["#ff5f57", "#febc2e", "#28c840"].map((c) => <span key={c} style={{ width: 9, height: 9, borderRadius: "50%", background: c }} />)}
              </div>
              <span className="mono" style={{ fontSize: 10, color: theme.muted }}>firecrow · scan output</span>
            </div>
            <div style={{ padding: "18px 16px", minHeight: 200, fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, lineHeight: 1.8 }}>
              {visible.map((l, i) => (
                <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ color: l.tone }}>{l.txt}</motion.div>
              ))}
              {visible.length < termLines.length && <span style={{ color: theme.muted }}>_</span>}
            </div>
          </div>

          {/* Stat row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginTop: 12 }}>
            {[["14", "Agents"], ["CVSS 3.1", "Scoring"], ["PDF", "Reports"]].map(([v, l]) => (
              <div key={l} style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 6, padding: "14px 16px" }}>
                <div style={{ fontSize: 20, fontWeight: 500, fontFamily: "'IBM Plex Mono', monospace", color: theme.text }}>{v}</div>
                <div style={{ fontSize: 11, color: theme.muted, marginTop: 4 }}>{l}</div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <div style={{ borderTop: `1px solid ${theme.border}`, padding: "20px 40px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 12, color: theme.muted }}>© {COPYRIGHT_YEAR} {COMPANY_NAME} · Fire Crow {PRODUCT_VERSION}</span>
        <div style={{ display: "flex", gap: 24 }}>
          {["Privacy", "Terms"].map((l) => (
            <Link key={l} href={`/${l.toLowerCase().replace(" ", "-")}`} style={{ fontSize: 12, color: theme.muted, cursor: "pointer" }}>{l}</Link>
          ))}
        </div>
      </div>
    </div>
  );
}

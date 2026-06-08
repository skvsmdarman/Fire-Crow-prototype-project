"use client";

import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import { useAuthSession } from "../../shared/hooks/useAuthSession";
import { useSSE, LogLine } from "../../shared/hooks/useSSE";
import useAudits from "../../features/audits/hooks";
import { fetchSystemStatus as apiFetchSystemStatus } from "../../features/audits/api";
import { Job, JobDetail, Finding, SystemStatus } from "../../features/audits/types";
import { formatDateTime, shortRepoName } from "../../shared/utils/format";
import { API_BASE_URL } from "../../shared/api/client";
import { ENDPOINTS } from "../../shared/api/endpoints";

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

const STATUS_COLORS: Record<string, string> = {
  completed: theme.green,
  running: theme.blue,
  failed: theme.red,
  cancelled: theme.amber,
  queued: theme.muted,
  partial: theme.amber,
  cancelling: theme.amber,
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: theme.red,
  high: theme.orange,
  medium: theme.amber,
  low: theme.blue,
  info: theme.muted,
};

function StatusPill({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || theme.muted;
  return (
    <span className="mono" style={{ fontSize: 10, fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase", color, border: `1px solid ${color}20`, padding: "3px 8px", borderRadius: 4 }}>
      {status === "running" && <span style={{ display: "inline-block", width: 5, height: 5, borderRadius: "50%", background: theme.blue, marginRight: 5, animation: "pulse 1.6s ease-in-out infinite", verticalAlign: "middle" }} />}
      {status}
    </span>
  );
}

function SeverityPill({ severity }: { severity: string }) {
  const color = SEVERITY_COLORS[severity] || theme.muted;
  return (
    <span className="mono" style={{ fontSize: 10, fontWeight: 500, letterSpacing: "0.06em", textTransform: "uppercase", color, border: `1px solid ${color}25`, padding: "3px 8px", borderRadius: 4, flexShrink: 0 }}>
      {severity}
    </span>
  );
}

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

function SectionIcon({ name, active }: { name: string; active: boolean }) {
  const color = active ? theme.orange : theme.muted;
  const icons: Record<string, React.ReactNode> = {
    Overview: <path d="M4 5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5zm10 0a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1V5zM4 14a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-5zm10-2a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-7z" />,
    Audits: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
    Findings: <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4m0 4h.01" />,
    Reports: <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8m8 4H8m2-8H8" />,
    Settings: <><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></>,
  };
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      {icons[name]}
    </svg>
  );
}

const SECTIONS = ["Overview", "Audits", "Findings", "Reports", "Settings"];

export default function Dashboard() {
  const router = useRouter();
  const authSession = useAuthSession();
  const isAuthenticated = authSession.hasDashboardSession;

  const [active, setActive] = useState("Overview");
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [newAuditUrl, setNewAuditUrl] = useState("");
  const [newAuditBranch, setNewAuditBranch] = useState("main");

  const {
    jobs,
    selectedJobId,
    setSelectedJobId,
    selectedJobDetail,
    runAudit,
    loadJobs,
    loadJobDetail,
  } = useAudits(authSession.token);

  const selectedJob = jobs.find(j => j.id === selectedJobId) || null;
  const findings = selectedJobDetail?.findings || [];

  const { logs, streamActive, startLogStream, stopLogStream } = useSSE({
    authenticated: isAuthenticated,
    token: authSession.token,
    onJobStatusChange: () => {
      void loadJobs();
      if (selectedJobId) void loadJobDetail(selectedJobId);
    },
  });

  const fetchSystemStatus = useCallback(() => {
    if (!isAuthenticated) return;
    apiFetchSystemStatus().then(setSystemStatus).catch(console.error);
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/signin");
      return;
    }
    fetchSystemStatus();
  }, [isAuthenticated, fetchSystemStatus, router]);

  useEffect(() => {
    if (selectedJob?.id) {
      if (selectedJob.status === "running") {
        void startLogStream(selectedJob.id);
      } else {
        stopLogStream();
      }
    }
  }, [selectedJob?.id, selectedJob?.status, startLogStream, stopLogStream]);

  // Use a polling interval to update the job list when a job is actively running
  useEffect(() => {
    let timer: number;
    if (jobs.some((job) => job.status === "running" || job.status === "queued")) {
      timer = window.setInterval(() => {
        void loadJobs();
        if (selectedJobId) void loadJobDetail(selectedJobId);
      }, 3500);
    }
    return () => clearInterval(timer);
  }, [jobs, loadJobs, loadJobDetail, selectedJobId]);


  const handleSignOut = () => {
    authSession.logout();
    router.replace("/");
  };

  const completedJobs = jobs.filter(j => j.status === "completed" || j.status === "partial");
  const criticalCount = findings.filter(f => f.severity === "critical").length;

  const filteredFindings = filter === "all" ? findings : findings.filter(f => f.severity === filter);

  if (!isAuthenticated) {
    return null;
  }

  const openReportUrl = async (jobId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}${ENDPOINTS.audit.report(jobId)}`, {
        headers: authSession.token ? { Authorization: `Bearer ${authSession.token}` } : {},
      });
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `firecrow_report_${jobId}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
      } else {
        console.error("Failed to fetch report PDF");
      }
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", minHeight: "100vh" }}>
      {/* Sidebar */}
      <aside style={{ borderRight: `1px solid ${theme.border}`, padding: "24px 0", display: "flex", flexDirection: "column", position: "sticky", top: 0, height: "100vh", background: theme.bg }}>
        <div style={{ padding: "0 20px 24px", borderBottom: `1px solid ${theme.border}` }}>
          <Logo />
        </div>
        <nav style={{ flex: 1, padding: "16px 10px" }}>
          {SECTIONS.map(s => (
            <button key={s} onClick={() => setActive(s)} style={{ width: "100%", textAlign: "left", padding: "9px 12px", borderRadius: 6, fontSize: 13, fontWeight: active === s ? 500 : 400, color: active === s ? theme.text : theme.muted, background: active === s ? "#1a1a1a" : "transparent", marginBottom: 2, display: "flex", alignItems: "center", gap: 10, transition: "all .15s" }}
              onMouseEnter={e => { if (active !== s) e.currentTarget.style.color = theme.text; }}
              onMouseLeave={e => { if (active !== s) e.currentTarget.style.color = theme.muted; }}>
              <SectionIcon name={s} active={active === s} />
              {s}
            </button>
          ))}
        </nav>
        <div style={{ padding: "16px 12px", borderTop: `1px solid ${theme.border}` }}>
          <div style={{ padding: "10px 10px", borderRadius: 6, background: theme.surface, border: `1px solid ${theme.border}`, marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: theme.muted, marginBottom: 4 }}>Workspace</div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{authSession.workspace || "acme-corp"}</div>
            <div className="mono" style={{ fontSize: 9, color: theme.muted, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{authSession.userId || "usr_unknown"}</div>
          </div>
          <button onClick={handleSignOut} style={{ width: "100%", padding: "7px 10px", border: `1px solid ${theme.border}`, borderRadius: 6, background: "transparent", color: theme.muted, fontSize: 12, textAlign: "left" }}>Sign out</button>
        </div>
      </aside>

      {/* Main */}
      <main style={{ overflowY: "auto", background: "#0d0d0d" }}>
        <AnimatePresence mode="wait">
          <motion.div key={active} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
            {active === "Overview" && <OverviewSection jobs={jobs} findings={findings} criticalCount={criticalCount} setActive={setActive} />}
            {active === "Audits" && <AuditsSection jobs={jobs} selected={selectedJob} onSelect={setSelectedJobId} newUrl={newAuditUrl} setNewUrl={setNewAuditUrl} newBranch={newAuditBranch} setNewBranch={setNewAuditBranch} onJobStarted={runAudit} openReportUrl={openReportUrl} streamActive={streamActive} logs={logs} />}
            {active === "Findings" && <FindingsSection findings={filteredFindings} all={findings} filter={filter} setFilter={setFilter} expanded={expandedFinding} setExpanded={setExpandedFinding} selected={selectedJob} />}
            {active === "Reports" && <ReportsSection jobs={completedJobs} openReportUrl={openReportUrl} />}
            {active === "Settings" && <SettingsSection systemStatus={systemStatus} />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

function PageHeader({ kicker, title, action }: { kicker: string; title: string; action?: React.ReactNode }) {
  return (
    <div style={{ padding: "28px 32px 20px", borderBottom: `1px solid ${theme.border}`, display: "flex", justifyContent: "space-between", alignItems: "flex-end", background: theme.bg }}>
      <div>
        <p className="mono" style={{ fontSize: 10, color: theme.orange, letterSpacing: "0.16em", textTransform: "uppercase", marginBottom: 6 }}>{kicker}</p>
        <h1 style={{ fontSize: 26, fontWeight: 500, letterSpacing: "-0.02em" }}>{title}</h1>
      </div>
      {action}
    </div>
  );
}

function MetricCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: boolean }) {
  return (
    <div style={{ background: theme.surface, border: `1px solid ${accent ? theme.orangeBorder : theme.border}`, borderRadius: 8, padding: "18px 20px" }}>
      <div style={{ fontSize: 11, color: theme.muted, marginBottom: 12 }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 500, fontFamily: "'IBM Plex Mono', monospace", color: accent ? theme.orange : theme.text }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: theme.muted, marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function OverviewSection({ jobs, findings, criticalCount, setActive }: { jobs: Job[]; findings: Finding[]; criticalCount: number; setActive: (s: string) => void }) {
  const running = jobs.filter(j => j.status === "running").length;
  const latestCompleted = jobs.find(j => j.status === "completed" || j.status === "partial");

  return (
    <div>
      <PageHeader kicker="Fire Crow · Workspace" title="Overview" />
      <div style={{ padding: "24px 32px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
          <MetricCard label="Active Audits" value={running} sub={`${running} running`} />
          <MetricCard label="Total Jobs" value={jobs.length} sub="this workspace" />
          <MetricCard label="Critical Findings" value={criticalCount} sub="need review" accent={criticalCount > 0} />
          <MetricCard label="Latest Report" value={latestCompleted ? "Ready" : "None"} sub={latestCompleted ? shortRepoName(latestCompleted.repo_url) : "no completed audits"} />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {/* Recent runs */}
          <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, overflow: "hidden" }}>
            <div style={{ padding: "14px 18px", borderBottom: `1px solid ${theme.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 500 }}>Recent audits</span>
              <button onClick={() => setActive("Audits")} style={{ fontSize: 11, color: theme.orange, background: "none", border: "none", cursor: "pointer" }}>View all →</button>
            </div>
            {jobs.slice(0, 4).map(j => (
              <div key={j.id} style={{ padding: "12px 18px", borderBottom: `1px solid ${theme.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{shortRepoName(j.repo_url)}</div>
                  <div className="mono" style={{ fontSize: 10, color: theme.muted }}>{j.repo_branch} · {formatDateTime(j.created_at)}</div>
                </div>
                <StatusPill status={j.status} />
              </div>
            ))}
            {jobs.length === 0 && <div style={{ padding: "20px", color: theme.muted, fontSize: 13, textAlign: "center" }}>No audits run yet.</div>}
          </div>

          {/* Severity distribution */}
          <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, overflow: "hidden" }}>
            <div style={{ padding: "14px 18px", borderBottom: `1px solid ${theme.border}` }}>
              <span style={{ fontSize: 12, fontWeight: 500 }}>Severity distribution</span>
            </div>
            <div style={{ padding: "16px 18px" }}>
              {findings.length === 0 ? <div style={{ color: theme.muted, fontSize: 13, textAlign: "center" }}>No findings available.</div> :
              [["critical", theme.red], ["high", theme.orange], ["medium", theme.amber], ["low", theme.blue], ["info", theme.muted]].map(([sev, color]) => {
                const count = findings.filter(f => f.severity === sev).length;
                const pct = findings.length > 0 ? Math.round((count / findings.length) * 100) : 0;
                return (
                  <div key={sev} style={{ marginBottom: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span className="mono" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color }}>{sev}</span>
                      <span className="mono" style={{ fontSize: 10, color: theme.muted }}>{count}</span>
                    </div>
                    <div style={{ height: 3, background: theme.dim, borderRadius: 2, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 2, transition: "width .6s ease" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function AuditsSection({ jobs, selected, onSelect, newUrl, setNewUrl, newBranch, setNewBranch, onJobStarted, openReportUrl, streamActive, logs }: { jobs: Job[]; selected: Job | null; onSelect: (id: string) => void; newUrl: string; setNewUrl: (s: string) => void; newBranch: string; setNewBranch: (s: string) => void; onJobStarted: (p: {repo_url: string; repo_branch: string;}) => Promise<Job | null>; openReportUrl: (id: string) => void; streamActive: boolean; logs: LogLine[]; }) {
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUrl.trim()) return;
    setSubmitting(true);
    try {
      await onJobStarted({ repo_url: newUrl, repo_branch: newBranch });
      setNewUrl("");
      setNewBranch("main");
    } catch (e) {
      console.error(e);
      alert("Failed to submit audit.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <PageHeader kicker="Security Auditing" title="Audits" />
      <div style={{ padding: "24px 32px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>
        {/* New audit form & list */}
        <div>
          <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, overflow: "hidden", marginBottom: 16 }}>
            <div style={{ padding: "14px 18px", borderBottom: `1px solid ${theme.border}` }}>
              <p className="mono" style={{ fontSize: 10, color: theme.orange, letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 4 }}>New audit</p>
              <span style={{ fontSize: 14, fontWeight: 500 }}>Start a scan</span>
            </div>
            <form onSubmit={handleSubmit} style={{ padding: "18px" }}>
              <label style={{ display: "block", fontSize: 11, color: theme.muted, marginBottom: 6 }}>Repository URL</label>
              <input value={newUrl} onChange={e => setNewUrl(e.target.value)} placeholder="https://github.com/org/repository" style={{ width: "100%", background: theme.bg, border: `1px solid ${theme.border}`, borderRadius: 6, padding: "10px 12px", fontSize: 12, color: theme.text, marginBottom: 12, outline: "none" }} />
              <label style={{ display: "block", fontSize: 11, color: theme.muted, marginBottom: 6 }}>Branch</label>
              <input value={newBranch} onChange={e => setNewBranch(e.target.value)} placeholder="main" style={{ width: "100%", background: theme.bg, border: `1px solid ${theme.border}`, borderRadius: 6, padding: "10px 12px", fontSize: 12, color: theme.text, marginBottom: 16, outline: "none" }} />
              <div style={{ padding: "10px 12px", background: "#1a1200", border: "1px solid #2a1f00", borderRadius: 6, marginBottom: 16 }}>
                <span style={{ fontSize: 11, color: "#aa8800", lineHeight: 1.6 }}>Only audit repositories you own or are authorized to test.</span>
              </div>
              <button type="submit" disabled={submitting || !newUrl.trim()} style={{ width: "100%", padding: "11px", background: submitting ? theme.dim : theme.orange, color: submitting ? theme.muted : "#160800", borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: submitting ? "not-allowed" : "pointer", transition: "background .2s" }}>
                {submitting ? "Queuing audit…" : "Start audit →"}
              </button>
            </form>
          </div>

          <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, overflow: "hidden" }}>
            <div style={{ padding: "14px 18px", borderBottom: `1px solid ${theme.border}`, fontSize: 14, fontWeight: 500, display: "flex", justifyContent: "space-between" }}>
              <span>Recent jobs</span>
            </div>
            {jobs.length === 0 ? <div style={{ padding: "20px", color: theme.muted, fontSize: 12, textAlign: "center" }}>No audits.</div> :
            jobs.map((j: Job) => (
              <button key={j.id} onClick={() => onSelect(j.id)} style={{ width: "100%", textAlign: "left", padding: "13px 18px", borderBottom: `1px solid ${theme.border}`, display: "flex", justifyContent: "space-between", alignItems: "center", background: selected?.id === j.id ? "#1a1a1a" : "transparent", transition: "background .15s", borderLeft: selected?.id === j.id ? `2px solid ${theme.orange}` : "2px solid transparent" }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 3 }}>{shortRepoName(j.repo_url)}</div>
                  <div className="mono" style={{ fontSize: 10, color: theme.muted }}>{j.repo_branch} · {formatDateTime(j.created_at)}</div>
                </div>
                <StatusPill status={j.status} />
              </button>
            ))}
          </div>
        </div>

        {/* Job detail */}
        {selected && (
          <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, overflow: "hidden" }}>
            <div style={{ padding: "14px 18px", borderBottom: `1px solid ${theme.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <p className="mono" style={{ fontSize: 10, color: theme.muted, marginBottom: 2 }}>Selected audit</p>
                <span style={{ fontSize: 14, fontWeight: 500 }}>{shortRepoName(selected.repo_url)}</span>
              </div>
              <StatusPill status={selected.status} />
            </div>
            <div style={{ padding: "18px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
                {[["Branch", selected.repo_branch], ["Created", formatDateTime(selected.created_at)]].map(([l, v]) => (
                  <div key={l as string} style={{ background: theme.bg, border: `1px solid ${theme.border}`, borderRadius: 6, padding: "12px 14px" }}>
                    <div className="mono" style={{ fontSize: 9, color: theme.muted, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>{l}</div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>{v}</div>
                  </div>
                ))}
              </div>

              <div style={{ marginBottom: 16 }}>
                <div className="mono" style={{ fontSize: 9, color: theme.muted, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>Pipeline</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {["Recon", "SAST", "Deps", "IaC", "Sandbox", "Report"].map((stage) => {
                    const done = selected.status === "completed" || selected.status === "partial";
                    const current = selected.status === "running";
                    return (
                      <div key={stage} style={{ padding: "4px 10px", borderRadius: 4, background: done ? "rgba(46,204,113,0.08)" : current ? theme.orangeDim : "#161616", border: `1px solid ${done ? "rgba(46,204,113,0.2)" : current ? theme.orangeBorder : theme.border}` }}>
                        <span className="mono" style={{ fontSize: 9, color: done ? theme.green : current ? theme.orange : theme.muted }}>{stage}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {selected.report_pdf_url && (
                <button onClick={() => openReportUrl(selected.id)} style={{ width: "100%", padding: "10px", border: `1px solid ${theme.border}`, borderRadius: 6, background: "transparent", color: theme.text, fontSize: 12, fontWeight: 500 }}>
                  Download PDF report ↓
                </button>
              )}
              {selected.error_message && (
                <div style={{ padding: "10px 12px", background: "rgba(231,76,60,0.06)", border: "1px solid rgba(231,76,60,0.15)", borderRadius: 6, fontSize: 12, color: "#e0887e", marginTop: 10 }}>
                  {selected.error_message}
                </div>
              )}
            </div>

            <div style={{ borderTop: `1px solid ${theme.border}`, padding: "14px 18px" }}>
              <div className="mono" style={{ fontSize: 9, color: theme.muted, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>Live logs / Events</div>
              <div style={{ background: theme.bg, borderRadius: 6, padding: "12px 14px", maxHeight: 160, overflowY: "auto", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, lineHeight: 1.8 }}>
                {logs.length > 0 ? logs.map(l => (
                  <div key={l.id} style={{ display: "flex", gap: 6 }}>
                    <span style={{ color: theme.muted }}>[{new Date(l.timestamp).toLocaleTimeString()}]</span>
                    <span style={{ color: l.log_level === "ERROR" ? theme.red : theme.text }}>{l.message}</span>
                  </div>
                )) : <div style={{ color: theme.muted }}>No live logs available.</div>}
                {streamActive && <div style={{ color: theme.blue }}>● Streaming live logs...</div>}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function FindingsSection({ findings, all, filter, setFilter, expanded, setExpanded, selected }: { findings: Finding[]; all: Finding[]; filter: string; setFilter: (s: string) => void; expanded: string | null; setExpanded: (s: string | null) => void; selected: Job | null; }) {
  const counts = ["all", "critical", "high", "medium", "low", "info"].reduce((acc: Record<string, number>, s) => {
    acc[s] = s === "all" ? all.length : all.filter((f: Finding) => f.severity === s).length;
    return acc;
  }, {});

  return (
    <div>
      <PageHeader kicker="Vulnerability Intelligence" title="Findings" />
      <div style={{ padding: "24px 32px" }}>
        {selected ? (
          <div style={{ marginBottom: 20, padding: 12, background: theme.surface, borderRadius: 6, border: `1px solid ${theme.border}` }}>
            <span style={{ fontSize: 12, color: theme.muted }}>Findings for </span>
            <span style={{ fontSize: 13, fontWeight: 500 }}>{shortRepoName(selected.repo_url)}</span>
            <span className="mono" style={{ fontSize: 10, color: theme.muted, marginLeft: 10 }}>Branch {selected.repo_branch}</span>
          </div>
        ) : (
          <div style={{ marginBottom: 20, padding: 12, background: theme.surface, borderRadius: 6, border: `1px solid ${theme.border}` }}>
            <span style={{ fontSize: 12, color: theme.muted }}>Select an audit from the Audits tab to view findings.</span>
          </div>
        )}

        {/* Filter rail */}
        <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
          {["all", "critical", "high", "medium", "low", "info"].map(s => (
            <button key={s} onClick={() => setFilter(s)} style={{ padding: "5px 12px", borderRadius: 4, border: `1px solid ${filter === s ? theme.orange : theme.border}`, background: filter === s ? theme.orangeDim : "transparent", fontSize: 11, fontWeight: 500, color: filter === s ? theme.orange : theme.muted, cursor: "pointer", transition: "all .15s", display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ textTransform: "capitalize" }}>{s}</span>
              <span className="mono" style={{ fontSize: 10 }}>{counts[s]}</span>
            </button>
          ))}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {findings.map((f: Finding) => (
            <div key={f.id} style={{ background: theme.surface, border: `1px solid ${expanded === f.id ? theme.orangeBorder : theme.border}`, borderRadius: 8, overflow: "hidden", transition: "border-color .2s" }}>
              <button onClick={() => setExpanded(expanded === f.id ? null : f.id)} style={{ width: "100%", display: "flex", alignItems: "center", gap: 14, padding: "14px 18px", background: "transparent", textAlign: "left" }}>
                <SeverityPill severity={f.severity} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{f.title}</div>
                  <div className="mono" style={{ fontSize: 10, color: theme.muted }}>{f.agent_source}</div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
                  {f.cvss_score !== null && <span className="mono" style={{ fontSize: 10, color: theme.muted }}>CVSS {f.cvss_score?.toFixed(1)}</span>}
                  <span style={{ color: theme.muted, fontSize: 12, transition: "transform .2s", transform: expanded === f.id ? "rotate(180deg)" : "none" }}>▾</span>
                </div>
              </button>
              <AnimatePresence initial={false}>
                {expanded === f.id && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }}>
                    <div style={{ borderTop: `1px solid ${theme.border}`, padding: "16px 18px", display: "flex", flexDirection: "column", gap: 14 }}>
                      <div>
                        <div className="mono" style={{ fontSize: 9, color: theme.orange, letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 6 }}>Risk explanation</div>
                        <p style={{ fontSize: 13, color: "#b0b0b0", lineHeight: 1.6 }}>{f.description}</p>
                      </div>
                      {f.remediation && (
                        <div>
                          <div className="mono" style={{ fontSize: 9, color: theme.orange, letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 6 }}>Recommended fix</div>
                          <div style={{ background: theme.bg, borderRadius: 6, padding: "12px 14px", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: theme.green, lineHeight: 1.6 }}>{f.remediation}</div>
                        </div>
                      )}
                      <div>
                        <div className="mono" style={{ fontSize: 9, color: theme.orange, letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 6 }}>Evidence</div>
                        <p style={{ fontSize: 13, color: theme.muted, lineHeight: 1.6 }}>{f.evidence || "No evidence snippet provided."}</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
          {findings.length === 0 && <div style={{ textAlign: "center", padding: 40, color: theme.muted, fontSize: 13 }}>No findings match this filter.</div>}
        </div>
      </div>
    </div>
  );
}

function ReportsSection({ jobs, openReportUrl }: { jobs: Job[]; openReportUrl: (id: string) => void; }) {
  return (
    <div>
      <PageHeader kicker="Audit Output" title="Reports" />
      <div style={{ padding: "24px 32px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {jobs.length === 0 ? <div style={{ color: theme.muted, fontSize: 13 }}>No completed audits yet.</div> :
          jobs.map(j => (
            <div key={j.id} style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, padding: "18px 20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                  <StatusPill status={j.status} />
                  <span style={{ fontSize: 15, fontWeight: 500 }}>{shortRepoName(j.repo_url)}</span>
                </div>
                <div className="mono" style={{ fontSize: 10, color: theme.muted }}>Branch {j.repo_branch} · finished {j.finished_at ? formatDateTime(j.finished_at) : "-"}</div>
              </div>
              {j.report_pdf_url ? (
                <button onClick={() => openReportUrl(j.id)} style={{ padding: "8px 16px", border: `1px solid ${theme.border}`, borderRadius: 6, background: "transparent", color: theme.text, fontSize: 12, fontWeight: 500, cursor: "pointer" }}>Open report ↓</button>
              ) : (
                <span style={{ color: theme.muted, fontSize: 12 }}>No PDF artifact</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SettingsSection({ systemStatus }: { systemStatus: SystemStatus | null }) {
  return (
    <div>
      <PageHeader kicker="Configuration" title="Settings" />
      <div style={{ padding: "24px 32px" }}>
        <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, overflow: "hidden", maxWidth: 640 }}>
          <div style={{ padding: "14px 18px", borderBottom: `1px solid ${theme.border}`, fontSize: 14, fontWeight: 500 }}>System status</div>
          {[
            ["API", systemStatus ? systemStatus.api : "checking", systemStatus?.api === "online" ? theme.green : theme.amber],
            ["Database", systemStatus ? systemStatus.database : "checking", systemStatus?.database === "connected" ? theme.green : theme.amber],
            ["Sandbox", systemStatus ? systemStatus.sandbox_mode : "checking", theme.text],
          ].map(([l, v, c]) => (
            <div key={l as string} style={{ padding: "14px 18px", borderBottom: `1px solid ${theme.border}`, display: "flex", justifyContent: "space-between" }}>
              <span className="mono" style={{ fontSize: 11, color: theme.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>{l}</span>
              <span style={{ fontSize: 12, color: c as string, fontWeight: 500 }}>{v}</span>
            </div>
          ))}
        </div>

        <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, overflow: "hidden", maxWidth: 640, marginTop: 16 }}>
          <div style={{ padding: "14px 18px", borderBottom: `1px solid ${theme.border}`, fontSize: 14, fontWeight: 500 }}>Integrations</div>
          {systemStatus ? Object.entries(systemStatus.integrations || {}).map(([l, on]) => (
            <div key={l} style={{ padding: "14px 18px", borderBottom: `1px solid ${theme.border}`, display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 13, color: theme.text }}>{l.replace("_", " ")}</span>
              <span className="mono" style={{ fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: on ? theme.green : theme.amber }}>{on ? "configured" : "not configured"}</span>
            </div>
          )) : <div style={{ padding: "14px 18px", color: theme.muted, fontSize: 12 }}>Loading integrations...</div>}
        </div>
      </div>
    </div>
  );
}

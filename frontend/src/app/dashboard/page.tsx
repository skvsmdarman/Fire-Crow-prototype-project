"use client";

import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import { useAuthSession } from "../../shared/hooks/useAuthSession";
import { useSSE, LogLine } from "../../shared/hooks/useSSE";
import useAudits from "../../features/audits/hooks";
import { fetchSystemStatus as apiFetchSystemStatus } from "../../features/audits/api";
import { Job, Finding, SystemStatus } from "../../features/audits/types";
import { formatDateTime, shortRepoName } from "../../shared/utils/format";
import { API_BASE_URL, apiClient } from "../../shared/api/client";
import AuditVerificationCard from "../../features/audits/components/AuditVerificationCard";
import { ENDPOINTS } from "../../shared/api/endpoints";
import { useToast } from "../../components/ui/Toast";
import LogStream from "../../features/audits/components/LogStream";
import dynamic from "next/dynamic";
import ChatWidget from "../../components/ChatWidget";
import Leaderboard from "../../components/Leaderboard";
import { subscribeUserToPush } from "../../lib/pushNotifications";
import { PRODUCT_NAME, PRODUCT_TAGLINE, GITHUB_SCOPE_DESCRIPTIONS } from "../../shared/config/app";
import styles from "./page.module.css";

const AttackGraph = dynamic(() => import("../../components/AttackGraph"), { ssr: false });

interface AuditInsightResponse {
  jobId: string;
  insight: string | null;
  enabled: boolean;
}

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



function SectionIcon({ name, active }: { name: string; active: boolean }) {
  const color = active ? theme.orange : theme.muted;
  const icons: Record<string, React.ReactNode> = {
    Overview: <path d="M4 5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5zm10 0a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1V5zM4 14a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-5zm10-2a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-7z" />,
    Audits: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
    Findings: <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4m0 4h.01" />,
    Reports: <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8m8 4H8m2-8H8" />,
    Leaderboard: <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.45 1-1 1H4v2h16v-2h-5c-.55 0-1-.45-1-1v-2.34M12 2a4 4 0 0 0-4 4v5c0 .55.45 1 1 1h6c.55 0 1-.45 1-1V6a4 4 0 0 0-4-4z" />,
    Settings: <><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></>,
  };
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      {icons[name]}
    </svg>
  );
}

const SECTIONS = ["Overview", "Audits", "Findings", "Reports", "Leaderboard", "Settings"];

export default function Dashboard() {
  const router = useRouter();
  const authSession = useAuthSession();
  const isAuthenticated = authSession.hasDashboardSession;
  const validateSession = authSession.validateSession;

  const [active, setActive] = useState("Overview");
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isValidating, setIsValidating] = useState(true);
  const [jobInsight, setJobInsight] = useState<AuditInsightResponse | null>(null);

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
  } = useAudits(isAuthenticated);

  const prevStatusesRef = React.useRef<Record<string, string>>({});
  const { toast } = useToast();

  useEffect(() => {
    if (isAuthenticated) {
      subscribeUserToPush();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    jobs.forEach((job) => {
      const prevStatus = prevStatusesRef.current[job.id];
      if (prevStatus && prevStatus !== job.status) {
        if (["completed", "partial"].includes(job.status)) {
          const mailPart = job.email_delivered 
            ? "Premium report sent to your mailbox." 
            : "Email report skipped or failed.";
          const issuePart = job.github_issues_raised 
            ? "Vulnerability tracking issues raised on GitHub." 
            : "GitHub tracking issues skipped or not raised.";
          
          if (job.status === "completed") {
            toast(`Audit Job Completed! ${mailPart} ${issuePart}`, "success");
          } else {
            toast(`Audit Job completed partially! ${mailPart} ${issuePart}`, "info");
          }
        } else if (job.status === "failed") {
          toast(`Audit Job Failed! Please review operational console logs.`, "error");
        }
      }
      prevStatusesRef.current[job.id] = job.status;
    });
  }, [jobs, toast]);

  const selectedJob = jobs.find(j => j.id === selectedJobId) || null;
  const findings = selectedJobDetail?.findings || [];

  const { logs, streamActive, startLogStream, stopLogStream } = useSSE({
    authenticated: isAuthenticated,
    onJobStatusChange: () => {
      void loadJobs();
      if (selectedJobId) void loadJobDetail(selectedJobId);
    },
  });

  const fetchSystemStatus = useCallback(() => {
    apiFetchSystemStatus().then(setSystemStatus).catch(console.error);
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/signin");
      return;
    }
    
    let isMounted = true;
    validateSession().then((isValid) => {
      if (!isMounted) return;
      if (!isValid) {
        router.replace("/signin");
      } else {
        setIsValidating(false);
        fetchSystemStatus();
      }
    });
    
    return () => { isMounted = false; };
  }, [isAuthenticated, validateSession, fetchSystemStatus, router]);

  useEffect(() => {
    if (selectedJob?.id) {
      void startLogStream(selectedJob.id);
    } else {
      stopLogStream();
    }
  }, [selectedJob?.id, startLogStream, stopLogStream]);

  useEffect(() => {
    let cancelled = false;

    if (!selectedJobId || !isAuthenticated || !systemStatus?.llm_features?.dashboard_insight) {
      return () => {
        cancelled = true;
      };
    }

    apiClient
      .get<AuditInsightResponse>(ENDPOINTS.audit.insight(selectedJobId))
      .then((response) => {
        if (!cancelled) {
          setJobInsight({ ...response, jobId: selectedJobId });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setJobInsight((current) => (current?.jobId === selectedJobId ? null : current));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, selectedJobId, systemStatus?.llm_features?.dashboard_insight]);

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
  const selectedJobInsight = systemStatus?.llm_features?.dashboard_insight && jobInsight?.jobId === selectedJobId ? jobInsight : null;

  const filteredFindings = filter === "all" ? findings : findings.filter(f => f.severity === filter);

  if (!isAuthenticated || isValidating) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#0d0d0d" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }} style={{ width: 32, height: 32, border: "2px solid #333", borderTopColor: theme.orange, borderRadius: "50%" }} />
          <div className="mono" style={{ fontSize: 11, color: theme.muted, letterSpacing: "0.1em", textTransform: "uppercase" }}>Validating session...</div>
        </div>
      </div>
    );
  }

  const openReportUrl = async (jobId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}${ENDPOINTS.audit.report(jobId)}`, {
        credentials: "include",
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
    <div className={styles.shell}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.brandBlock}>
          <span className={styles.brandMark}>FC</span>
          <div>
            <p className={styles.brandName}>{PRODUCT_NAME}</p>
            <span className={styles.brandSubtitle}>{PRODUCT_TAGLINE}</span>
          </div>
        </div>
        <nav className={styles.navStack}>
          {SECTIONS.map(s => (
            <button
              key={s}
              onClick={() => setActive(s)}
              className={`${styles.navItem} ${active === s ? styles.navItemActive : ""}`}
            >
              {active === s && <span className={styles.activeIndicator} />}
              <div className={styles.navItemContent}>
                <span className={`${active === s ? styles.navIconActive : ""}`}>
                  <SectionIcon name={s} active={active === s} />
                </span>
                <span className={styles.navLabel}>{s}</span>
              </div>
            </button>
          ))}
        </nav>
        <div className={styles.workspaceCard}>
          <div className={styles.authCardAccent} />
          <span className={styles.sectionKicker}>Workspace</span>
          <div className={styles.workspaceName}>{authSession.workspace || "acme-corp"}</div>
          <div className={styles.workspaceId}>{authSession.userId || "usr_unknown"}</div>
        </div>
        <button onClick={handleSignOut} className={styles.ghostAction}>Sign out</button>
      </aside>

      {/* Main Area */}
      <main className={styles.mainSurface}>
        <AnimatePresence mode="wait">
          <motion.div key={active} initial={{ opacity: 0, scale: 0.98, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98, y: -10 }} transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}>
            {active === "Overview" && <OverviewSection jobs={jobs} findings={findings} criticalCount={criticalCount} setActive={setActive} />}
            {active === "Audits" && <AuditsSection jobs={jobs} selected={selectedJob} insight={selectedJobInsight} onSelect={setSelectedJobId} newUrl={newAuditUrl} setNewUrl={setNewAuditUrl} newBranch={newAuditBranch} setNewBranch={setNewAuditBranch} onJobStarted={runAudit} openReportUrl={openReportUrl} streamActive={streamActive} logs={logs} />}
            {active === "Findings" && <FindingsSection findings={filteredFindings} all={findings} filter={filter} setFilter={setFilter} expanded={expandedFinding} setExpanded={setExpandedFinding} selected={selectedJob} />}
             {active === "Reports" && <ReportsSection jobs={completedJobs} openReportUrl={openReportUrl} />}
            {active === "Leaderboard" && (
              <div>
                <PageHeader kicker="Workspace Security" title="Leaderboard" />
                <div style={{ padding: "24px 32px", maxWidth: 800 }}>
                  <Leaderboard />
                </div>
              </div>
            )}
            {active === "Settings" && <SettingsSection systemStatus={systemStatus} />}
          </motion.div>
        </AnimatePresence>
      </main>
      {systemStatus?.llm_features?.chat_assistant ? (
        <ChatWidget jobId={selectedJobId} />
      ) : null}
    </div>
  );
}

function PageHeader({ kicker, title, action }: { kicker: string; title: string; action?: React.ReactNode }) {
  return (
    <div className={styles.topbar}>
      <div>
        <p className={`mono ${styles.sectionKicker}`}>{kicker}</p>
        <h1>{title}</h1>
      </div>
      {action && <div className={styles.headerActions}>{action}</div>}
    </div>
  );
}

function MetricCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: boolean }) {
  return (
    <div className={`${styles.metricCard} ${accent ? "accent" : ""}`}>
      <div className={styles.metricHeader}>
        <span>{label}</span>
        {accent && <span className={styles.metricAccent} style={{ background: "var(--red)", boxShadow: "0 0 0 4px rgba(255,48,71,0.12)" }} />}
      </div>
      <span className={styles.metricValue}>{value}</span>
      {sub && <p className={styles.metricNote}>{sub}</p>}
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

        <div className={styles.workGrid}>
          {/* Recent runs */}
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <span className={`mono ${styles.sectionKicker}`}>History</span>
                <h2>Recent audits</h2>
              </div>
              <button onClick={() => setActive("Audits")} className={styles.ghostAction}>View all →</button>
            </div>
            {jobs.length === 0 ? (
              <div className={styles.emptyState}>No audits run yet.</div>
            ) : (
              <div className={styles.jobList}>
                {jobs.slice(0, 4).map(j => (
                  <div key={j.id} className={styles.jobRow}>
                    <div className={styles.jobInfo}>
                      <svg className={styles.jobIcon} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                      <div className={styles.jobMetaBlock}>
                        <strong>{shortRepoName(j.repo_url)}</strong>
                        <small>{j.repo_branch} · {formatDateTime(j.created_at)}</small>
                      </div>
                    </div>
                    <StatusPill status={j.status} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Severity distribution */}
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <span className={`mono ${styles.sectionKicker}`}>Distribution</span>
                <h2>Severity breakdown</h2>
              </div>
            </div>
            <div className={styles.panel}>
              {findings.length === 0 ? <div className={styles.emptyState}>No findings available.</div> :
              [["critical", "var(--red)"], ["high", "var(--orange)"], ["medium", "var(--amber)"], ["low", "var(--blue)"], ["info", "var(--muted)"]].map(([sev, color]) => {
                const count = findings.filter(f => f.severity === sev).length;
                const pct = findings.length > 0 ? Math.round((count / findings.length) * 100) : 0;
                return (
                  <div key={sev} style={{ marginBottom: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span className="mono" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color }}>{sev}</span>
                      <span className="mono" style={{ fontSize: 10, color: "var(--muted)" }}>{count}</span>
                    </div>
                    <div style={{ height: 3, background: "var(--dim)", borderRadius: 2, overflow: "hidden" }}>
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

function AuditsSection({ jobs, selected, insight, onSelect, newUrl, setNewUrl, newBranch, setNewBranch, onJobStarted, openReportUrl, streamActive, logs }: { jobs: Job[]; selected: Job | null; insight: AuditInsightResponse | null; onSelect: (id: string) => void; newUrl: string; setNewUrl: (s: string) => void; newBranch: string; setNewBranch: (s: string) => void; onJobStarted: (p: {repo_url: string; repo_branch: string; attestation_accepted: boolean; authorization_scope: string;}) => Promise<Job | null>; openReportUrl: (id: string) => void; streamActive: boolean; logs: LogLine[]; }) {
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUrl.trim()) return;
    setSubmitting(true);
    try {
      await onJobStarted({ repo_url: newUrl, repo_branch: newBranch, attestation_accepted: true, authorization_scope: "authorized_representative" });
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
      <div className={styles.sectionBody}>
        {/* New audit form & list */}
        <div>
          <div className={styles.panel} style={{ marginBottom: 16 }}>
            <div className={styles.panelHeader}>
              <div>
                <span className={`mono ${styles.sectionKicker}`}>New audit</span>
                <h2>Start a scan</h2>
              </div>
            </div>
            <form onSubmit={handleSubmit} className={styles.auditForm}>
              <div>
                <span className={styles.sectionKicker} style={{ fontSize: 9, marginBottom: 6, display: "block" }}>Repository URL</span>
                <input value={newUrl} onChange={e => setNewUrl(e.target.value)} placeholder="https://github.com/org/repository" className={styles.urlInput} />
              </div>
              <div>
                <span className={styles.sectionKicker} style={{ fontSize: 9, marginBottom: 6, display: "block" }}>Branch</span>
                <input value={newBranch} onChange={e => setNewBranch(e.target.value)} placeholder="main" className={styles.urlInput} />
              </div>
              <div style={{ padding: "10px 12px", background: "rgba(255,184,0,0.06)", border: "1px solid rgba(255,184,0,0.15)", borderRadius: 10, fontSize: 11, color: "var(--amber)", lineHeight: 1.6 }}>
                Only audit repositories you own or are authorized to test.
              </div>
              <button type="submit" disabled={submitting || !newUrl.trim()} className={styles.submitButton}>
                {submitting ? "Queuing audit…" : "Start audit →"}
              </button>
            </form>
          </div>

          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <span className={`mono ${styles.sectionKicker}`}>History</span>
                <h2>Recent jobs</h2>
              </div>
            </div>
            {jobs.length === 0 ? <div className={styles.emptyState}>No audits.</div> :
            <div className={styles.jobList}>
              {jobs.map((j: Job) => (
                <button
                  key={j.id}
                  onClick={() => onSelect(j.id)}
                  className={`${styles.jobRow} ${selected?.id === j.id ? styles.jobRowActive : ""}`}
                >
                  {selected?.id === j.id && <span className={styles.activeJobIndicator} />}
                  <div className={styles.jobInfo}>
                    <svg className={styles.jobIcon} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                    <div className={styles.jobMetaBlock}>
                      <strong>{shortRepoName(j.repo_url)}</strong>
                      <small>{j.repo_branch} · {formatDateTime(j.created_at)}</small>
                    </div>
                  </div>
                  <StatusPill status={j.status} />
                </button>
              ))}
            </div>
            }
          </div>
        </div>

        {/* Job detail */}
        {selected && (
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <span className={`mono ${styles.sectionKicker}`}>Selected audit</span>
                <h2>{shortRepoName(selected.repo_url)}</h2>
              </div>
              <StatusPill status={selected.status} />
            </div>
            <div style={{ display: "grid", gap: 12 }}>
              <div className={styles.auditSummaryGrid}>
                {[["Branch", selected.repo_branch], ["Created", formatDateTime(selected.created_at)]].map(([l, v]) => (
                  <div key={l as string} className={styles.auditSummaryItem}>
                    <span>{l}</span>
                    <strong>{v}</strong>
                  </div>
                ))}
              </div>

              <div className={styles.auditStatusStrip}>
                <span className={`mono ${styles.sectionKicker}`} style={{ width: "100%", marginBottom: 4 }}>Pipeline</span>
                {["Recon", "Threat", "SAST", "Deps", "Config", "IaC", "Sandbox", "Report"].map((stage) => {
                  const done = selected.status === "completed" || selected.status === "partial";
                  const current = selected.status === "running";
                  return (
                    <span key={stage} style={{
                      color: done ? "var(--green)" : current ? "var(--orange)" : "var(--muted)",
                      background: done ? "rgba(0,230,118,0.08)" : current ? "var(--orangeDim)" : "rgba(255,255,255,0.03)",
                    }}>
                      {done ? "✓ " : current ? "● " : ""}{stage}
                    </span>
                  );
                })}
              </div>

              {insight?.enabled && insight.insight && (
                <div style={{ marginBottom: 16, padding: "12px 14px", background: "rgba(255, 107, 43, 0.08)", border: "1px solid rgba(255, 107, 43, 0.18)", borderRadius: 6 }}>
                  <div className="mono" style={{ fontSize: 9, color: theme.orange, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 8 }}>AI Insight</div>
                  <div style={{ fontSize: 13, lineHeight: 1.5, color: theme.text }}>{insight.insight}</div>
                  <div style={{ fontSize: 11, color: theme.muted, marginTop: 8 }}>Optional LLM hint only. Findings and report evidence remain the source of truth.</div>
                </div>
              )}

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

              <AuditVerificationCard job={selected} />

              {selected.status === "completed" ? (
                <div style={{ marginTop: 20 }}>
                  <div className="mono" style={{ fontSize: 9, color: theme.muted, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>Attack Graph</div>
                  <AttackGraph jobId={selected.id} />
                </div>
              ) : null}
            </div>

            <div style={{ borderTop: `1px solid ${theme.border}`, padding: "14px 18px" }}>
              <LogStream logs={logs} streamActive={streamActive} hasSelection={!!selected} />
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
      <div className={styles.sectionBody}>
        {selected ? (
          <div style={{ marginBottom: 20, padding: "12px 16px", background: "var(--surface)", borderRadius: "var(--card-radius)", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--orange)" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>Findings for </span>
            <span style={{ fontSize: 13, fontWeight: 500 }}>{shortRepoName(selected.repo_url)}</span>
            <span className="mono" style={{ fontSize: 10, color: "var(--muted)", marginLeft: "auto" }}>Branch {selected.repo_branch}</span>
          </div>
        ) : (
          <div className={styles.emptyState} style={{ marginBottom: 20 }}>
            Select an audit from the Audits tab to view findings.
          </div>
        )}

        {/* Filter rail */}
        <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
          {["all", "critical", "high", "medium", "low", "info"].map(s => (
            <button key={s} onClick={() => setFilter(s)} style={{
              padding: "6px 14px", borderRadius: 999, fontSize: 11, fontWeight: 600,
              border: `1px solid ${filter === s ? "var(--orange)" : "var(--border)"}`,
              background: filter === s ? "var(--orangeDim)" : "transparent",
              color: filter === s ? "var(--orange)" : "var(--muted)",
              cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
              transition: "all .15s",
            }}>
              <span style={{ textTransform: "capitalize" }}>{s}</span>
              <span className="mono" style={{ fontSize: 10, opacity: 0.7 }}>{counts[s]}</span>
            </button>
          ))}
        </div>

        <div className={styles.findingList}>
          {findings.map((f: Finding) => (
            <div key={f.id} className={`${styles.findingRowContainer} ${expanded === f.id ? styles.findingExpanded : ""}`}>
              <button onClick={() => setExpanded(expanded === f.id ? null : f.id)} className={styles.findingRowHeader}>
                <div className={styles.findingRowMain}>
                  <SeverityPill severity={f.severity} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p className={styles.findingTitle}>{f.title}</p>
                    <span className={styles.findingAgent}>{f.agent_source}</span>
                  </div>
                </div>
                <div className={styles.findingRowMeta}>
                  {f.cvss_score !== null && <span className={styles.findingCvss}>CVSS {f.cvss_score?.toFixed(1)}</span>}
                  <span className={`${styles.expandArrow} ${expanded === f.id ? styles.arrowRotated : ""}`}>▾</span>
                </div>
              </button>
              <AnimatePresence initial={false}>
                {expanded === f.id && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }}>
                    <div className={styles.findingDetailPanel}>
                      <div className={styles.findingDetailContent}>
                        <div className={styles.detailSection}>
                          <h4>Risk explanation</h4>
                          <p className={styles.findingDescription}>{f.description}</p>
                        </div>
                        {f.remediation && (
                          <div className={styles.detailSection}>
                            <h4>Recommended fix</h4>
                            <div className={styles.remediationContent}>{f.remediation}</div>
                          </div>
                        )}
                        <div className={styles.detailSection}>
                          <h4>Evidence</h4>
                          <p className={styles.evidenceBlock} style={{ margin: 0, fontSize: 12, lineHeight: 1.6 }}>{f.evidence || "No evidence snippet provided."}</p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
          {findings.length === 0 && <div className={styles.emptyState}>No findings match this filter.</div>}
        </div>
      </div>
    </div>
  );
}

function ReportsSection({ jobs, openReportUrl }: { jobs: Job[]; openReportUrl: (id: string) => void; }) {
  return (
    <div>
      <PageHeader kicker="Audit Output" title="Reports" />
      <div className={styles.sectionBody}>
        <div className={styles.reportList}>
          {jobs.length === 0 ? <div className={styles.emptyState}>No completed audits yet.</div> :
          jobs.map(j => (
            <div key={j.id} className={styles.reportRow}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <StatusPill status={j.status} />
                  <h3>{shortRepoName(j.repo_url)}</h3>
                </div>
                <p>Branch {j.repo_branch} · finished {j.finished_at ? formatDateTime(j.finished_at) : "-"}</p>
              </div>
              {j.report_pdf_url ? (
                <button onClick={() => openReportUrl(j.id)} className={styles.ghostAction}>Open report ↓</button>
              ) : (
                <span className={styles.reportMissing}>No PDF artifact</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface DbStats {
  dialect: string;
  db_size_bytes: number | null;
  row_counts: Record<string, number>;
  pending_migrations: boolean;
}

function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "Unknown";
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function SettingsSection({ systemStatus }: { systemStatus: SystemStatus | null }) {
  const { toast } = useToast();
  const [dbStats, setDbStats] = useState<DbStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [pruning, setPruning] = useState(false);

  const isAdmin = Boolean(systemStatus?.integrations);

  const fetchDbStats = useCallback(async () => {
    if (!isAdmin) return;
    setLoadingStats(true);
    try {
      const stats = await apiClient.get<DbStats>(ENDPOINTS.system.dbStats);
      setDbStats(stats);
    } catch (err: unknown) {
      console.error("Failed to fetch database stats:", err);
    } finally {
      setLoadingStats(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    if (isAdmin) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchDbStats();
    }
  }, [isAdmin, fetchDbStats]);

  const handleHousekeeping = async () => {
    if (pruning) return;
    setPruning(true);
    toast("Initiating database housekeeping and storage pruning...", "info");
    try {
      const res = await apiClient.post<{ status: string; counts: Record<string, number> }>(
        ENDPOINTS.system.dbHousekeeping
      );
      if (res.status === "success") {
        const counts = res.counts;
        const summary = `Housekeeping completed. Pruned: ${counts.pruned_logs} logs, ${counts.pruned_artifacts} artifacts. Deleted: ${counts.deleted_jobs_expiry} expired jobs, ${counts.deleted_jobs_overflow} overflow jobs.`;
        toast(summary, "success");
        fetchDbStats();
      } else {
        toast("Housekeeping reported non-success status.", "error");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute database housekeeping.";
      toast(msg, "error");
    } finally {
      setPruning(false);
    }
  };

  return (
    <div>
      <PageHeader kicker="Configuration" title="Settings" />
      <div className={styles.sectionBody} style={{ maxWidth: 640 }}>
        
        {/* System Status */}
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <span className={`mono ${styles.sectionKicker}`}>Status</span>
              <h2>System status</h2>
            </div>
          </div>
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

        {/* Integrations */}
        <div className={styles.statusCard}>
          <div className={styles.statusCardHeader}>
            <span>Integrations</span>
          </div>
          {!systemStatus ? (
            <div className={styles.emptyState} style={{ border: "none" }}>Loading integrations...</div>
          ) : !systemStatus.integrations ? (
            <div className={styles.emptyState} style={{ border: "none" }}>Only accessible to administrators.</div>
          ) : (
            <div className={styles.integrationList}>
              {Object.entries(systemStatus.integrations).map(([l, on]) => (
                <div key={l} className={styles.integrationRow}>
                  <span>{l.replace("_", " ")}</span>
                  <strong className={on ? styles.integrationOn : styles.integrationOff}>
                    {on ? "configured" : "not configured"}
                  </strong>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Scanner Capabilities */}
        <div className={styles.statusCard}>
          <div className={styles.statusCardHeader}>
            <span>Scanner Capabilities</span>
          </div>
          {!systemStatus?.scanner_capabilities ? (
            <div className={styles.emptyState} style={{ border: "none" }}>Scanner capabilities not available.</div>
          ) : (
            <div className={styles.agentGrid} style={{ marginTop: 4 }}>
              {Object.entries(systemStatus.scanner_capabilities).map(([scanner, available]) => (
                <div key={scanner} className={styles.statusCard} style={{ border: "none", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", borderRadius: 0 }}>
                  <div className={styles.statusCardHeader}>
                    <span>{scanner.replace("_", " ")}</span>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: available ? "var(--green)" : "var(--muted)", flexShrink: 0 }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* GitHub Permissions */}
        <div className={styles.integrationList} style={{ marginTop: 0 }}>
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="var(--text)"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.49.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.56 9.56 0 0 1 12 6.84c.85.004 1.7.115 2.5.337 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10.02 10.02 0 0 0 22 12c0-5.52-4.48-10-10-10z"/></svg>
                <span className={`mono ${styles.sectionKicker}`}>GitHub Permissions</span>
              </div>
            </div>
            {!systemStatus?.github_permissions ? (
              <div className={styles.emptyState}>GitHub permissions not available.</div>
            ) : (
              <div className={styles.integrationList}>
                {systemStatus.github_permissions.scopes.map((scope) => {
                  const desc = GITHUB_SCOPE_DESCRIPTIONS[scope] || systemStatus.github_permissions?.descriptions[scope] || scope;
                  return (
                    <div key={scope} className={styles.integrationRow}>
                      <span className="mono" style={{ color: "var(--orange)", fontWeight: 500 }}>{scope}</span>
                      <span style={{ fontSize: 11, color: "var(--muted)", textAlign: "right", maxWidth: "70%" }}>{desc}</span>
                    </div>
                  );
                })}
                <div className={styles.integrationRow} style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.5 }}>
                  Labels are automatically created for security findings (firecrow, critical, high, medium, low, security, needs-triage).
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Admin Database Management */}
        {isAdmin && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 8 }}>
            <div className={`mono ${styles.sectionKicker}`} style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--orange)" strokeWidth="2"><path d="M12 22c5.523 0 10-2.239 10-5V7c0-2.761-4.477-5-10-5S2 4.239 2 7v10c0 2.761 4.477 5 10 5z"/><path d="M22 7c0 2.761-4.477 5-10 5S2 12 2 7"/><path d="M2 12c0 2.761 4.477 5 10 5s10-2.239 10-5"/></svg>
              Database Control Panel
            </div>

            {/* Quick Metrics */}
            <div className={styles.metricsGrid}>
              <div className={styles.statusCard}>
                <div className={styles.statusCardHeader}>
                  <span>Engine Dialect</span>
                </div>
                <strong style={{ textTransform: "capitalize", fontSize: 18 }}>{dbStats?.dialect || (loadingStats ? "..." : "Unknown")}</strong>
              </div>
              <div className={styles.statusCard}>
                <div className={styles.statusCardHeader}>
                  <span>Database Size</span>
                </div>
                <strong style={{ fontSize: 18 }}>{dbStats ? formatBytes(dbStats.db_size_bytes) : (loadingStats ? "..." : "Unknown")}</strong>
              </div>
              <div className={styles.statusCard}>
                <div className={styles.statusCardHeader}>
                  <span>Migration State</span>
                </div>
                <strong style={{ fontSize: 14, color: dbStats?.pending_migrations ? "var(--red)" : "var(--green)" }}>
                  {dbStats ? (dbStats.pending_migrations ? "Pending Update" : "Up-to-Date") : (loadingStats ? "..." : "Unknown")}
                </strong>
              </div>
            </div>

            {/* Detailed Row Counts */}
            <div className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <span className={`mono ${styles.sectionKicker}`}>Tables</span>
                  <h2>Registry Metrics</h2>
                </div>
                {loadingStats && <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>Refreshing...</span>}
              </div>
              {dbStats?.row_counts ? (
                Object.entries(dbStats.row_counts).map(([tbl, cnt]) => (
                  <div key={tbl} className={styles.integrationRow}>
                    <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{tbl}</span>
                    <span className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--text)", background: "var(--dim)", padding: "2px 8px", borderRadius: 4 }}>{cnt}</span>
                  </div>
                ))
              ) : (
                <div className={styles.emptyState}>
                  {loadingStats ? "Loading table stats..." : "No registry data loaded."}
                </div>
              )}
            </div>

            {/* Housekeeping Action */}
            <div className={styles.panel} style={{ borderColor: "var(--orangeBorder)" }}>
              <div className={styles.panelHeader}>
                <div>
                  <span className={`mono ${styles.sectionKicker}`}>Storage Optimization</span>
                  <h2>Prune Database Records</h2>
                </div>
              </div>
              <p className={styles.emptyState} style={{ textAlign: "left", border: "none", padding: "0 0 16px", color: "var(--muted)", fontSize: 12, lineHeight: 1.5 }}>
                Detailed agent logs and raw artifacts older than 7 days, as well as entire audit jobs older than 30 days, will be pruned. Keeps maximum of 20 jobs per user.
              </p>
              <button
                onClick={handleHousekeeping}
                disabled={pruning}
                className={styles.ghostAction}
                style={{
                  alignSelf: "flex-start",
                  background: pruning ? "transparent" : "linear-gradient(135deg, var(--fire), var(--orange) 62%, var(--amber))",
                  color: pruning ? "var(--muted)" : "#160800",
                  border: pruning ? "1px solid var(--border)" : "none",
                  fontWeight: 700,
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ animation: pruning ? "spin 1.5s linear infinite" : "none" }}>
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
                </svg>
                {pruning ? "Executing Pruning Pipeline..." : "Run Database Housekeeping"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

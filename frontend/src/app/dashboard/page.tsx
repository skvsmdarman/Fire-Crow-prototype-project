"use client";

import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Database,
  Download,
  FileText,
  Fingerprint,
  Globe,
  HardDrive,
  LogOut,
  Play,
  PlusCircle,
  RefreshCw,
  Search,
  ShieldCheck,
  User,
} from "lucide-react";

import FireCrowLoader from "../../components/FireCrowLoader";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import { useToast } from "../../components/ui/Toast";
import { fadeIn, fadeInUp, scaleUp, staggerContainer, tabTransition } from "../../lib/animations";
import { useAuthSession } from "../../shared/hooks/useAuthSession";
import { useSSE } from "../../shared/hooks/useSSE";
import {
  submitAudit,
  fetchJobs as apiFetchJobs,
  fetchJobDetail as apiFetchJobDetail,
  cancelJob as apiCancelJob,
  fetchSystemStatus as apiFetchSystemStatus,
} from "../../features/audits/api";
import { Job, JobDetail, Finding, SystemStatus, Severity, JobStatus } from "../../features/audits/types";
import Sidebar, { Section } from "../../features/audits/components/Sidebar";
import MetricsRow from "../../features/audits/components/MetricsRow";
import AuditForm from "../../features/audits/components/AuditForm";
import JobList from "../../features/audits/components/JobList";
import PipelineViz from "../../features/audits/components/PipelineViz";
import LogStream from "../../features/audits/components/LogStream";
import FindingsList from "../../features/findings/components/FindingsList";
import { API_BASE_URL } from "../../shared/api/client";
import { ENDPOINTS } from "../../shared/api/endpoints";
import { formatDateTime, shortRepoName } from "../../shared/utils/format";
import mobile from "./mobile.module.css";
import styles from "./page.module.css";

const TERMINAL_STATUSES: JobStatus[] = ["completed", "failed", "cancelled", "partial"];
const TABS: Section[] = ["home", "audits", "findings", "reports", "settings"];
const SECTION_TITLES: Record<Section, string> = {
  home: "Overview",
  audits: "Audits",
  findings: "Findings",
  reports: "Reports",
  settings: "Settings",
};

function statusLabel(job: Job): "queued" | "running" | "completed" | "failed" | "cancelled" | "partial" | "cancelling" {
  if (job.cancel_requested && !TERMINAL_STATUSES.includes(job.status)) return "cancelling";
  return job.status;
}

function calculateRiskScore(findings: Finding[]): number | null {
  if (findings.length === 0) return null;
  const weights: Record<Severity, number> = { critical: 28, high: 18, medium: 9, low: 4, info: 0 };
  return Math.min(100, findings.reduce((score, finding) => score + weights[finding.severity], 0));
}

function postureLabel(score: number | null, activeJobs: number): string {
  if (activeJobs > 0) return "Audit running";
  if (score === null) return "Awaiting first audit";
  if (score >= 80) return "Critical attention";
  if (score >= 55) return "High risk";
  if (score >= 25) return "Needs review";
  return "Controlled";
}

function severityBreakdown(findings: Finding[]) {
  return findings.reduce<Record<Severity, number>>(
    (acc, finding) => {
      acc[finding.severity] += 1;
      return acc;
    },
    { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
  );
}

export default function Dashboard() {
  const router = useRouter();
  const { toast } = useToast();
  const authSession = useAuthSession();
  const validateSession = authSession.validateSession;

  const [activeSection, setActiveSection] = useState<Section>("home");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJobDetail, setSelectedJobDetail] = useState<JobDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [systemError, setSystemError] = useState("");
  const [loadingSystem, setLoadingSystem] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const touchStartXRef = useRef<number | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const isAuthenticated = authSession.hasDashboardSession;

  useEffect(() => {
    let active = true;

    async function bootstrapSession() {
      const valid = await validateSession();
      if (!active) {
        return;
      }
      if (!valid) {
        router.replace("/signin");
        return;
      }
      setAuthReady(true);
    }

    void bootstrapSession();

    return () => {
      active = false;
    };
  }, [router, validateSession]);

  const fetchJobs = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoadingJobs(true);
    try {
      const data = await apiFetchJobs();
      setJobs(data);
      setSelectedJobId((current) => current || data[0]?.id || null);
    } catch (error) {
      // apiClient handles unauthorized redirect automatically
      console.error("Failed to fetch jobs:", error);
    } finally {
      setLoadingJobs(false);
    }
  }, [isAuthenticated]);

  const fetchJobDetail = useCallback(
    async (jobId: string) => {
      if (!isAuthenticated) return;
      setLoadingDetail(true);
      try {
        const detail = await apiFetchJobDetail(jobId);
        setSelectedJobDetail(detail);
      } catch (error) {
        console.error("Failed to fetch job detail:", error);
      } finally {
        setLoadingDetail(false);
      }
    },
    [isAuthenticated],
  );

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) || selectedJobDetail?.job || null,
    [jobs, selectedJobDetail, selectedJobId],
  );

  // Use hook-based SSE logs
  const { logs, streamActive, startLogStream, stopLogStream } = useSSE({
    authenticated: isAuthenticated,
    token: authSession.token,
    onJobStatusChange: useCallback(() => {
      void fetchJobs();
      if (selectedJobId) void fetchJobDetail(selectedJobId);
    }, [fetchJobs, fetchJobDetail, selectedJobId]),
  });

  useEffect(() => {
    if (!isAuthenticated || !selectedJobId || activeSection !== "audits") {
      stopLogStream();
      return;
    }

    void startLogStream(selectedJobId);
    return stopLogStream;
  }, [activeSection, isAuthenticated, selectedJobId, startLogStream, stopLogStream]);

  const findings = selectedJobDetail?.findings || [];
  const activeJobs = jobs.filter((job) => job.status === "queued" || job.status === "running").length;
  const criticalFindings = findings.filter((finding) => finding.severity === "critical").length;
  const highFindings = findings.filter((finding) => finding.severity === "high").length;
  const latestReportJob = jobs.find((job) => job.report_pdf_url) || null;
  const latestReport = latestReportJob?.report_pdf_url || null;
  const reportJobs = jobs.filter((job) => TERMINAL_STATUSES.includes(job.status));
  const riskScore = calculateRiskScore(findings);
  const posture = postureLabel(riskScore, activeJobs);
  const severityCounts = severityBreakdown(findings);
  const recentJobs = jobs.slice(0, 4);

  const fetchSystemStatus = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoadingSystem(true);
    setSystemError("");
    try {
      const status = await apiFetchSystemStatus();
      setSystemStatus(status);
    } catch (error) {
      const err = error as { message?: string };
      setSystemError(err.message || "System status endpoint is unavailable.");
    } finally {
      setLoadingSystem(false);
    }
  }, [isAuthenticated]);

  const openReport = useCallback(
    async (jobId: string) => {
      if (!isAuthenticated) return;
      setReportError(null);
      toast("Retrieving report PDF...", "info");
      try {
        // Binary fetch bypasses request JSON parser
        const headers = authSession.token ? { Authorization: `Bearer ${authSession.token}` } : undefined;
        const response = await fetch(`${API_BASE_URL}${ENDPOINTS.audit.report(jobId)}`, {
          credentials: "include",
          headers,
        });
        if (!response.ok) {
          const errorBody = await response.json().catch(() => null);
          throw new Error(errorBody?.detail || "Unable to open this report.");
        }
        const blob = await response.blob();
        const reportUrl = window.URL.createObjectURL(blob);
        window.open(reportUrl, "_blank", "noopener,noreferrer");
        window.setTimeout(() => window.URL.revokeObjectURL(reportUrl), 60_000);
        toast("Report opened successfully.", "success");
      } catch (error) {
        const err = error as { message?: string };
        const msg = err.message || "Unable to open this report.";
        setReportError(msg);
        toast(msg, "error");
      }
    },
    [authSession.token, isAuthenticated, toast],
  );

    const handleLaunchScan = async (repoUrl: string, repoBranch: string) => {
    const job = await runAudit({ repo_url: repoUrl, repo_branch: repoBranch });
    if (job) {
      router.push(`/dashboard/audits/${job.id}`);
    }
  };
      const msg = err.message || "Unable to launch audit.";
      setSubmitError(msg);
      toast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const cancelScan = async (jobId: string) => {
    if (!isAuthenticated) return;
    toast("Requesting job cancellation...", "info");
    try {
      await apiCancelJob(jobId);
      await fetchJobs();
      await fetchJobDetail(jobId);
      toast("Cancellation request transmitted.", "success");
    } catch (error) {
      const err = error as { message?: string };
      toast(err.message || "Unable to cancel job.", "error");
    }
  };

  const handleSignOut = () => {
    toast("Signing out...", "info");
    authSession.logout();
    router.push("/signin");
  };

  useEffect(() => {
    if (isAuthenticated) {
      const timer = setTimeout(() => {
        void fetchJobs();
        void fetchSystemStatus();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [fetchJobs, fetchSystemStatus, isAuthenticated]);

  useEffect(() => {
    if (selectedJobId && isAuthenticated) {
      const timer = setTimeout(() => {
        void fetchJobDetail(selectedJobId);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [fetchJobDetail, isAuthenticated, selectedJobId]);

  useEffect(() => {
    if (typeof window === "undefined" || !isAuthenticated) return;
    const urlParams = new URLSearchParams(window.location.search);
    const queryJobId = urlParams.get("job_id");
    if (queryJobId) {
      const timer = setTimeout(() => {
        setSelectedJobId(queryJobId);
        setActiveSection("reports");
        void openReport(queryJobId);
      }, 0);
      // Clean up the URL to prevent double opening on refresh
      const url = new URL(window.location.href);
      url.searchParams.delete("job_id");
      window.history.replaceState({}, "", url.toString());
      return () => clearTimeout(timer);
    }
  }, [isAuthenticated, openReport]);

  useEffect(() => {
    if (!selectedJob || !isAuthenticated || (selectedJob.status !== "queued" && selectedJob.status !== "running")) return;
    const interval = window.setInterval(() => {
      void fetchJobs();
      void fetchJobDetail(selectedJob.id);
    }, 3500);
    return () => window.clearInterval(interval);
  }, [fetchJobDetail, fetchJobs, isAuthenticated, selectedJob]);

  const onTouchStart = (event: React.TouchEvent) => { touchStartXRef.current = event.touches[0].clientX; };
  const onTouchEnd = (event: React.TouchEvent) => {
    if (touchStartXRef.current === null) return;
    const diffX = touchStartXRef.current - event.changedTouches[0].clientX;
    const currentTabIndex = TABS.indexOf(activeSection);
    if (Math.abs(diffX) > 72 && diffX > 0 && currentTabIndex < TABS.length - 1) setActiveSection(TABS[currentTabIndex + 1]);
    if (Math.abs(diffX) > 72 && diffX < 0 && currentTabIndex > 0) setActiveSection(TABS[currentTabIndex - 1]);
    touchStartXRef.current = null;
  };

  // If the session isn't loaded yet
  if (!authReady) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <FireCrowLoader size="lg" />
          <div className="section-kicker">Session</div>
          <h1>Opening Fire Crow console</h1>
          <p>Checking for an authenticated workspace session.</p>
        </section>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <div className="auth-glow-orb auth-glow-orb-1" style={{ opacity: 0.15 }} />
      <div className="auth-glow-orb auth-glow-orb-2" style={{ opacity: 0.15 }} />
      <Sidebar activeSection={activeSection} setActiveSection={setActiveSection} username={authSession.workspace || ""} userId={authSession.userId || ""} />

      <motion.section variants={fadeIn} initial="hidden" animate="visible" className={styles.mainSurface} onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
        <header className={styles.topbar}>
          <div>
            <div className={styles.sectionKicker}>Fire Crow workspace</div>
            <h1>{SECTION_TITLES[activeSection]}</h1>
          </div>
          <div className={styles.workspaceSession}>
            <User size={13} className={styles.sessionIcon} />
            <div className={styles.sessionMeta}>
              <strong>{authSession.workspace}</strong>
              <span>Signed in</span>
            </div>
            <Button variant="ghost" size="sm" onClick={handleSignOut} style={{ minHeight: "32px", fontSize: "11px", padding: "0 8px" }}><LogOut size={12} />Sign out</Button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          {activeSection === "home" && (
            <motion.div key="home" initial="hidden" animate="visible" exit="exit" variants={staggerContainer}>
              <motion.div variants={fadeInUp}><MetricsRow activeAudits={activeJobs} totalJobs={jobs.length} criticalFindings={criticalFindings} latestReport={latestReport} /></motion.div>
              <div className={mobile.homeGrid}>
                <div className={mobile.homePrimary}>
                  <motion.div variants={scaleUp}>
                    <Card variant="surface" className={`${styles.panel} ${mobile.overviewCard}`}>
                      <div className={styles.panelHeader}>
                        <div>
                          <div className={styles.sectionKicker}>Current view</div>
                          <h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit selected"}</h2>
                        </div>
                        {selectedJob ? <Badge variant="status" type={statusLabel(selectedJob)}>{statusLabel(selectedJob)}</Badge> : <ShieldCheck size={18} className={styles.metricIcon} />}
                      </div>
                      <p className={mobile.panelCopy}>
                        {selectedJob
                          ? `Reviewing branch ${selectedJob.repo_branch}. Status and findings below reflect the selected audit only.`
                          : "Pick an audit to see its findings, report state, and current posture in one place."}
                      </p>
                      <div className={mobile.overviewStats}>
                        <div className={mobile.overviewStat}>
                          <span>Posture</span>
                          <strong>{posture}</strong>
                        </div>
                        <div className={mobile.overviewStat}>
                          <span>Risk score</span>
                          <strong>{riskScore === null ? "—" : `${riskScore}/100`}</strong>
                        </div>
                        <div className={mobile.overviewStat}>
                          <span>Critical</span>
                          <strong>{severityCounts.critical}</strong>
                        </div>
                      </div>
                      <div className={mobile.severityStrip} aria-label="Finding severity breakdown">
                        <span>Critical {severityCounts.critical}</span>
                        <span>High {severityCounts.high}</span>
                        <span>Medium {severityCounts.medium}</span>
                        <span>Low {severityCounts.low}</span>
                      </div>
                      <div className={mobile.quickActionGrid}>
                        <Button type="button" variant="primary" onClick={() => setActiveSection("audits")}><PlusCircle size={14} />New audit</Button>
                        <Button type="button" variant="ghost" disabled={!selectedJob || submitting} onClick={() => selectedJob && handleLaunchScan(selectedJob.repo_url, selectedJob.repo_branch)}><Play size={14} />Re-run</Button>
                        <Button type="button" variant="ghost" onClick={() => setActiveSection("findings")}><Search size={14} />Findings</Button>
                        <Button type="button" variant="ghost" disabled={!latestReportJob} onClick={() => latestReportJob && openReport(latestReportJob.id)}><Download size={14} />Report</Button>
                      </div>
                    </Card>
                  </motion.div>
                  <motion.div variants={scaleUp}>
                    <Card variant="surface" className={styles.panel}>
                      <div className={styles.panelHeader}>
                        <div>
                          <div className={styles.sectionKicker}>Latest audit</div>
                          <h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit yet"}</h2>
                        </div>
                        {selectedJob && <Badge variant="status" type={statusLabel(selectedJob)}>{statusLabel(selectedJob)}</Badge>}
                      </div>
                      <div className={mobile.auditMetaList}>
                        <div className={mobile.auditMetaRow}>
                          <span>Branch</span>
                          <strong>{selectedJob?.repo_branch || "—"}</strong>
                        </div>
                        <div className={mobile.auditMetaRow}>
                          <span>Created</span>
                          <strong>{selectedJob ? formatDateTime(selectedJob.created_at) : "—"}</strong>
                        </div>
                        <div className={mobile.auditMetaRow}>
                          <span>Report</span>
                          <strong>{selectedJob?.report_pdf_url ? "Available" : "Pending"}</strong>
                        </div>
                      </div>
                    </Card>
                  </motion.div>
                </div>
                <div className={mobile.homeSidebar}>
                  <motion.div variants={scaleUp}>
                    <Card variant="surface" className={styles.panel}>
                      <div className={styles.panelHeader}>
                        <div>
                          <div className={styles.sectionKicker}>System</div>
                          <h2>{systemStatus?.api || "Checking"}</h2>
                        </div>
                        <Button variant="ghost" size="sm" onClick={fetchSystemStatus} disabled={loadingSystem}><RefreshCw className={loadingSystem ? styles.spin : ""} size={12} />Refresh</Button>
                      </div>
                      {systemError && <div className={styles.noticeError}>{systemError}</div>}
                      <div className={mobile.statusStrip}>
                        <span><Globe size={13} /> API {systemStatus?.api || "checking"}</span>
                        <span><Database size={13} /> DB {systemStatus?.database || "checking"}</span>
                        <span><HardDrive size={13} /> {systemStatus?.sandbox_mode || "sandbox"}</span>
                      </div>
                    </Card>
                  </motion.div>
                  <motion.div variants={scaleUp}>
                    <Card variant="surface" className={styles.panel}>
                      <div className={styles.panelHeader}>
                        <div>
                          <div className={styles.sectionKicker}>Recent activity</div>
                          <h2>Latest runs</h2>
                        </div>
                      </div>
                      <div className={mobile.timelineList}>
                        {recentJobs.map((job) => (
                          <button
                            key={job.id}
                            type="button"
                            className={mobile.timelineItem}
                            onClick={() => {
                              setSelectedJobId(job.id);
                              setActiveSection("audits");
                              void fetchJobDetail(job.id);
                            }}
                          >
                            <span>{formatDateTime(job.created_at)}</span>
                            <strong>{shortRepoName(job.repo_url)}</strong>
                            <Badge variant="status" type={statusLabel(job)}>{statusLabel(job)}</Badge>
                          </button>
                        ))}
                        {jobs.length === 0 && <div className={styles.emptyState}>No audit activity is available yet.</div>}
                      </div>
                    </Card>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          )}

          {activeSection === "audits" && (
            <motion.div key="audits" initial="hidden" animate="visible" exit="exit" variants={staggerContainer}>
              <div className={styles.workGrid}><motion.div variants={scaleUp}><AuditForm onSubmit={handleLaunchScan} submitting={submitting} submitError={submitError} /></motion.div><motion.div variants={scaleUp}><JobList jobs={jobs} selectedJobId={selectedJobId} loadingJobs={loadingJobs} onRefresh={fetchJobs} onJobSelect={(jobId) => { setSelectedJobId(jobId); void fetchJobDetail(jobId); }} /></motion.div></div>
              <div className={styles.detailGrid}><motion.div variants={scaleUp}><PipelineViz job={selectedJob} onOpenReport={openReport} onCancel={cancelScan} reportError={reportError} /></motion.div><motion.div variants={scaleUp}><Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Status</div><h2>{selectedJob ? statusLabel(selectedJob) : "No audit selected"}</h2></div><Badge variant="status" type={streamActive ? "running" : selectedJob ? statusLabel(selectedJob) : "queued"}>{streamActive ? "live logs" : selectedJob ? statusLabel(selectedJob) : "idle"}</Badge></div><p className={mobile.panelCopy}>{selectedJob ? "The selected audit controls the summary, report action, and log panel below." : "Choose an audit from the list to inspect its saved state."}</p></Card></motion.div></div>
              <motion.div variants={scaleUp}><LogStream logs={logs} streamActive={streamActive} hasSelection={Boolean(selectedJobId)} /></motion.div>
            </motion.div>
          )}

          {activeSection === "findings" && (
            <motion.div key="findings" initial="hidden" animate="visible" exit="exit" variants={tabTransition} className={styles.sectionBody}>
              <div className={mobile.findingsHeroGrid}><Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Selected Audit</div><h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit selected"}</h2></div>{selectedJob && <Badge variant="status" type={statusLabel(selectedJob)}>{statusLabel(selectedJob)}</Badge>}</div><p className={mobile.panelCopy}>{selectedJob ? `Showing findings returned for branch ${selectedJob.repo_branch}. Select another audit from the Audits tab to inspect its details.` : "Start or select an audit to review evidence-backed findings."}</p></Card><Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Critical / High</div><h2>{criticalFindings + highFindings}</h2></div><AlertTriangle size={18} className={styles.metricIcon} /></div><p className={mobile.panelCopy}>Severity labels are shown in text and color; color is never the only signal.</p></Card></div>
              <FindingsList findings={findings} loading={loadingDetail} />
            </motion.div>
          )}

          {activeSection === "reports" && (
            <motion.div key="reports" initial="hidden" animate="visible" exit="exit" variants={tabTransition} className={styles.sectionBody}>
              <Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Reports</div><h2>Audit reports</h2></div><Button variant="ghost" size="sm" onClick={fetchJobs} disabled={!authSession.token || loadingJobs}><RefreshCw className={loadingJobs ? styles.spin : ""} size={12} />Refresh</Button></div><div className={styles.reportList}>{reportError && <div className={styles.noticeError}>{reportError}</div>}{!authSession.token ? <div className={styles.emptyState}>Connect a workspace to view reports.</div> : reportJobs.length === 0 ? <div className={styles.emptyState}>No audit reports are available yet. Start an authorized audit to generate your first report.</div> : reportJobs.map((job) => <motion.article whileHover={{ scale: 1.01 }} className={styles.reportRow} key={job.id}><div><Badge variant="status" type={statusLabel(job)}>{statusLabel(job)}</Badge><h3>{shortRepoName(job.repo_url)}</h3><p>Branch {job.repo_branch} / finished {formatDateTime(job.finished_at)}</p></div>{job.report_pdf_url ? <Button variant="ghost" size="sm" onClick={() => openReport(job.id)}><FileText size={14} />Open report</Button> : <span className={styles.reportMissing}>No PDF artifact</span>}</motion.article>)}</div></Card>
            </motion.div>
          )}

          {activeSection === "settings" && (
            <motion.div key="settings" initial="hidden" animate="visible" exit="exit" variants={tabTransition} className={styles.sectionBody}>
              <Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Settings</div><h2>Workspace settings</h2></div><Button variant="ghost" size="sm" onClick={fetchSystemStatus} disabled={loadingSystem}><RefreshCw className={loadingSystem ? styles.spin : ""} size={12} />Refresh</Button></div>{systemError && <div className={styles.noticeError}>{systemError}</div>}<div className={styles.settingsGrid}><StatusCard label="API" value={systemStatus?.api || "checking"} tone={systemStatus?.api === "online" ? "good" : "warn"} icon={<Globe size={14} />} /><StatusCard label="Database" value={systemStatus?.database || "checking"} tone={systemStatus?.database === "connected" ? "good" : "warn"} icon={<Database size={14} />} /><StatusCard label="Sandbox" value={systemStatus?.sandbox_mode === "docker" ? "Docker/Kali" : "Simulation"} tone="warn" icon={<HardDrive size={14} />} /><StatusCard label="Workspace" value={authSession.workspace || "Not connected"} tone={authSession.workspace ? "good" : "warn"} icon={<Fingerprint size={14} />} /></div><div className={styles.integrationList}>{Object.entries(systemStatus?.integrations || {}).map(([name, enabled]) => <motion.div whileHover={{ x: 2 }} className={styles.integrationRow} key={name}><span>{name.replaceAll("_", " ")}</span><strong className={enabled ? styles.integrationOn : styles.integrationOff}>{enabled ? "configured" : "not configured"}</strong></motion.div>)}<div className={styles.integrationRow}><span>PWA offline policy</span><strong className={styles.integrationOn}>private API data not cached</strong></div><div className={styles.integrationRow}><span>Install help</span><strong className={styles.integrationOn}>use browser install prompt when available</strong></div>{!systemStatus && !systemError && <div className={styles.emptyState}>System status has not loaded yet.</div>}</div><div className={mobile.settingsActions}><Button type="button" variant="danger" onClick={handleSignOut}><LogOut size={14} />Logout</Button></div></Card>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.section>
    </main>
  );
}

function StatusCard({ label, value, tone, icon }: { label: string; value: string; tone: "good" | "warn"; icon?: React.ReactNode }) {
  const cardClass = [styles.statusCard, tone === "good" ? styles.statusCardGood : styles.statusCardWarn].join(" ");
  return <div className={cardClass}><div className={styles.statusCardHeader}><span>{label}</span>{icon}</div><strong>{value}</strong></div>;
}

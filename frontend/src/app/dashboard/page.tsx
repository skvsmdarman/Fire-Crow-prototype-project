"use client";

import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import { useAuthSession } from "../../shared/hooks/useAuthSession";
import { useSSE } from "../../shared/hooks/useSSE";
import useAudits from "../../features/audits/hooks";
import { apiClient } from "../../shared/api/client";
import { ENDPOINTS } from "../../shared/api/endpoints";
import dynamic from "next/dynamic";
import ChatWidget from "../../components/ChatWidget";
import Leaderboard from "../../components/Leaderboard";
import { subscribeUserToPush } from "../../lib/pushNotifications";
import styles from "./page.module.css";

import {
  useDashboardStatus,
  useSessionValidation,
  useAuditSubmission,
  useReportDownload,
} from "./hooks";

import {
  DashboardSidebar,
  OverviewSection,
  AuditLaunchPanel,
  AuditJobList,
  AuditJobDetail,
  FindingsPanel,
  ReportsPanel,
  SettingsPanel,
  PageHeader,
  theme,
} from "./components";

interface AuditInsightResponse {
  jobId: string;
  insight: string | null;
  enabled: boolean;
}

export default function Dashboard() {
  const router = useRouter();
  const authSession = useAuthSession();
  const isAuthenticated = authSession.hasDashboardSession;

  const { isValidating, isReconnecting } = useSessionValidation(router);

  const [active, setActive] = useState("Overview");
  const [jobInsight, setJobInsight] = useState<AuditInsightResponse | null>(null);
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");

  const {
    jobs,
    selectedJobId,
    setSelectedJobId,
    selectedJobDetail,
    runAudit,
    loadJobs,
    loadJobDetail,
  } = useAudits(isAuthenticated);

  const {
    systemStatus,
    runningCount,
    criticalCount,
    latestCompleted,
    fetchSystemStatus,
  } = useDashboardStatus(jobs, selectedJobDetail?.findings || []);

  const {
    newUrl,
    setNewUrl,
    newBranch,
    setNewBranch,
    attestationAccepted,
    setAttestationAccepted,
    authorizationScope,
    setAuthorizationScope,
    submitting,
    handleStartAudit,
  } = useAuditSubmission(runAudit);

  const {
    downloadingId,
    downloadReport,
  } = useReportDownload();

  useEffect(() => {
    if (isAuthenticated) {
      void subscribeUserToPush();
    }
  }, [isAuthenticated]);

  const selectedJob = jobs.find((j) => j.id === selectedJobId) || null;
  const findings = selectedJobDetail?.findings || [];

  const { logs, streamActive, startLogStream, stopLogStream } = useSSE({
    authenticated: isAuthenticated,
    onJobStatusChange: () => {
      void loadJobs();
      if (selectedJobId) void loadJobDetail(selectedJobId);
    },
  });

  useEffect(() => {
    if (selectedJob?.id) {
      void startLogStream(selectedJob.id);
    } else {
      stopLogStream();
    }
  }, [selectedJob?.id, startLogStream, stopLogStream]);

  const isLlmFeatureEnabled = (feature: "chat_assistant" | "dashboard_insight") => {
    if (!systemStatus) return false;
    const feats = systemStatus.llm_features;
    if (typeof feats === "object" && feats !== null) {
      return !!feats[feature];
    }
    return false;
  };

  useEffect(() => {
    let cancelled = false;

    const showInsight = isLlmFeatureEnabled("dashboard_insight");

    if (!selectedJobId || !isAuthenticated || !showInsight) {
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
  }, [isAuthenticated, selectedJobId, systemStatus]);

  // Update job details periodically when running
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

  const completedJobs = jobs.filter((j) => j.status === "completed" || j.status === "partial");
  const selectedJobInsight =
    isLlmFeatureEnabled("dashboard_insight") && jobInsight?.jobId === selectedJobId
      ? jobInsight
      : null;

  const filteredFindings = filter === "all" ? findings : findings.filter((f) => f.severity === filter);

  if (!isAuthenticated || isValidating) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#0d0d0d" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }} style={{ width: 32, height: 32, border: "2px solid #333", borderTopColor: theme.orange, borderRadius: "50%" }} />
          <div className="mono" style={{ fontSize: 11, color: theme.muted, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            Validating session...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.shell}>
      {/* Sidebar */}
      <DashboardSidebar
        active={active}
        setActive={setActive}
        workspace={authSession.workspace}
        userId={authSession.userId}
        onSignOut={handleSignOut}
      />

      {/* Main Area */}
      <main className={styles.mainSurface}>
        {isReconnecting && (
          <div
            style={{
              background: "rgba(255, 184, 0, 0.08)",
              borderBottom: "1px solid rgba(255, 184, 0, 0.18)",
              padding: "10px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              color: "var(--amber)",
              fontSize: 11,
              fontWeight: 500,
              width: "100%",
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "var(--amber)",
                marginRight: 4,
                animation: "pulse 1.6s ease-in-out infinite",
              }}
            />
            Coordination server offline. Operating in read-only mode. Reconnecting...
          </div>
        )}

        <AnimatePresence mode="wait">
          <motion.div
            key={active}
            initial={{ opacity: 0, scale: 0.98, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: -10 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            {active === "Overview" && (
              <OverviewSection
                jobs={jobs}
                findings={findings}
                criticalCount={criticalCount}
                setActive={setActive}
              />
            )}
            {active === "Audits" && (
              <div>
                <PageHeader kicker="Security Auditing" title="Audits" />
                <div className={styles.sectionBody}>
                  <div>
                    <AuditLaunchPanel
                      newUrl={newUrl}
                      setNewUrl={setNewUrl}
                      newBranch={newBranch}
                      setNewBranch={setNewBranch}
                      attestationAccepted={attestationAccepted}
                      setAttestationAccepted={setAttestationAccepted}
                      authorizationScope={authorizationScope}
                      setAuthorizationScope={setAuthorizationScope}
                      submitting={submitting}
                      onSubmit={handleStartAudit}
                    />
                    <AuditJobList
                      jobs={jobs}
                      selectedId={selectedJobId}
                      onSelect={setSelectedJobId}
                    />
                  </div>
                  {selectedJob && (
                    <AuditJobDetail
                      selected={selectedJob}
                      insight={selectedJobInsight}
                      downloadReport={downloadReport}
                      downloadingId={downloadingId}
                      streamActive={streamActive}
                      logs={logs}
                    />
                  )}
                </div>
              </div>
            )}
            {active === "Findings" && (
              <FindingsPanel
                findings={filteredFindings}
                all={findings}
                filter={filter}
                setFilter={setFilter}
                expanded={expandedFinding}
                setExpanded={setExpandedFinding}
                selected={selectedJob}
              />
            )}
            {active === "Reports" && (
              <ReportsPanel
                jobs={completedJobs}
                downloadReport={downloadReport}
                downloadingId={downloadingId}
              />
            )}
            {active === "Leaderboard" && (
              <div>
                <PageHeader kicker="Workspace Security" title="Leaderboard" />
                <div style={{ padding: "24px 32px", maxWidth: 800 }}>
                  <Leaderboard />
                </div>
              </div>
            )}
            {active === "Settings" && <SettingsPanel systemStatus={systemStatus} />}
          </motion.div>
        </AnimatePresence>
      </main>

      {isLlmFeatureEnabled("chat_assistant") ? (
        <ChatWidget jobId={selectedJobId} />
      ) : null}
    </div>
  );
}

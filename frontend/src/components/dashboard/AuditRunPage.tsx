"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { buildApiUrl } from "../../lib/base-url";
import { formatRelativeDate, formatRepoName, severityRank } from "../../lib/format";
import { ApiError, request } from "../../lib/request";
import { AuditInsightResponse, ChatResponse, JobDetailResponse } from "../../lib/types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { SiteHeader } from "../SiteChrome";

async function readStream(jobId: string, onLine: (line: string) => void, signal: AbortSignal) {
  const response = await fetch(buildApiUrl(`/audit/${jobId}/stream`), {
    credentials: "include",
    signal,
  });
  if (!response.ok || !response.body) {
    throw new ApiError("Stream unavailable.", response.status);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    onLine(decoder.decode(value, { stream: true }));
  }
}

export function AuditRunPage({ jobId }: { jobId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resolvedJobId = useMemo(() => searchParams.get("jobId") ?? jobId, [jobId, searchParams]);
  const hasExplicitJob = useMemo(() => Boolean(searchParams.get("jobId")) || jobId !== "default", [jobId, searchParams]);
  const [detail, setDetail] = useState<JobDetailResponse | null>(null);
  const [graph, setGraph] = useState<unknown>(null);
  const [insight, setInsight] = useState<AuditInsightResponse | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<Array<{ role: "user" | "assistant"; text: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [chatBusy, setChatBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    const [jobDetail, jobInsight] = await Promise.all([
      request<JobDetailResponse>(`/audit/job/${resolvedJobId}`),
      request<AuditInsightResponse>(`/audit/job/${resolvedJobId}/insight`).catch(() => null),
    ]);
    setDetail(jobDetail);
    setInsight(jobInsight);
    try {
      setGraph(await request<unknown>(`/audit/job/${resolvedJobId}/graph`));
    } catch {
      setGraph(null);
    }
  }, [resolvedJobId]);

  useEffect(() => {
    if (!hasExplicitJob) {
      setLoading(false);
      setDetail(null);
      return;
    }
    let cancelled = false;
    void loadAll()
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load audit.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [hasExplicitJob, loadAll]);

  useEffect(() => {
    if (!hasExplicitJob || !detail || !["queued", "running"].includes(detail.job.status)) {
      return;
    }
    const controller = new AbortController();
    setLogs([]);
    void readStream(
      resolvedJobId,
      (chunk) => {
        setLogs((current) => [...current.slice(-80), chunk]);
      },
      controller.signal,
    ).catch(() => undefined);
    return () => controller.abort();
  }, [detail, hasExplicitJob, resolvedJobId]);

  async function handleChat() {
    if (!chatInput.trim() || !hasExplicitJob) {
      return;
    }
    const message = chatInput.trim();
    setChatMessages((current) => [...current, { role: "user", text: message }]);
    setChatInput("");
    setChatBusy(true);
    try {
      const response = await request<ChatResponse>("/chat/ask", {
        method: "POST",
        body: { job_id: resolvedJobId, message },
      });
      setChatMessages((current) => [...current, { role: "assistant", text: response.answer ?? response.response ?? "No response." }]);
    } catch (err) {
      setChatMessages((current) => [...current, { role: "assistant", text: err instanceof Error ? err.message : "Chat failed." }]);
    } finally {
      setChatBusy(false);
    }
  }

  const findings = [...(detail?.findings ?? [])].sort((left, right) => severityRank(right.severity) - severityRank(left.severity));

  return (
    <div className="fc-page">
      <SiteHeader ctaHref="/dashboard" ctaLabel="Back to dashboard" />
      <main className="fc-shell fc-dashboard-shell">
        <div className="fc-dashboard-main">
          {error ? <div className="fc-form-error">{error}</div> : null}
          {loading ? (
            <Card className="fc-panel">
              <div className="fc-panel-title">Loading audit view...</div>
            </Card>
          ) : null}
          {detail ? (
            <>
              <Card className="fc-panel">
                <div className="fc-panel-head">
                  <div>
                    <div className="fc-kicker">Audit focus</div>
                    <h1 className="fc-title-md">{formatRepoName(detail.job.repo_url)}</h1>
                  </div>
                  <div className="fc-chip-row">
                    <Badge tone={detail.job.status === "completed" ? "success" : detail.job.status === "failed" ? "critical" : "warning"}>
                      {detail.job.status}
                    </Badge>
                    <Button variant="secondary" onClick={() => window.open(buildApiUrl(`/audit/job/${resolvedJobId}/report`), "_blank", "noopener,noreferrer")}>
                      Open report
                    </Button>
                  </div>
                </div>
                <div className="fc-grid-3">
                  <Card className="fc-metric">
                    <div className="fc-muted">Created</div>
                    <span className="fc-metric-value">{formatRelativeDate(detail.job.created_at)}</span>
                  </Card>
                  <Card className="fc-metric">
                    <div className="fc-muted">Finished</div>
                    <span className="fc-metric-value">{formatRelativeDate(detail.job.finished_at)}</span>
                  </Card>
                  <Card className="fc-metric">
                    <div className="fc-muted">Findings</div>
                    <span className="fc-metric-value">{findings.length}</span>
                  </Card>
                </div>
              </Card>

              <div className="fc-grid-2">
                <Card className="fc-panel">
                  <div className="fc-panel-head">
                    <div>
                      <div className="fc-kicker">Log stream</div>
                      <h2 className="fc-panel-title">Realtime output</h2>
                    </div>
                  </div>
                  <div className="fc-stream">
                    {logs.length ? logs.map((line, index) => <div className="fc-terminal-line" key={index}>{line}</div>) : "No live stream has been captured for this view yet."}
                  </div>
                </Card>
                <Card className="fc-panel">
                  <div className="fc-panel-head">
                    <div>
                      <div className="fc-kicker">Operator insight</div>
                      <h2 className="fc-panel-title">Summary + graph</h2>
                    </div>
                  </div>
                  <div className="fc-empty" style={{ marginBottom: 16 }}>
                    {insight?.enabled ? insight.insight : "Dashboard insight is disabled or not available for this audit."}
                  </div>
                  <pre className="fc-json">{graph ? JSON.stringify(graph, null, 2) : "Attack graph not available."}</pre>
                </Card>
              </div>

              <Card className="fc-panel">
                <div className="fc-panel-head">
                  <div>
                    <div className="fc-kicker">Findings</div>
                    <h2 className="fc-panel-title">Evidence-backed issues</h2>
                  </div>
                  <Link className="fc-button fc-button-secondary" href="/dashboard">
                    Return to dashboard
                  </Link>
                </div>
                {findings.length ? (
                  <div className="fc-findings">
                    {findings.map((finding) => (
                      <div className="fc-finding" key={finding.id}>
                        <div className="fc-finding-head">
                          <strong>{finding.title}</strong>
                          <Badge tone={finding.severity === "critical" ? "critical" : finding.severity === "high" ? "warning" : "info"}>
                            {finding.severity}
                          </Badge>
                        </div>
                        <div className="fc-copy" style={{ marginTop: 10 }}>{finding.description}</div>
                        {finding.evidence ? <div className="fc-copy" style={{ marginTop: 10 }}><strong>Evidence:</strong> {finding.evidence}</div> : null}
                        {finding.remediation ? <div className="fc-copy" style={{ marginTop: 10 }}><strong>Remediation:</strong> {finding.remediation}</div> : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="fc-empty">No findings were returned for this audit.</div>
                )}
              </Card>

              <Card className="fc-panel">
                <div className="fc-panel-head">
                  <div>
                    <div className="fc-kicker">Chat assistant</div>
                    <h2 className="fc-panel-title">Ask about this run</h2>
                  </div>
                  <Button variant="ghost" onClick={() => router.push("/dashboard")}>
                    Dashboard
                  </Button>
                </div>
                <div className="fc-findings" style={{ maxHeight: 220 }}>
                  {chatMessages.length ? chatMessages.map((message, index) => (
                    <div className="fc-finding" key={`${message.role}-${index}`}>
                      <div className="fc-muted">{message.role === "assistant" ? "Assistant" : "You"}</div>
                      <div className="fc-copy" style={{ marginTop: 8 }}>{message.text}</div>
                    </div>
                  )) : <div className="fc-empty">Use the assistant to ask for a summary or next-step recommendations.</div>}
                </div>
                <div className="fc-inline-fields" style={{ marginTop: 16 }}>
                  <Input value={chatInput} onChange={(event) => setChatInput(event.target.value)} placeholder="Summarize the attack path or explain the evidence." />
                  <Button onClick={handleChat} loading={chatBusy}>Ask</Button>
                </div>
              </Card>
            </>
          ) : !loading ? (
            <Card className="fc-panel">
              <div className="fc-empty">Open this page from the dashboard to inspect a specific audit run.</div>
            </Card>
          ) : null}
        </div>
      </main>
    </div>
  );
}

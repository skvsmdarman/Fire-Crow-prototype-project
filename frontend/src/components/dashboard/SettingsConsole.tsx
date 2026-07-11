"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { request } from "../../lib/request";
import { enablePushNotifications } from "../../lib/push";
import { AuthUser, SystemStatus, DomainVerificationRecord, VerificationMethod } from "../../lib/types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { SiteHeader } from "../SiteChrome";

export function SettingsConsole() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [domains, setDomains] = useState<DomainVerificationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pushMessage, setPushMessage] = useState<string | null>(null);

  const [newDomain, setNewDomain] = useState("");
  const [addingDomain, setAddingDomain] = useState(false);
  const [verifyingDomainId, setVerifyingDomainId] = useState<string | null>(null);
  const [selectedDomainMethod, setSelectedDomainMethod] = useState<Record<string, VerificationMethod>>({});
  const [activeInstructionsId, setActiveInstructionsId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      request<AuthUser>("/auth/me"),
      request<SystemStatus>("/system/status"),
      request<DomainVerificationRecord[]>("/verify/domains"),
    ])
      .then(([user, status, domainRecords]) => {
        if (!cancelled) {
          setAuthUser(user);
          setSystemStatus(status);
          setDomains(domainRecords);
          // Initialize methods for each domain
          const initialMethods: Record<string, VerificationMethod> = {};
          domainRecords.forEach((d) => {
            initialMethods[d.id] = "dns";
          });
          setSelectedDomainMethod(initialMethods);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load settings profile.");
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
  }, []);

  async function handlePushEnable() {
    try {
      const msg = await enablePushNotifications();
      setPushMessage(msg);
    } catch (err) {
      setPushMessage(err instanceof Error ? err.message : "Push registration failed.");
    }
  }

  async function handleAddDomain(e: React.FormEvent) {
    e.preventDefault();
    if (!newDomain.trim()) return;
    setAddingDomain(true);
    setError(null);
    setPushMessage(null);
    try {
      const added = await request<DomainVerificationRecord>("/verify/domain", {
        method: "POST",
        body: { domain: newDomain.trim() },
      });
      setDomains((prev) => [...prev, added]);
      setSelectedDomainMethod((prev) => ({ ...prev, [added.id]: "dns" }));
      setNewDomain("");
      setPushMessage(`Successfully registered domain ${added.domain}. Please complete verification below.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add domain.");
    } finally {
      setAddingDomain(false);
    }
  }

  async function handleVerifyDomain(domain: DomainVerificationRecord) {
    const method = selectedDomainMethod[domain.id] || "dns";
    setVerifyingDomainId(domain.id);
    setError(null);
    setPushMessage(null);
    try {
      const res = await request<{ verified: boolean; message: string }>("/verify/domain/check", {
        method: "POST",
        body: { domain: domain.domain, method },
      });
      if (res.verified) {
        setPushMessage(res.message);
        // Refresh domain list
        const updated = await request<DomainVerificationRecord[]>("/verify/domains");
        setDomains(updated);
        setActiveInstructionsId(null);
      } else {
        setError(res.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification request failed.");
    } finally {
      setVerifyingDomainId(null);
    }
  }

  async function handleDeleteDomain(id: string) {
    if (!confirm("Are you sure you want to remove this domain verification record?")) return;
    setError(null);
    setPushMessage(null);
    try {
      await request(`/verify/domain/${id}`, { method: "DELETE" });
      setDomains((prev) => prev.filter((d) => d.id !== id));
      setPushMessage("Domain verification record removed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete domain.");
    }
  }

  return (
    <div className="fc-page">
      <SiteHeader ctaHref="/dashboard" ctaLabel="Back to Dashboard" />
      <main className="fc-shell fc-dashboard-shell">
        <div className="fc-dashboard-grid">
          <Card className="fc-sidebar">
            <div>
              <div className="fc-kicker">Navigation</div>
              <h2 className="fc-panel-title" style={{ marginTop: 10 }}>Settings</h2>
              <div className="fc-copy" style={{ marginTop: 10 }}>
                Manage your workspace credentials, active connections, and check domain ownership verification.
              </div>
            </div>
            <div className="fc-sidebar-nav">
              <Link className="fc-sidebar-tab" href="/dashboard">Dashboard</Link>
              <Link className="fc-sidebar-tab" href="/dashboard/findings">Findings</Link>
              <Link className="fc-sidebar-tab" href="/dashboard/signals">Signals & AI</Link>
              <Link className="fc-sidebar-tab" href="/dashboard/settings" data-active="true">Settings</Link>
            </div>
          </Card>

          <div className="fc-dashboard-main">
            {error && <div className="fc-form-error">{error}</div>}
            {pushMessage && <div className="fc-form-success">{pushMessage}</div>}

            {loading ? (
              <Card className="fc-panel">
                <div className="fc-copy">Loading settings profile...</div>
              </Card>
            ) : (
              <>
                <div className="fc-grid-2">
                  <Card className="fc-panel">
                    <div className="fc-panel-head">
                      <div>
                        <div className="fc-kicker">Profile details</div>
                        <h3 className="fc-panel-title">Identity & Providers</h3>
                      </div>
                    </div>
                    <div className="fc-data-list" style={{ display: "grid", gap: 14 }}>
                      <div>
                        <div className="fc-muted" style={{ fontSize: "0.85rem", textTransform: "uppercase" }}>Workspace Name</div>
                        <strong style={{ fontSize: "1.1rem" }}>{authUser?.username ?? "N/A"}</strong>
                      </div>
                      <div>
                        <div className="fc-muted" style={{ fontSize: "0.85rem", textTransform: "uppercase" }}>Associated Email</div>
                        <strong>{authUser?.email ?? "Not provided"}</strong>
                      </div>
                      <div>
                        <div className="fc-muted" style={{ fontSize: "0.85rem", textTransform: "uppercase" }}>Policy Version</div>
                        <strong>{authUser?.privacy_policy_version ?? "N/A"}</strong>
                      </div>
                      <div style={{ marginTop: 10 }}>
                        <div className="fc-muted" style={{ fontSize: "0.85rem", textTransform: "uppercase", marginBottom: 8 }}>Linked Accounts</div>
                        <div className="fc-chip-row">
                          <Badge tone={authUser?.providers?.github?.connected ? "success" : "neutral"}>
                            GitHub {authUser?.providers?.github?.connected ? "Connected" : "Not connected"}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </Card>

                  <Card className="fc-panel">
                    <div className="fc-panel-head">
                      <div>
                        <div className="fc-kicker">Integrations</div>
                        <h3 className="fc-panel-title">Runtime Posture</h3>
                      </div>
                    </div>
                    <div className="fc-data-list" style={{ display: "grid", gap: 14 }}>
                      <div>
                        <div className="fc-muted" style={{ fontSize: "0.85rem", textTransform: "uppercase" }}>API Status</div>
                        <strong>{systemStatus?.api ?? "Offline"}</strong>
                      </div>
                      <div>
                        <div className="fc-muted" style={{ fontSize: "0.85rem", textTransform: "uppercase" }}>Database Status</div>
                        <strong>{systemStatus?.database ?? "Offline"}</strong>
                      </div>
                      <div>
                        <div className="fc-muted" style={{ fontSize: "0.85rem", textTransform: "uppercase" }}>Docker Sandbox</div>
                        <strong style={{ textTransform: "capitalize" }}>{systemStatus?.sandbox_mode ?? "N/A"}</strong>
                      </div>
                      <div style={{ marginTop: 10 }}>
                        <div className="fc-muted" style={{ fontSize: "0.85rem", textTransform: "uppercase", marginBottom: 8 }}>AI Subsystems</div>
                        <div className="fc-chip-row">
                          <Badge tone={systemStatus?.llm_features?.chat_assistant ? "success" : "neutral"}>Chat assistant</Badge>
                          <Badge tone={systemStatus?.llm_features?.dashboard_insight ? "success" : "neutral"}>Dashboard summary</Badge>
                          <Badge tone={systemStatus?.llm_features?.attack_chain_naming ? "success" : "neutral"}>Attack naming</Badge>
                        </div>
                      </div>
                      <div style={{ marginTop: 16 }}>
                        <Button variant="secondary" onClick={handlePushEnable} style={{ width: "100%" }}>
                          Register device for push notifications
                        </Button>
                      </div>
                    </div>
                  </Card>
                </div>

                <Card className="fc-panel" style={{ marginTop: 18 }}>
                  <div className="fc-panel-head">
                    <div>
                      <div className="fc-kicker">Live Scanning Target Verification</div>
                      <h3 className="fc-panel-title">Verified Domains</h3>
                    </div>
                  </div>
                  <div className="fc-copy" style={{ marginBottom: 20 }}>
                    To perform live external scans, you must verify ownership of the target domain. Choose one of the validation protocols below.
                  </div>

                  <form onSubmit={handleAddDomain} style={{ display: "flex", gap: 12, marginBottom: 24 }}>
                    <div style={{ flex: 1 }}>
                      <input
                        type="text"
                        placeholder="e.g., my-app.com"
                        value={newDomain}
                        onChange={(e) => setNewDomain(e.target.value)}
                        className="fc-input"
                        disabled={addingDomain}
                        required
                        style={{ height: 46 }}
                      />
                    </div>
                    <Button type="submit" disabled={addingDomain} variant="primary" style={{ minHeight: 46 }}>
                      {addingDomain ? "Registering..." : "Add Domain"}
                    </Button>
                  </form>

                  {domains.length === 0 ? (
                    <div className="fc-empty" style={{ textAlign: "center", padding: 32 }}>
                      No domains registered yet. Add a domain above to get started.
                    </div>
                  ) : (
                    <div style={{ display: "grid", gap: 16 }}>
                      {domains.map((dom) => {
                        const isVerified = dom.verified;
                        const method = selectedDomainMethod[dom.id] || "dns";
                        const showInstructions = activeInstructionsId === dom.id;

                        return (
                          <div
                            key={dom.id}
                            style={{
                              border: "1px solid var(--border)",
                              borderRadius: 16,
                              padding: 18,
                              background: "rgba(255, 255, 255, 0.02)",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
                              <div>
                                <span style={{ fontSize: "1.15rem", fontWeight: 600, marginRight: 12 }}>{dom.domain}</span>
                                <Badge tone={isVerified ? "success" : "warning"}>
                                  {isVerified ? "Verified" : "Pending Verification"}
                                </Badge>
                                {isVerified && dom.verified_at && (
                                  <div className="fc-muted" style={{ fontSize: "0.8rem", marginTop: 4 }}>
                                    Verified on: {new Date(dom.verified_at).toLocaleString()}
                                  </div>
                                )}
                              </div>
                              <div style={{ display: "flex", gap: 10 }}>
                                {!isVerified && (
                                  <Button
                                    variant="secondary"
                                    onClick={() => setActiveInstructionsId(showInstructions ? null : dom.id)}
                                    style={{ minHeight: 38, padding: "0 14px", fontSize: "0.9rem" }}
                                  >
                                    {showInstructions ? "Hide Setup" : "Setup Verification"}
                                  </Button>
                                )}
                                <Button
                                  variant="danger"
                                  onClick={() => handleDeleteDomain(dom.id)}
                                  style={{ minHeight: 38, padding: "0 14px", fontSize: "0.9rem" }}
                                >
                                  Delete
                                </Button>
                              </div>
                            </div>

                            {!isVerified && showInstructions && (
                              <div
                                style={{
                                  marginTop: 18,
                                  paddingTop: 18,
                                  borderTop: "1px solid rgba(255, 255, 255, 0.05)",
                                }}
                              >
                                <div className="fc-field" style={{ marginBottom: 16 }}>
                                  <label className="fc-field-label">Verification Protocol</label>
                                  <div style={{ display: "flex", gap: 10 }}>
                                    {(["dns", "html", "file"] as const).map((m) => (
                                      <button
                                        key={m}
                                        type="button"
                                        onClick={() =>
                                          setSelectedDomainMethod((prev) => ({ ...prev, [dom.id]: m }))
                                        }
                                        style={{
                                          flex: 1,
                                          height: 38,
                                          borderRadius: 10,
                                          border: "1px solid",
                                          borderColor: method === m ? "var(--fire-soft)" : "var(--border)",
                                          background: method === m ? "rgba(255, 107, 26, 0.1)" : "rgba(255, 255, 255, 0.02)",
                                          color: method === m ? "var(--text)" : "var(--text-dim)",
                                          cursor: "pointer",
                                          fontWeight: method === m ? 600 : 400,
                                          transition: "all 140ms ease",
                                        }}
                                      >
                                        {m.toUpperCase()}
                                      </button>
                                    ))}
                                  </div>
                                </div>

                                <div
                                  style={{
                                    padding: 16,
                                    borderRadius: 12,
                                    background: "rgba(0, 0, 0, 0.2)",
                                    border: "1px solid rgba(255, 255, 255, 0.03)",
                                    marginBottom: 16,
                                    fontSize: "0.9rem",
                                    lineHeight: 1.6,
                                  }}
                                >
                                  {method === "dns" && (
                                    <>
                                      <p style={{ margin: "0 0 10px" }}>
                                        Create a <strong>TXT record</strong> at your DNS provider:
                                      </p>
                                      <div style={{ display: "grid", gap: 8, fontFamily: "monospace", fontSize: "0.85rem" }}>
                                        <div>
                                          <span className="fc-muted">Host: </span>
                                          <span style={{ color: "var(--cyan)" }}>{dom.dns_txt_name}</span>
                                        </div>
                                        <div>
                                          <span className="fc-muted">Value: </span>
                                          <span style={{ color: "var(--fire-soft)" }}>{dom.dns_txt_value}</span>
                                        </div>
                                      </div>
                                    </>
                                  )}

                                  {method === "html" && (
                                    <>
                                      <p style={{ margin: "0 0 10px" }}>
                                        Insert the following <strong>meta tag</strong> inside the <code>&lt;head&gt;</code> of your website at <code>https://{dom.domain}</code>:
                                      </p>
                                      <pre
                                        style={{
                                          margin: 0,
                                          padding: 10,
                                          background: "rgba(0, 0, 0, 0.3)",
                                          borderRadius: 8,
                                          overflow: "auto",
                                          color: "var(--fire-soft)",
                                          fontSize: "0.85rem",
                                        }}
                                      >
                                        {`<meta name="${dom.html_meta_name}" content="${dom.html_meta_content}" />`}
                                      </pre>
                                    </>
                                  )}

                                  {method === "file" && (
                                    <>
                                      <p style={{ margin: "0 0 10px" }}>
                                        Upload a text file to your web server containing the challenge token:
                                      </p>
                                      <div style={{ display: "grid", gap: 8, fontFamily: "monospace", fontSize: "0.85rem" }}>
                                        <div>
                                          <span className="fc-muted">Path: </span>
                                          <span style={{ color: "var(--cyan)" }}>https://{dom.domain}{dom.well_known_path}</span>
                                        </div>
                                        <div>
                                          <span className="fc-muted">File Content: </span>
                                          <span style={{ color: "var(--fire-soft)" }}>{dom.well_known_content}</span>
                                        </div>
                                      </div>
                                    </>
                                  )}
                                </div>

                                <Button
                                  variant="primary"
                                  onClick={() => handleVerifyDomain(dom)}
                                  disabled={verifyingDomainId === dom.id}
                                  style={{ width: "100%", minHeight: 40 }}
                                >
                                  {verifyingDomainId === dom.id ? "Checking..." : "Check & Verify Domain"}
                                </Button>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Card>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

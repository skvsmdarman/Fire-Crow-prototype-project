"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { request } from "../../lib/request";
import { enablePushNotifications } from "../../lib/push";
import { AuthUser, SystemStatus } from "../../lib/types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { SiteHeader } from "../SiteChrome";

export function SettingsConsole() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pushMessage, setPushMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      request<AuthUser>("/auth/me"),
      request<SystemStatus>("/system/status"),
    ])
      .then(([user, status]) => {
        if (!cancelled) {
          setAuthUser(user);
          setSystemStatus(status);
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
                Manage your workspace credentials, active connections, and check background runtime integrations.
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
                        <Badge tone={authUser?.providers?.google?.connected ? "success" : "neutral"}>
                          Google {authUser?.providers?.google?.connected ? "Connected" : "Not connected"}
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
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

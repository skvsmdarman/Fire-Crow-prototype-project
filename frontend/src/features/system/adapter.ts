import { RawSystemStatus, SystemStatusViewModel, StatusValue } from "./types";

export function adaptSystemStatus(raw: RawSystemStatus | null | undefined): SystemStatusViewModel {
  if (!raw) {
    return {
      api: "unknown",
      database: "unknown",
      readiness: "unknown",
      debug: "unknown",
      sandbox_mode: "unknown",
      stats: "unknown",
      integrations: "unknown",
      llm_features: "unknown",
      agents: [],
      scanner_capabilities: "not_reported",
      github_permissions: "unknown"
    };
  }

  // Integrations mapping
  let integrationsVal: SystemStatusViewModel["integrations"] = "unknown";
  if (raw.integrations === undefined) {
    integrationsVal = "admin_only";
  } else if (raw.integrations) {
    const mapped: Record<string, StatusValue> = {};
    for (const [key, value] of Object.entries(raw.integrations)) {
      mapped[key] = value ? "configured" : "not_configured";
    }
    integrationsVal = mapped;
  }

  // Sandbox Mode mapping
  let sandboxModeVal: SystemStatusViewModel["sandbox_mode"] = "unknown";
  if (raw.sandbox_mode === undefined) {
    sandboxModeVal = "admin_only";
  } else {
    sandboxModeVal = raw.sandbox_mode;
  }

  // Debug mapping
  let debugVal: SystemStatusViewModel["debug"] = "unknown";
  if (raw.debug === undefined) {
    debugVal = "admin_only";
  } else {
    debugVal = raw.debug;
  }

  // Scanner capabilities mapping
  let scannerCapabilitiesVal: SystemStatusViewModel["scanner_capabilities"] = "not_reported";
  if (raw.scanner_capabilities) {
    scannerCapabilitiesVal = raw.scanner_capabilities;
  }

  // Github permissions mapping
  let githubPermissionsVal: SystemStatusViewModel["github_permissions"] = "unknown";
  if (raw.github_permissions) {
    githubPermissionsVal = {
      scopes: raw.github_permissions.scopes || [],
      descriptions: raw.github_permissions.descriptions || {}
    };
  } else if (raw.github_permissions === null || raw.github_permissions === undefined) {
    githubPermissionsVal = "unavailable";
  }

  let apiVal: SystemStatusViewModel["api"] = "unknown";
  if (raw.api === "online" || raw.api === "offline") {
    apiVal = raw.api;
  }

  let databaseVal: SystemStatusViewModel["database"] = "unknown";
  if (raw.database === "connected" || raw.database === "unavailable") {
    databaseVal = raw.database;
  }

  let readinessVal: SystemStatusViewModel["readiness"] = "unknown";
  if (raw.readiness === "ready" || raw.readiness === "degraded") {
    readinessVal = raw.readiness;
  }

  return {
    api: apiVal,
    database: databaseVal,
    readiness: readinessVal,
    debug: debugVal,
    sandbox_mode: sandboxModeVal,
    stats: raw.stats || "unknown",
    integrations: integrationsVal,
    llm_features: raw.llm_features || "unknown",
    agents: raw.agents || [],
    scanner_capabilities: scannerCapabilitiesVal,
    github_permissions: githubPermissionsVal
  };
}

export const privacySections = [
  {
    title: "Authorized-repository processing",
    body:
      "Fire Crow processes repository metadata, scan telemetry, findings, reports, and evidence only for repositories submitted by an authorized operator. Audit artifacts remain inside Neon PostgreSQL as structured text and JSON data.",
  },
  {
    title: "Retention model",
    body:
      "Reports, evidence, attack graphs, findings, and compliance events are persisted as database records. Large binary artifacts are generated on demand and are not stored long-term as the system of record.",
  },
  {
    title: "Regional handling",
    body:
      "Timezone and region metadata may be attached to authentication and legal acceptance flows so policy views and compliance logging can reflect the operator context recorded during sign-in or sign-up.",
  },
  {
    title: "Security posture",
    body:
      "Artifacts are stored encrypted at rest in the database through database-native and/or application-layer protections. Access to audit data is scoped through workspace membership and authenticated session checks.",
  },
];

export const termsSections = [
  {
    title: "Authorized use only",
    body:
      "You may submit only repositories and systems for which you have explicit authorization to perform security testing. By launching a run, you attest that you are an authorized representative or have delegated permission.",
  },
  {
    title: "Operational limits",
    body:
      "Scans may run in fallback or degraded modes when optional infrastructure such as Redis, Docker, or notification providers is unavailable. The product surfaces those states but does not guarantee a specific scanning depth in all environments.",
  },
  {
    title: "Evidence-backed reporting",
    body:
      "Findings, reports, and attack chains are produced from the repository state and orchestrated scan phases available to the system at runtime. Reports are stored as database-backed HTML or generated documents rather than permanent object-storage blobs.",
  },
  {
    title: "Workspace responsibility",
    body:
      "Workspace owners are responsible for credential hygiene, repository authorization, and downstream remediation. Fire Crow provides analysis artifacts and workflow telemetry, not legal certification or guaranteed exploit validation in every environment.",
  },
];

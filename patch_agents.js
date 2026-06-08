const fs = require('fs');
const file = 'frontend/src/app/page.tsx';
let content = fs.readFileSync(file, 'utf8');

const oldAgents = `const AGENTS = [
  { id: "MAESTRO", role: "Coordinates audit jobs, status, and cleanup." },
  { id: "RECON", role: "Builds repository and dependency context." },
  { id: "SAST", role: "Flags secrets, sinks, and code-level risk." },
  { id: "SANDBOX", role: "Maintains isolated validation boundaries." },
  { id: "AUTH", role: "Reviews authentication and session behavior." },
  { id: "API", role: "Reviews API security and configuration exposure." },
  { id: "SCORING", role: "Ranks findings with severity context." },
  { id: "REPORTER", role: "Packages reports and remediation handoff." },
];`;

const newAgents = `const AGENTS = [
  { id: "Intake & Auth", role: "Validates repository connection and confirms authorized review boundary." },
  { id: "Clone Layer", role: "Securely clones and isolates target repository code." },
  { id: "Sandbox Layer", role: "Maintains secure isolated runtime boundaries." },
  { id: "SAST Layer", role: "Flags secrets, sinks, and static code-level risk." },
  { id: "Deps & IaC", role: "Analyzes dependency vulnerabilities and IaC misconfigurations." },
  { id: "Runtime Probe", role: "Executes dynamic analysis and runtime validation." },
  { id: "Evidence", role: "Normalizes findings and verifies artifact evidence." },
  { id: "Deterministic Triage", role: "Filters false positives and groups vulnerabilities deterministically." },
  { id: "AI Triage", role: "AI-assisted triage with safe deterministic fallback." },
  { id: "Report Auto", role: "Generates founder-ready remediation reports." },
  { id: "Email Dispatch", role: "Dispatches automated email notifications when configured." },
  { id: "PR Automation", role: "Generates PR-ready remediation plans and creates PRs when configured." },
  { id: "Storage Layer", role: "Safely persists audit artifacts to cloud or local storage." },
  { id: "Observability", role: "Dashboard observability and execution history." },
];`;

content = content.replace(oldAgents, newAgents);

const oldHeroBody = `Run authorization-only audits, review evidence-backed findings, and generate founder-ready security reports.`;
const newHeroBody = `Run authorization-only audits, review evidence-backed findings, and generate founder-ready security reports. With deterministic fallback and safe reporting automation.`;

content = content.replace(oldHeroBody, newHeroBody);

fs.writeFileSync(file, content);

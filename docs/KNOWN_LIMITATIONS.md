# Known Limitations

This list only includes limitations verified in the current repository.

## Frontend / Backend Contract Mismatches

- The backend requires `attestation_accepted=true` on `POST /api/v1/audit/submit`, but the current dashboard does not send it. Sources: `backend/app/schemas/audit_api.py`, `frontend/src/features/audits/api.ts`, `frontend/src/app/dashboard/page.tsx`.
- `frontend/src/features/audits/types.ts` still exposes `scanners` and `sandbox_mode` fields that the current backend submit route does not use.
- `/system/status` only includes `sandbox_mode` and `integrations` for admin-like roles, but the dashboard code reads those fields as if they were broadly available. Sources: `backend/app/api/routes_system.py`, `frontend/src/app/dashboard/page.tsx`.

## Debug And Simulation Paths

- Dependency scanning falls back to simulated findings in debug mode when `osv-scanner` and `trivy` are unavailable. Source: `backend/app/agents/dependency_scan.py`.
- Semgrep scanning falls back to simulated findings in debug mode when `semgrep` is unavailable. Source: `backend/app/agents/sast_semgrep.py`.
- Sandbox provisioning can fall back to simulated containers in debug mode. Source: `backend/app/services/sandbox.py`.
- AI analyzer, GitHub MCP, and Google agent all have debug-fallback behavior. Sources: `backend/app/agents/ai_analyzer.py`, `github_mcp.py`, `google_agent.py`.
- Report generation can fall back to HTML plus a placeholder PDF when WeasyPrint is unavailable. Source: `backend/app/services/reporter.py`.

## Hosted Active-Testing Constraints

- Active testing depends on Docker availability, a supported Python/Node launch profile, and a `full_active` authorization scope. Source: `backend/app/orchestrator/scan_plan.py`.
- A hosted deployment can therefore run the UI/API while never performing real dynamic stages.

## Storage And Cleanup Risks

- `ReportGenerator.clean_r2_bucket_clutter()` deletes every non-PDF object in the configured bucket, even though the system also stores non-PDF artifacts. Source: `backend/app/services/reporter.py`.
- Local temporary report files are deleted after email dispatch, so durable access depends on the artifact copy. Source: `backend/app/services/reporter.py`.

## Frontend Content Drift

- `frontend/src/app/signup/page.tsx` still advertises "6 offensive agents", "Neon", and guaranteed email/report behavior that are not grounded in current backend code.
- `frontend/src/lib/policyData.ts` includes strong claims about SLAs, Neon, R2, GDPR/DPDP/CCPA compliance, and subscription operations that are not proven by the backend implementation.

## Test And Validation Gaps

- `scripts/smoke.py` is out of sync with the current auth and audit-submit contracts.
- The repository does not include a first-class browser E2E suite.
- Passing tests do not prove external scanners or Docker are installed.

## Partial Or Placeholder Subsystems

- `backend/app/workers/scheduler.py` contains placeholder scheduled-scan logic.
- `backend/app/middleware/telemetry.py` exists but is not registered in the FastAPI app.
- The current scoring stage uses simple severity-based CVSS assignment rather than scanner-native scoring inputs.


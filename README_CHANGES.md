# Fire Crow Backend Orchestration Refactor

## Changes
- Expanded `FindingModel` with safe, nullable metadata columns (`confidence`, `scanner_name`, `scanner_mode`, `file_path`, `line_number`, `route`, `metadata_json`).
- Added an `AuditArtifact` database table to capture large structured data outputs (e.g. SBOMs, API surface info, attack graphs).
- Introduced 8 new scanner and analyzer layers:
  - `backend/app/agents/api_surface.py`: Heuristically maps API routes from the codebase.
  - `backend/app/agents/authz_idor.py`: Flags potential IDOR vulnerabilities based on routing parameters and risk tags.
  - `backend/app/agents/cicd_scan.py`: Inspects `.github/workflows` for risky configurations (like `pull_request_target`).
  - `backend/app/agents/container_scan.py`: Inspects `Dockerfile` configurations for bad practices.
  - `backend/app/agents/sbom_graph.py`: Captures dependency manifest mappings.
  - `backend/app/agents/secret_history.py`: Heuristically spots hardcoded secrets with auto-redaction.
  - `backend/app/services/attack_graph.py`: Builds a node/edge correlation matrix.
  - `backend/app/services/confidence.py`: Upscores vulnerability confidence based on scanner type.
  - `backend/app/services/evidence_normalizer.py`: Normalizes disparate tool outputs.
  - `backend/app/services/remediation_planner.py`: Generates actionable fix plans.
- Rewrote the `maestro.py` `create_maestro_graph` function to securely execute all the above phases without disrupting terminal state generation or prior nodes.
- Updated the PDF `reporter.py` to seamlessly append the new artifact datasets.
- Tuned `github_mcp.py` to automatically construct GitHub issues out of the `remediation_tasks` pipeline instead of raw findings.

## Verification
- Backend tests (`pytest backend/tests -v`) run clean at 100% pass rate.
- Verified that `routes_sse.py` contains the required 15-second heartbeat loop logic.

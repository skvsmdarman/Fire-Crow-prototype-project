# Fire Crow — Fixes & Changelog

## 1. GitHub MCP Agent

**File:** `backend/app/agents/github_mcp.py`

### Issues Fixed
| # | Issue | Fix |
|---|-------|-----|
| 1.1 | `_github_api_request` had redundant imports inside the function body | Removed `import urllib.request`, `import urllib.error`, `import json` — already imported at module level |
| 1.2 | `GitMCPClient.connect_sse()` used f-string in `logger.info(f"...")` | Replaced with lazy `%s` formatting: `logger.info("...", self.sse_url)` |
| 1.3 | `GitMCPClient.connect_sse()` used f-string in `logger.info(f"...")` for write endpoint | Replaced with `logger.info("Discovered GitMCP write endpoint: %s", self.write_url)` |
| 1.4 | `GitMCPClient.call_tool()` used f-string in `logger.error(f"...")` for MCP error | Replaced with `logger.error("MCP tool call returned error: %s", res_data.get("error"))` |
| 1.5 | `GitMCPClient.call_tool()` used f-string in `logger.error(f"...")` for tool failure | Replaced with `logger.error("Failed to invoke GitMCP tool %s: %s", tool_name, exc)` |
| 1.6 | `run_github_mcp()` used f-string in `logger.warning(f"...")` for unsupported URL | Replaced with `logger.warning("Unsupported git URL for GitHub integration: %s", repo_url)` |
| 1.7 | Missing error message when `write_url` is None after failed connection | Added `logger.error("Failed to obtain GitMCP write URL for %s/%s", self.owner, self.repo)` |

---

## 2. SAST Agent (Security Scanner)

**File:** `backend/app/agents/sast.py`

### Issues Fixed
| # | Issue | Fix |
|---|-------|-----|
| 2.1 | f-string in `logger.warning()` for large file skip | Replaced with `logger.warning("Skipping large file %s...", rel_path)` |
| 2.2 | f-string in `logger.warning()` for file size check failure | Replaced with `logger.warning("Failed to check size for %s: %s", file_path, e)` |
| 2.3 | f-string in `logger.warning()` for file scan failure (secrets) | Replaced with `logger.warning("Failed to scan file %s for secrets: %s", file_path, e)` |
| 2.4 | f-string in `logger.warning()` for file size check failure (unsafe code) | Replaced with `logger.warning("Failed to check size for %s: %s", file_path, e)` |
| 2.5 | f-string in `logger.warning()` for file scan failure (unsafe code) | Replaced with `logger.warning("Failed to scan file %s for code issues: %s", file_path, e)` |
| 2.6 | f-string in `logger.info()` for `run_sast()` | Replaced with `logger.info("Running SAST scanner on %s", clone_path)` |
| 2.7 | Limited directory exclusions (`.git`, `node_modules`, `venv`, `.venv`) | Extended to `{".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "dist", "build", ".tox", ".eggs"}` with path-safe filtering |
| 2.8 | Limited binary file skip list | Extended with `.jpeg`, `.gif`, `.svg`, `.ico`, `.woff`, `.woff2`, `.eot`, `.ttf` |
| 2.9 | `errors='ignore'` silently drops encoding errors | Changed to `errors='replace'` — replaces invalid bytes with `�` instead of dropping |
| 2.10 | Limited source code extensions for unsafe code scan | Added `.rb`, `.rs` (Ruby, Rust) |

---

## 3. Authz/IDOR Agent

**File:** `backend/app/agents/authz_idor.py`

### Issues Fixed
| # | Issue | Fix |
|---|-------|-----|
| 3.1 | `db` parameter typed as `Any` | Changed to `Session` from `sqlalchemy.orm` |
| 3.2 | Missing `Session` import | Added `from sqlalchemy.orm import Session` |

---

## 4. API Surface Scanner

**File:** `backend/app/agents/api_surface.py`

### Issues Fixed
| # | Issue | Fix |
|---|-------|-----|
| 4.1 | `errors='ignore'` when reading source files silently drops invalid UTF-8 data | Changed to `errors='replace'` |

---

## 5. Telemetry Middleware

### Files Modified
- `backend/app/middleware/telemetry.py`
- `backend/app/main.py`

### Issues Fixed
| # | Issue | Fix |
|---|-------|-----|
| 5.1 | `TelemetryMiddleware` existed but was **never registered** in `main.py` | Added `app.add_middleware(TelemetryMiddleware)` in `main.py` |
| 5.2 | Hardcoded mock trace ID `"mock-trace-id-1234"` | Replaced with real `str(uuid.uuid4())` |
| 5.3 | Debug logger was **commented out** | Uncommented and converted to proper lazy formatting with `logger.debug("Telemetry: %s %s completed in %.4fs", ...)` |
| 5.4 | `X-Process-Time` header hardcoded as string | Now uses `f"{process_time:.4f}"` for proper float formatting |
| 5.5 | Missing `uuid` import | Added `import uuid` |

---

## 6. Neo4j Graph Database — Migration Infrastructure

### New Files
- `backend/app/services/neo4j_client.py` — Neo4j database driver (sync & async)
- `backend/app/services/neo4j_migration.py` — PostgreSQL → Neo4j migration pipeline

### Modified Files
- `backend/app/config.py`

### What Was Added
| # | Change | Details |
|---|--------|---------|
| 6.1 | Neo4j configuration settings | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` with sensible defaults |
| 6.2 | Neo4j client (`neo4j_client.py`) | Singleton pattern driver; `get_driver()`, `get_session()`, `verify_connectivity()`, `execute_query()`, async variants; connection lifecycle management |
| 6.3 | Migration service (`neo4j_migration.py`) | Full graph schema (Users, AuditJobs, Findings, AgentLogs, SecurityLogs, Organizations); constraints & indexes; `migrate_users()`, `migrate_audit_jobs()`, `migrate_security_logs()`, `run_full_migration()` |
| 6.4 | Graph query helper | `find_jobs_by_user()` — example graph traversal query using Neo4j patterns |

### Graph Schema
```
(:User)-[:OWNS]->(:AuditJob)
(:User)-[:HAS_LOG]->(:SecurityLog)
(:AuditJob)-[:HAS_FINDING]->(:Finding)
(:AuditJob)-[:HAS_AGENT_LOG]->(:AgentLog)
(:User)-[:MEMBER_OF]->(:Organization)
```

---

## 7. Documentation Updates

### Files Modified
- `docs/SECURITY_MODEL.md`
- `docs/ORCHESTRATION_PIPELINE.md`

| # | Change |
|---|--------|
| 7.1 | Marked `TelemetryMiddleware` registration as `[x]` (resolved) in Known Security Gaps |
| 7.2 | Added "Resolved Issues" section listing all completed fixes |

---

## Files Changed Summary

| File | Status |
|------|--------|
| `backend/app/agents/github_mcp.py` | Modified |
| `backend/app/agents/sast.py` | Modified |
| `backend/app/agents/authz_idor.py` | Modified |
| `backend/app/agents/api_surface.py` | Modified |
| `backend/app/middleware/telemetry.py` | Modified |
| `backend/app/main.py` | Modified |
| `backend/app/config.py` | Modified |
| `backend/app/services/neo4j_client.py` | **Created** |
| `backend/app/services/neo4j_migration.py` | **Created** |
| `docs/SECURITY_MODEL.md` | Modified |
| `docs/ORCHESTRATION_PIPELINE.md` | Modified |
| `FIXES_CHANGELOG.md` | **Created** |

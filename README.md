# Fire Crow

Fire Crow is a production-ready, repository-focused security audit and intelligence platform. It features a high-performance **FastAPI** backend, a responsive **Next.js** frontend, and a sophisticated **LangGraph** orchestration pipeline capable of chaining multiple deterministic and LLM-powered security agents.

Users can securely authenticate, submit GitHub HTTPS repository URLs for analysis, stream real-time audit logs over Server-Sent Events (SSE), and review comprehensive vulnerability reports with visual charts and detailed findings.

## Key Features

- **Enhanced Report Generation**: Premium PDF reports with SVG charts (donut, bar, stacked), severity distribution, scanner performance metrics, CWE analysis, and actionable security recommendations.
- **Real-Time Log Streaming**: Native SSE integration for streaming scan logs and progress updates directly to the frontend dashboard.
- **Agentic Orchestration Engine**: Uses a graph-based state machine (LangGraph) to route execution between passive scanning, heuristic intelligence gathering, and LLM-driven vulnerability reasoning.
- **Deep Security Tooling Integration**: Includes 14+ specialized scanners with AST-based analysis, configuration file scanning, and dynamic attack testing.
- **Secure Authentication Flow**: Native password login with secure token revocation, along with OAuth integrations for GitHub and Google.
- **Production Hardening**: Enforces SQLite blocklists in production, supports Redis/Celery job queues, and incorporates compliance filters.
- **Neon-Only Artifact Persistence**: All artifacts (reports, evidence, attack graphs) are stored in Neon PostgreSQL as TEXT/JSONB.
- **Automated Remediation (GitHub MCP)**: Creates GitHub issues with security labels (critical, high, medium, low, firecrow, security) and planning pull request structures.
- **Adaptive Scanning**: Dynamically adjusts scanning depth based on initial findings and repository characteristics.
- **Retry Mechanisms**: Automatic retry with exponential backoff for transient failures in non-critical phases.
- **Database Query Caching**: In-memory TTL cache for frequently accessed queries, reducing database load.
- **Performance Indexes**: Optimized database indexes for audit jobs, findings, and user sessions.

## System Architecture

### Backend Overview
- **Core Framework**: FastAPI (`backend/app/main.py`)
- **Orchestration**: LangGraph pipeline orchestrating security nodes via `backend/app/orchestrator/maestro.py`
- **Background Execution**: Scales horizontally with Celery + Redis, while preserving fast local development mode
- **Database**: SQLAlchemy ORM with PostgreSQL (production) or SQLite (development), optimized with connection pooling and query caching

### Frontend Overview
- **Framework**: Next.js App Router
- **Key Views**:
  - Landing page with scanner capabilities display
  - Auth flows with legal compliance checks
  - Main dashboard with real-time job monitoring, attack graphs, and chat widget
- **Data Fetching**: Custom API client, React hooks, and native SSE stream parsing

## Audit Scanners & Intelligence Layers

### Passive Analysis Phases
1. **recon**: Clones repository, detects tech stack, checks GitHub API security settings
2. **threat_model**: Generates prioritized attack vectors and assets
3. **api_surface**: Maps API routes and REST endpoints from the codebase
4. **secret_history**: Scans commit history for hardcoded secrets
5. **dependency**: Scans dependencies for known vulnerabilities (OSV/Trivy)
6. **sbom_graph**: Captures dependency mappings, outputs CycloneDX-compatible SBOM
7. **iac**: Scans Infrastructure-as-Code files for misconfigurations
8. **cicd_scan**: Inspects GitHub workflows for risky configurations
9. **container_scan**: Analyzes Dockerfile rules for dangerous capabilities
10. **config_scan**: Scans config files using hadolint, kube-linter, tfsec
11. **sast**: Static application security testing (Bandit, ESLint, regex)
12. **semgrep**: Multi-language static analysis with Semgrep rules
13. **authz_idor**: Flags potential IDOR vulnerabilities

### Active Testing Phases (Sandbox)
14. **sandbox**: Provisions isolated Docker/Kali container
15. **network**: Port scanning and service discovery
16. **attack**: Dynamic vulnerability testing (SSRF, XXE, SSTI, JWT, rate limiting)
17. **exploit**: Controlled validation of discovered vulnerabilities

### Analysis & Reporting
18. **ai_analyzer**: Deterministic finding triage and deduplication
19. **cross_validation**: Correlates findings, flags false positives
20. **scoring**: CVSS v3.1 vector assignment and risk scoring
21. **attack_graph**: Node-edge correlation for chained attack paths
22. **remediation_planner**: Generates actionable fix plans
23. **reporter**: Stores HTML reports in the database, generates on-demand PDFs for delivery workflows, and sends email notifications
24. **github_mcp**: Creates GitHub issues with security labels
25. **google_agent**: AI-powered PR risk analysis

## Pipeline Flow

```
recon → threat_model → api_surface → secret_history → dependency → sbom_graph → 
iac → cicd_scan → container_scan → config_scan → sast → semgrep → 
authz_idor → [sandbox → network → attack → exploit] → 
ai_analyzer → cross_validation → scoring → attack_graph → 
remediation_planner → reporter → github_mcp → google_agent → cleanup
```

## Local Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL (production) or SQLite (development)

### Backend Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend Setup
```powershell
cd frontend
npm install
```

### Environment Configuration
1. Copy `backend/.env.example` to `backend/.env.local`
2. Copy `frontend/.env.example` to `frontend/.env.local`

### Launch Application
```powershell
npm run dev
```

## Deployment Guide (Render)

**Minimum Production Environment Variables**:
```bash
DEBUG=false
DATABASE_URL=postgresql://...
SECRET_KEY=<long random secret>
ENCRYPTION_KEY=<long random encryption key>
FRONTEND_URL=https://your-firecrow-frontend.example.com
CORS_ORIGINS=https://your-firecrow-frontend.example.com
```

**Feature Flags (LLM Support)**:
```bash
LLM_CHAT_ASSISTANT=false
LLM_DASHBOARD_INSIGHT=false
LLM_ATTACK_CHAIN_NAMING=false
LLM_PR_DESCRIPTION=false
```

All `LLM_*` feature flags default to `false` and can be enabled independently when you are ready to activate those AI-assisted experiences.

**Optional Provider Integrations**:
```bash
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

## Testing and Validation

- **Full Suite Validation**: `npm run validate`
- **Backend Tests**: `python -m pytest backend/tests -v`
- **Frontend Checks**: `npm run lint && npm run build`

## Security Model

Fire Crow executes active/dynamic penetration tools. To prevent misuse:
- **Authorization Attestations**: Job submissions require cryptographically tracked consent fields
- **Sandboxing**: Active tools run inside isolated container network partitions
- **Data Protection**: Security audit logs and artifacts are persisted in Neon PostgreSQL

---

## Efficiency Recommendations for Developers

### Package Management
- **Removed**: `gitpython` (unused, potential security risk banned by cloud providers)
- **Kept**: All actively used dependencies (`docker`, `weasyprint`, `celery`, `redis`)
- **Frontend**: `reactflow` retained for attack graph visualization

### Database Optimization
- **Indexing**: Added composite indexes for frequently queried columns
- **Connection Pooling**: Configured with `pool_pre_ping=True`, 20 connections, 10 overflow
- **Query Caching**: In-memory TTL cache reduces DB load on repeated queries

### Server Efficiency
- **Async Operations**: FastAPI async endpoints with background task support
- **Response Caching**: System status cached for 30 seconds
- **Connection Recycling**: Database connections recycled every 30 minutes

### Report Generation
- **SVG Charts**: Donut charts for severity distribution, bar charts for scanner performance
- **Modular Design**: Chart generation methods separated for maintainability
- **PDF Optimization**: WeasyPrint generates temporary PDFs on demand while canonical reports stay in the database as HTML

---

*Documentation last updated: June 19, 2026*

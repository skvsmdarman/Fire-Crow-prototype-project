# Fire Crow

Fire Crow is a production-ready, repository-focused security audit and intelligence platform. It features a high-performance **FastAPI** backend, a responsive **Next.js** frontend, and a sophisticated **LangGraph** orchestration pipeline capable of chaining multiple deterministic and LLM-powered security agents.

Users can securely authenticate, submit GitHub HTTPS repository URLs for analysis, stream real-time audit logs over Server-Sent Events (SSE), and download comprehensive vulnerability reports with visual charts and detailed findings.

## Key Features

- **Enterprise Security Controls (MFA/SSO/PAM/IAM)**: Full Multi-Factor Authentication (TOTP), Single Sign-On federation (OIDC & SAML 2.0), Just-In-Time role escalation (PAM), fine-grained IAM resource policies, dormant account deactivations, and concurrent login audits.
- **Multi-Tenant Isolation**: Complete database-level partitioning with custom slug/domain headers routing resolution, and plan-specific limits (max users, max storage size).
- **Enhanced Report Generation**: Premium PDF reports with SVG charts (donut, bar, stacked), severity distribution, scanner performance metrics, CWE analysis, and actionable security recommendations.
- **Real-Time Log Streaming**: Native SSE integration for streaming scan logs and progress updates directly to the frontend dashboard.
- **Agentic Orchestration Engine**: Uses a graph-based state machine (LangGraph) to route execution between passive scanning, heuristic intelligence gathering, and LLM-driven vulnerability reasoning.
- **Deep Security Tooling Integration**: Includes 14+ specialized scanners with AST-based analysis, configuration file scanning, and dynamic attack testing.
- **Secure Authentication Flow**: Native password login with secure token revocation, along with OAuth integrations for GitHub and Google.
- **Production Hardening**: Enforces SQLite blocklists in production, supports Redis/Celery job queues, and incorporates compliance filters.
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
23. **reporter**: Generates PDF reports with charts and sends email notifications
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

## Deployment Topologies

The codebase supports three primary deployment paths for production environments:

### 1. Single-Service Render Deployment
Bundles the statically exported Next.js frontend and FastAPI backend inside a single Docker image, running migrations automatically during startup.
Refer to `render.yaml` and [docs/DEPLOYMENT_NOTES.md](docs/DEPLOYMENT_NOTES.md) for configuration details.

### 2. Multi-Service Docker Compose Stack
Orchestrates API replicas, background Celery workers, Celery Beat periodic scheduler, PostgreSQL, and password-secured Redis cache/brokers behind an Nginx ingress load balancer.
Launch using:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 3. AWS Cloud Architecture (Terraform)
Fully provisions highly available infrastructure on AWS including Application Load Balancers (ALB), ECS Fargate containers (with Auto-Scaling Policies), secure public/private subnets, private Amazon RDS PostgreSQL databases, and ElastiCache Redis replication groups.
Deploy using:
```bash
cd infrastructure/terraform
terraform init
terraform apply
```

## Production Environment Variables

**Minimum Production Credentials**:
```bash
DEBUG=false
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=<strong random key, min 32 chars>
ENCRYPTION_KEY=<strong random encryption key, min 32 chars>
FRONTEND_URL=https://your-firecrow-frontend.example.com
CORS_ORIGINS=https://your-firecrow-frontend.example.com
```

**Enterprise Hardening Controls**:
```bash
MFA_ENFORCE_FOR_ADMINS=true
MFA_TOTP_ISSUER="Fire Crow"
SSO_ALLOW_AUTO_PROVISION=false
PAM_MAX_DURATION_MINUTES=480
IAM_DORMANT_DAYS_THRESHOLD=90
```

**Feature Flags (LLM Support)**:
```bash
LLM_CHAT_ASSISTANT=false
LLM_DASHBOARD_INSIGHT=false
LLM_ATTACK_CHAIN_NAMING=false
LLM_PR_DESCRIPTION=false
```

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

> **Note**: A comprehensive strict rule-based audit was completed on June 29, 2026. All critical and high-severity backend issues were patched, and the build pipeline is fully verified. Read the full report at [docs/STRICT_AUDIT_REPORT.md](docs/STRICT_AUDIT_REPORT.md).

## Security Model

Fire Crow executes active/dynamic penetration tools. To prevent misuse:
- **Authorization Attestations**: Job submissions require cryptographically tracked consent fields
- **Sandboxing**: Active tools run inside isolated container network partitions
- **Data Protection**: Security audit logs are persisted immutably in the DB

---

## Efficiency Recommendations for Developers

### Package Management
- **Removed**: `gitpython` (unused, potential security risk banned by cloud providers)
- **Kept**: All actively used dependencies (`docker`, `weasyprint`, `celery`, `redis`, `boto3`)
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
- **PDF Optimization**: WeasyPrint with fallback for environments without GPU support

---

*Documentation last updated: June 29, 2026*

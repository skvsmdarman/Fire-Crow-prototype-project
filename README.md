# Fire Crow

Fire Crow is a production-ready, repository-focused security audit and intelligence platform. It features a high-performance **FastAPI** backend, a responsive **Next.js** frontend, and a sophisticated **LangGraph** orchestration pipeline capable of chaining multiple deterministic and LLM-powered security agents. 

Users can securely authenticate, submit GitHub HTTPS repository URLs for analysis, stream real-time audit logs over Server-Sent Events (SSE), and download comprehensive vulnerability reports and generated artifacts (such as SBOMs and Attack Graphs).

## 🚀 Key Features & Current Status

- **Real-Time Log Streaming**: Native SSE (Server-Sent Events) integration for real-time streaming of scan logs and progress updates directly to the frontend dashboard.
- **Agentic Orchestration Engine**: Uses a graph-based state machine (`LangGraph`) to route execution between passive scanning, heuristic intelligence gathering, and LLM-driven vulnerability reasoning.
- **Deep Security Tooling Integration**: Includes 8 specialized scanners (API surface, AuthZ/IDOR flagger, CI/CD scanning, Container scanning, SBOM generation, Secret history parsing).
- **Secure Authentication Flow**: Native password login with secure token revocation, along with OAuth integrations for GitHub and Google.
- **Production Hardening**: Enforces SQLite blocklists in production, supports Redis/Celery job queues, incorporates compliance filters (Terms of Service, Regional settings), and uses encrypted object storage (e.g., S3/R2).
- **Automated Remediation (GitHub MCP)**: Features GitHub integration capable of constructing automated GitHub issues and planning pull request structures from remediation tasks.

## 🏗 System Architecture

The project follows a decoupled, scalable architecture spanning frontend UI, an API gateway, background job orchestrators, and specialized security agents.

### Backend Overview
- **Core Framework**: FastAPI (`backend/app/main.py`)
- **Orchestration**: `LangGraph` pipeline orchestrating security nodes via `backend/app/orchestrator/maestro.py` and `backend/app/orchestrator/runtime.py`.
- **Background Execution**: Scales horizontally with `Celery` + `Redis`, while preserving a fast local development mode through FastAPI `BackgroundTasks`.
- **Database & Storage**: SQLAlchemy ORM (`backend/app/models/`) persisting jobs, multi-layered findings, audit artifacts, and system/compliance logs. Uses local filesystem fallback or R2/S3 for large PDF reports and SBOMs.

### Frontend Overview
- **Framework**: Next.js App Router (`frontend/src/app/*`)
- **Key Views**:
  - `page.tsx`: Landing Page
  - `signin/page.tsx` & `signup/page.tsx`: Auth flows with legal compliance checks
  - `dashboard/page.tsx`: Main user console featuring dynamic real-time job execution monitoring
- **Data Fetching**: Custom API client, React hooks, and native SSE stream parsing (`frontend/src/shared/hooks/useSSE.ts`).

## 🛡️ Audit Scanners & Intelligence Layers

Fire Crow's graph dynamically invokes a suite of analyzers based on the repository's technology stack and authorization scopes. Recent refactoring introduced numerous advanced analysis layers:

1. **`api_surface`**: Heuristically maps API routes and REST endpoints from the codebase.
2. **`authz_idor`**: Flags potential Insecure Direct Object Reference (IDOR) vulnerabilities based on routing parameters and risk tags.
3. **`cicd_scan`**: Inspects `.github/workflows` for risky configurations (e.g., untrusted `pull_request_target`).
4. **`container_scan`**: Analyzes `Dockerfile` rules for dangerous capabilities and bad practices.
5. **`sbom_graph`**: Captures dependency manifest mappings and outputs CycloneDX-compatible SBOM artifacts.
6. **`secret_history`**: Scans commit history heuristically to spot hardcoded secrets, supporting auto-redaction.
7. **`attack_graph`**: Builds a node-edge correlation matrix indicating chained attack paths across files.
8. **`remediation_planner`**: Analyzes findings to generate actionable fix plans and code snippets.
9. **`evidence_normalizer` & `confidence`**: Normalizes disparate tool outputs and intelligently upscores finding confidence.

## ⚙️ Local Development Setup

Fire Crow includes an easy-to-use launch configuration allowing rapid local development.

1. **Backend Environment Setup**:
   Create a Python virtual environment and install dependencies:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Frontend Environment Setup**:
   Install npm dependencies:
   ```powershell
   cd frontend
   npm install
   ```

3. **Environment Configuration**:
   - Copy `backend/.env.example` to `backend/.env.local`.
   - Copy `frontend/.env.example` to `frontend/.env.local`.

4. **Launch Application**:
   From the repository root, run the primary development script which boots both the frontend and backend servers concurrently:
   ```powershell
   npm run dev
   ```
   *(Alternatively, run `npm run dev:no-worker` to disable background worker scaling)*

## ☁️ Deployment Guide (Render)

Production deployments must not use `http://localhost:3000`. Set `FRONTEND_URL` accurately as OAuth callbacks and CORS mappings are heavily restricted.

**Minimum Production Environment Variables**:
```bash
DEBUG=false
DATABASE_URL=postgresql://...
SECRET_KEY=<long random secret>
ENCRYPTION_KEY=<long random encryption key>
FRONTEND_URL=https://your-firecrow-frontend.example.com
CORS_ORIGINS=https://your-firecrow-frontend.example.com
```

**Optional Provider Integrations**:
```bash
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

Before relying on OAuth or external connections in a production environment, verify the safety of your environment variables:
```bash
bash scripts/verify_render_env.sh
```
*(The script intentionally fails if SQLite is targeted, `DEBUG` is active, or `FRONTEND_URL` is missing)*

## 🧪 Testing and Validation

Fire Crow emphasizes testability. A full suite of testing utilities guarantees execution safety and architectural compliance:

- **Full Suite Validation**:
  ```powershell
  npm run validate
  ```
- **Backend Tests (Pytest)**:
  ```powershell
  .\.venv\Scripts\python.exe -m pytest backend/tests -v
  ```
- **Frontend Code Checks**:
  ```powershell
  cd frontend
  npm run lint
  npm run build
  ```

## 🔒 Security Model & Attestations

Fire Crow executes active/dynamic penetration tools. To prevent misuse, the API enforces a stringent Authorization Model:
- **Authorization Attestations**: Job submissions require cryptographically tracked consent fields (`attestation_accepted` and an explicit `authorization_scope`). 
- **Sandboxing**: Active tools run strictly inside isolated container network partitions (`backend/app/services/sandbox.py`) to prevent side-effects on public infrastructure.
- **Data Protection**: Security audit logs are persisted immutably in the DB. Presigned URLs are strictly validated. 
- Further reading on our detailed security roadmap and implementations can be found in `docs/SECURITY_MODEL.md` and `docs/IMPLEMENTATION_FRAMEWORK_V2.md`.

---
*Documentation last updated: June 08, 2026*

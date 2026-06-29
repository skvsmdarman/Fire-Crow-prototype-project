# Local Development

This guide reflects `package.json`, `scripts/dev.py`, `scripts/start-dev.ps1`, `scripts/validate.py`, `backend/.env.example`, `frontend/.env.example`, and the current backend/frontend entry points.

## Prerequisites

- Windows PowerShell is the primary repo workflow today.
- Python 3.12
- A virtual environment at `.venv`
- Node.js and npm
- Git
- Redis only if you want Celery locally
- Docker only if you want active sandboxing instead of simulation

## Backend Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Create backend env file:

```powershell
Copy-Item backend\.env.example backend\.env.local
```

Recommended local values from the example:

- `DEBUG=true`
- `DATABASE_URL=sqlite:///./firecrow.db`
- `FRONTEND_URL=http://localhost:3000`
- `FIRE_CROW_MOCK_SANDBOX=false` or `true` depending on your local goal

## Frontend Setup

```powershell
cd frontend
npm install
cd ..
```

Create frontend env file if you are not using the launcher:

```powershell
Copy-Item frontend\.env.example frontend\.env.local
```

Set:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Run The Full Stack

Preferred repo command:

```powershell
npm run dev
```

What it does from `scripts/dev.py`:

- reuses an already healthy backend or frontend when possible
- falls forward from busy ports
- injects `NEXT_PUBLIC_API_URL` into the frontend process
- starts a Celery worker only when Redis is reachable

## Run Without Worker

```powershell
npm run dev:no-worker
```

This still allows audit execution because the API falls back to `BackgroundTasks` in `backend/app/api/routes_audit.py`.

## Manual Backend Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Manual Frontend Run

```powershell
cd frontend
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000/api/v1"
npm run dev -- --port 3000
```

## Redis And Celery Notes

- Redis is optional for local development.
- If Redis is not reachable on `127.0.0.1:6379`, the launcher prints a warning and skips the worker.
- When Redis is reachable, the worker command is the one defined in `scripts/dev.py` and `backend/app/workers/celery_app.py`.

## Docker / Sandbox Notes

- `backend/app/services/sandbox.py` uses Docker only when `FIRE_CROW_MOCK_SANDBOX` is false and the Docker daemon is reachable.
- In debug mode, Docker failures fall back to simulation.
- In non-debug mode, Docker unavailability is treated more strictly.
- Active testing also depends on the scan plan in `backend/app/orchestrator/scan_plan.py`, not just Docker presence.

## Environment File Notes

- Backend env load order is documented in `backend/.env.example` and `backend/app/config.py`.
- The frontend launcher can override `NEXT_PUBLIC_API_URL` at process startup.
- Production-safe values should not be committed to local env files.

## Common Startup Issues

### Backend will not start

Check:

- `.venv` exists
- `SECRET_KEY` is set when `DEBUG=false`
- `DATABASE_URL` is valid
- `PYTHONPATH` points at repo root if running tests or manual scripts

### Frontend cannot reach backend

Check:

- `NEXT_PUBLIC_API_URL`
- backend actual port selected by the launcher
- browser devtools for 401/403 redirect loops

### Audit jobs never hit Celery

Check:

- Redis reachability on `127.0.0.1:6379`
- `REDIS_URL`
- worker logs

### Active testing never runs

Check:

- backend schema requires attestation fields
- authorization scope must be `full_active`
- Docker must be reachable
- repo must look like a supported Python or Node target

Note: The dashboard frontend correctly sends the required attestation fields to the backend.

---
*Documentation last updated: June 29, 2026*

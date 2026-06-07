# Troubleshooting

This guide uses the current code in `backend/app/*`, `frontend/src/*`, `scripts/*`, and the repo configuration files.

## Backend Won't Start

Check:

- `.venv` exists and dependencies are installed
- `SECRET_KEY` is set when `DEBUG=false`
- `DATABASE_URL` is reachable
- `PYTHONPATH` includes the repo root when running tests or manual commands

Relevant sources:

- `backend/app/config.py`
- `backend/app/models/database.py`
- `scripts/dev.py`

## Database Unavailable

Symptoms:

- `/health` returns `degraded`
- `/health/ready` returns `503`

Check:

- `DATABASE_URL`
- PostgreSQL reachability in non-debug mode
- whether you intended to use local SQLite in debug mode

Relevant sources:

- `backend/app/main.py`
- `backend/app/models/database.py`

## Redis Unavailable

Symptoms:

- worker does not start from the launcher
- jobs still run, but only through local fallback

Check:

- `REDIS_URL`
- Redis bind/port
- whether you are okay using `BackgroundTasks` instead of Celery

Relevant sources:

- `scripts/dev.py`
- `backend/app/api/routes_audit.py`

## Docker Unavailable

Symptoms:

- no real sandbox phases
- dynamic validation phases may be skipped or simulated

Check:

- Docker daemon status
- `FIRE_CROW_MOCK_SANDBOX`
- `DEBUG`
- whether the target repo looks like Python or Node

Relevant sources:

- `backend/app/services/sandbox.py`
- `backend/app/orchestrator/scan_plan.py`

## SSE Stream Disconnects

Symptoms:

- dashboard logs stop updating
- stream emits an error line

Check:

- auth token still present
- selected job still belongs to the current user
- backend logs for stream exceptions

Relevant sources:

- `backend/app/api/routes_sse.py`
- `frontend/src/shared/hooks/useSSE.ts`

## Report Not Generated

Check:

- reporter phase logs in `agent_logs`
- whether WeasyPrint is available
- whether the job ended as `partial`
- whether object storage or email errors degraded the job

Relevant sources:

- `backend/app/services/reporter.py`
- `backend/app/orchestrator/runtime.py`

## Object Storage Upload Failed

Symptoms:

- report falls back to local serving
- logs mention R2 or S3 failure

Check:

- `R2_*` settings
- legacy `CLOUDFLARE_R2_*` aliases if you rely on them
- endpoint scheme; the code prepends `https://` when missing in some paths

Relevant sources:

- `backend/app/services/storage.py`
- `backend/app/services/reporter.py`

## OAuth Callback Issues

Check:

- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
- `FRONTEND_URL`
- reverse proxy scheme headers such as `x-forwarded-proto`

Relevant sources:

- `backend/app/api/routes_auth.py`

## CORS Or API URL Issues

Symptoms:

- browser fetch failures
- frontend redirect loops back to `/signin`

Check:

- `NEXT_PUBLIC_API_URL`
- actual backend port chosen by the launcher
- `FRONTEND_URL`
- `CORS_ORIGINS`

Relevant sources:

- `frontend/src/shared/api/client.ts`
- `backend/app/main.py`
- `scripts/dev.py`

## Render Or Hosted Restart Issues

Check:

- production secrets and PostgreSQL config
- whether the frontend static export exists in the image
- whether pending migrations are blocking startup
- whether the host environment can support Docker-backed active phases

Relevant sources:

- `render.yaml`
- `Dockerfile`
- `backend/app/main.py`
- `backend/app/models/database.py`


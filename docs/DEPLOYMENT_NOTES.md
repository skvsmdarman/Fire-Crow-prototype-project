# Deployment Notes

These notes are based on `render.yaml`, `Dockerfile`, `backend/app/config.py`, `backend/app/models/database.py`, `backend/app/main.py`, `backend/app/services/sandbox.py`, and `backend/app/services/storage.py`.

## Current Deploy Shape

The repo contains a single-service Docker deployment path:

- `Dockerfile` builds the frontend static export and the backend image.
- `backend/app/main.py` mounts `frontend/out` if it exists.
- `render.yaml` declares one Docker web service named `firecrow`.

## Render Notes

Current `render.yaml` only provisions:

- `DATABASE_URL`
- `DEBUG=false`
- `SECRET_KEY`

That is enough for a minimal boot, not for all optional features.

The Docker container now runs `alembic -c backend/alembic.ini upgrade head` before starting `uvicorn`. That keeps the production startup guard in `backend/app/main.py` intact while making the default Render boot path compatible with pending schema changes.

## Production Database Requirements

Source: `backend/app/config.py`, `backend/app/models/database.py`.

- Production mode rejects SQLite.
- If `DATABASE_URL` points at PostgreSQL and the connection fails in non-debug mode, startup fails.
- In debug mode, failed PostgreSQL connection can fall back to local SQLite.

## Migration Behavior

Source: `backend/app/main.py`, `backend/app/models/database.py`, `backend/alembic/env.py`.

- Debug startup runs `Base.metadata.create_all()` and `ensure_database_compatibility()`.
- Non-debug startup checks for pending Alembic migrations and can block startup.
- The Docker production start command applies Alembic migrations first, then launches `uvicorn`.
- The compatibility helpers still auto-add some columns/tables outside Alembic in debug mode.

Practical warning:

- This repository still mixes migration-aware behavior with compatibility helpers. Treat schema changes carefully.

## Redis / Celery

- Redis is optional in the codebase.
- Without Redis, audit execution falls back to in-process `BackgroundTasks`.
- If you want worker isolation in production, you need a reachable Redis instance plus a Celery worker deployment.

## Docker / Sandbox Limits

Source: `backend/app/services/sandbox.py`.

- Dynamic validation depends on Docker and on the scanner image.
- Some platforms, especially restrictive hosted environments, may not support nested Docker use the way the active phases expect.
- In debug mode the code can simulate sandbox behavior; in non-debug mode the sandbox is stricter.

This means a hosted deployment can still serve the UI/API while never performing real active sandbox stages.

## Object Storage

- No external object storage required. All data lives in Neon DB.
- Reports and evidence are stored as HTML/JSONB in the database.

## Email Providers

- SMTP
- Resend
- Brevo

If none are configured:

- debug mode can write email HTML locally
- non-debug mode does not use that local fallback

## Static Frontend Serving

The backend serves `frontend/out` only if the directory exists. The Dockerfile makes that true in the container image, but local source-only backend runs do not automatically build the frontend.

## Render / Free-Tier Caveats

The codebase itself does not encode Render pricing or sleep behavior, but current hosted caveats still apply operationally:

- cold starts can affect startup probes
- Redis and Docker-dependent active stages may not be present
- filesystem-backed local artifact storage is not a strong persistence strategy for scaled or ephemeral instances

## Production-Hardening Checklist

- Use PostgreSQL (Neon DB), not SQLite.
- Set a strong `SECRET_KEY` and preferably a separate `ENCRYPTION_KEY`.
- Decide whether Redis/Celery is required or whether in-process execution is acceptable.
- Ensure Neon DB has appropriate backup policies, as all artifacts and reports are stored directly in the database.
- Decide whether email delivery is required and configure one provider.
- Decide whether real sandboxed active testing is possible on the target host.
- If you override the Docker start command, keep `alembic -c backend/alembic.ini upgrade head` ahead of `uvicorn`.
- Verify that frontend and backend audit-submit contracts match before relying on the dashboard UI.

---
*Documentation last updated: June 08, 2026*

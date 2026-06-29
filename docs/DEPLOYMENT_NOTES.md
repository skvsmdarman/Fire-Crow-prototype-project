# Deployment Notes

These notes are based on `render.yaml`, `Dockerfile`, `backend/app/config.py`, `backend/app/models/database.py`, `backend/app/main.py`, `backend/app/services/sandbox.py`, and `backend/app/services/storage.py`.

## Production Deploy Topologies

The codebase supports three primary deployment paths for production, ranging from single-container deployments to multi-container on-premise orchestration and full cloud architectures on AWS:

### 1. Single-Service Render Deployment
- **Architecture**: Encods a single-service Docker deployment path. The `Dockerfile` builds the frontend static export and bundles it with the backend API.
- **Boot Flow**: Runs `alembic -c backend/alembic.ini upgrade head` to apply pending migrations before launching `uvicorn`.
- **Render Spec**: `render.yaml` provisions `DATABASE_URL`, `DEBUG=false`, and `SECRET_KEY`.

### 2. Multi-Service Docker Compose Stack (`docker-compose.prod.yml`)
For self-hosted, scalable on-premise environments, a multi-service orchestration is provided:
- **Nginx Ingress Load Balancer**: Replicated reverse proxy mapping ports `80` and `443` with custom SSL volume mounts, distributing incoming traffic across API services.
- **Stateless API Services (FastAPI)**: Configured with `mode: replicated` and `replicas: 2`. Restricts resources per replica to `1 CPU` and `1GB RAM`.
- **Background Worker Nodes (Celery)**: Configured with `replicas: 2` to fetch tasks asynchronously from the message broker. Restricts resources per replica to `2 CPUs` and `2GB RAM`. Run using the command `celery -A app.workers.celery_app worker --loglevel=info --concurrency=4`.
- **Beat Scheduler (Celery Beat)**: A singleton container coordinating scheduled database cleanup routines and audit jobs.
- **Relational Storage (PostgreSQL)**: Replicated Postgres database mapping database state persistent volumes, featuring automated pg_isready health checks.
- **Cache & Message Broker (Redis)**: Replicated Redis instance running on port `6379`, secured with password verification and write-ahead persistence logs (`appendonly yes`).

### 3. Terraform Cloud Infrastructure (`infrastructure/terraform/*`)
For enterprise deployments on AWS, the architecture is fully provisioned using Terraform:
- **Secure Network VPC**: Segmented across 2 Availability Zones, separating public subnets (hosting the ALB) and private subnets (hosting ECS containers, RDS, and ElastiCache nodes) with a NAT Gateway for private internet egress.
- **Elastic Container Service (ECS) Fargate**: Runs API and Celery worker task definitions on AWS serverless compute with Auto-Scaling Policies linked to CPU utilization.
- **Application Load Balancer (ALB)**: Exposes endpoints securely with SSL termination and distributes traffic to ECS tasks.
- **Amazon RDS (PostgreSQL)**: Provisioned within a private DB subnet with restricted security groups accepting connections only from ECS security groups.
- **Amazon ElastiCache (Redis)**: Provisioned inside private subnets for fast session management, rate limiting, and task queues.

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
*Documentation last updated: June 29, 2026*

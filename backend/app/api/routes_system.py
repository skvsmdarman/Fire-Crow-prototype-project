from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import AuditJob, FindingModel, User, get_db
from backend.app.services.auth import get_current_user


router = APIRouter(prefix="/system", tags=["System"])


def _is_admin(user: User | None) -> bool:
    role = (user.role_id or "").lower() if user else ""
    return role in {"admin", "owner", "security_admin", "platform_admin"}


@router.get("/status")
async def system_status(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return backend readiness and tenant-scoped operational status for the control panel."""
    try:
        db.execute(text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "unavailable"

    user = db.query(User).filter(User.id == user_id).first()
    total_jobs = db.query(AuditJob).filter(AuditJob.user_id == user_id).count()

    # Count findings for this user's jobs.
    # The Neo4j ORM layer supports .join() but we use a safer two-step
    # approach that works reliably across both PostgreSQL and Neo4j.
    try:
        total_findings = (
            db.query(FindingModel)
            .join(AuditJob, FindingModel.job_id == AuditJob.id)
            .filter(AuditJob.user_id == user_id)
            .count()
        )
    except (AttributeError, Exception):
        # Fallback: fetch user's job IDs then count findings by those IDs
        user_jobs = db.query(AuditJob).filter(AuditJob.user_id == user_id).all()
        user_job_ids = [j.id for j in user_jobs]
        if user_job_ids:
            total_findings = sum(
                db.query(FindingModel).filter(FindingModel.job_id == jid).count()
                for jid in user_job_ids
            )
        else:
            total_findings = 0

    payload = {
        "api": "online",
        "database": database,
        "readiness": "degraded" if database != "connected" else "ready",
        "stats": {
            "jobs": total_jobs,
            "findings": total_findings,
        },
        "legal": {
            "privacy_policy_version": "2026-06-06",
            "terms_version": "2026-06-06",
        },
        "agents": [
            {"name": "MAESTRO", "role": "Orchestration", "status": "ready"},
            {"name": "RECON", "role": "Repository clone and stack detection", "status": "ready"},
            {"name": "SAST", "role": "Secrets and unsafe code analysis", "status": "ready"},
            {"name": "SANDBOX", "role": "Controlled sandbox validation", "status": "ready"},
            {"name": "NETWORK", "role": "Port and service discovery", "status": "ready"},
            {"name": "DYNAMIC_VALIDATION", "role": "Authorization-only runtime checks", "status": "ready"},
            {"name": "EVIDENCE", "role": "Evidence-backed finding validation", "status": "ready"},
            {"name": "SCORING", "role": "CVSS prioritization", "status": "ready"},
            {"name": "REPORTER", "role": "Report generation", "status": "ready"},
            {"name": "GITHUB_MCP", "role": "GitMCP issue and PR generation", "status": "ready"},
            {"name": "GOOGLE_AGENT", "role": "PR risk assessment and email alerts", "status": "ready"},
        ],
    }

    if _is_admin(user):
        payload["debug"] = settings.DEBUG
        payload["sandbox_mode"] = "simulation" if settings.FIRE_CROW_MOCK_SANDBOX else "docker"
        payload["integrations"] = {
            "github_oauth": bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET),
            "google_oauth": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
            "redis": bool(settings.REDIS_URL),
            "report_storage": bool(
                settings.R2_ACCESS_KEY_ID
                and settings.R2_SECRET_ACCESS_KEY
                and settings.R2_ENDPOINT_URL
                and settings.R2_BUCKET_NAME
            ),
            "email": bool(settings.RESEND_API_KEY),
            "ai_models": bool(settings.GEMINI_API_KEY or settings.OPENAI_API_KEY),
        }

    return payload

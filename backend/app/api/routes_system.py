from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import (
    AuditJob,
    FindingModel,
    User,
    get_db,
    AgentLog,
    AuditArtifact,
    ComplianceEvent,
    UserSession,
    SecurityLog,
)
from backend.app.services.auth import get_current_user
from backend.app.services.housekeeping import run_housekeeping


router = APIRouter(prefix="/system", tags=["System"])


def _is_admin(user: User | None) -> bool:
    role = (user.role_id or "").lower() if user else ""
    return role in {"admin", "owner", "security_admin", "platform_admin"}


async def require_admin(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not _is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access database management.",
        )
    return user


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
    total_findings = (
        db.query(FindingModel)
        .join(AuditJob, FindingModel.job_id == AuditJob.id)
        .filter(AuditJob.user_id == user_id)
        .count()
    )

    payload = {
        "api": "online",
        "database": database,
        "readiness": "degraded" if database != "connected" else "ready",
        "llm_features": {
            "chat_assistant": settings.LLM_CHAT_ASSISTANT,
            "dashboard_insight": settings.LLM_DASHBOARD_INSIGHT,
            "attack_chain_naming": settings.LLM_ATTACK_CHAIN_NAMING,
            "pr_description": settings.LLM_PR_DESCRIPTION,
        },
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


@router.get("/database/stats")
async def get_database_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Retrieve detailed database metrics, table row counts, and storage metrics for admin dashboard."""
    dialect = db.bind.dialect.name if db.bind else "unknown"
    db_size = None

    if "postgresql" in settings.DATABASE_URL:
        try:
            db_size = db.execute(text("SELECT pg_database_size(current_database())")).scalar()
        except Exception:
            pass
    else:
        try:
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path)
            else:
                db_size = 0
        except Exception:
            pass

    def get_count(model) -> int:
        try:
            return db.query(model).count()
        except Exception:
            db.rollback()
            return 0

    from backend.app.models.database import check_pending_migrations
    pending_migrations = check_pending_migrations()

    row_counts = {
        "users": get_count(User),
        "audit_jobs": get_count(AuditJob),
        "findings": get_count(FindingModel),
        "agent_logs": get_count(AgentLog),
        "audit_artifacts": get_count(AuditArtifact),
        "compliance_events": get_count(ComplianceEvent),
        "user_sessions": get_count(UserSession),
        "security_logs": get_count(SecurityLog),
    }

    return {
        "dialect": dialect,
        "db_size_bytes": db_size,
        "row_counts": row_counts,
        "pending_migrations": pending_migrations,
    }


@router.post("/database/housekeeping")
async def trigger_database_housekeeping(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Manually trigger database housekeeping / storage pruning on demand."""
    try:
        counts = run_housekeeping(db)
        return {"status": "success", "counts": counts}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database housekeeping failed: {str(e)}",
        )

from __future__ import annotations

import os
import shutil
import socket
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
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
from app.services.auth import get_current_user
from app.services.housekeeping import run_housekeeping
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System"])


def _is_admin(user: User | None) -> bool:
    if not user:
        return False
    return user.is_admin


def _redis_reachable() -> bool:
    if not settings.REDIS_URL:
        return False
    parsed = urlparse(settings.REDIS_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _sandbox_agent_status() -> str:
    if settings.FIRE_CROW_MOCK_SANDBOX:
        return "simulation"
    return "ready" if shutil.which("docker") else "degraded"


def _email_agent_status() -> str:
    has_provider = bool(
        (settings.SMTP_USER and settings.SMTP_PASSWORD)
        or settings.RESEND_API_KEY
        or settings.BREVO_API_KEY
    )
    if has_provider:
        return "ready"
    return "local-only" if settings.DEBUG else "disabled"


def _llm_agent_status() -> str:
    return "ready" if (settings.GEMINI_API_KEY or settings.OPENAI_API_KEY) else "disabled"


def _github_agent_status() -> str:
    return "ready" if (settings.GITHUB_TOKEN or (settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET)) else "disabled"


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
    from app.models.database import query_cache
    
    # Check cache first
    cache_key = f"system_status:{user_id}"
    cached = query_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        db.execute(text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "unavailable"
    redis_ready = _redis_reachable()
    sandbox_status = _sandbox_agent_status()
    llm_status = _llm_agent_status()
    github_status = _github_agent_status()
    email_status = _email_agent_status()

    user = db.query(User).filter(User.id == user_id).first()
    total_jobs = db.query(AuditJob).filter(AuditJob.user_id == user_id).count()
    total_findings = (
        db.query(FindingModel)
        .join(AuditJob, FindingModel.job_id == AuditJob.id)
        .filter(AuditJob.user_id == user_id)
        .count()
    )

    # GitHub scope descriptions for frontend display
    github_scope_descriptions = {
        "repo": "Full control of private repositories (issues, labels, PRs, code)",
        "workflow": "Update GitHub Action workflows",
        "read:org": "Read organization membership",
        "user:email": "Access user email addresses",
    }

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
            "privacy_policy_version": settings.PRIVACY_POLICY_VERSION,
            "terms_version": settings.TERMS_VERSION,
        },
        "github_permissions": {
            "scopes": settings.GITHUB_OAUTH_SCOPES,
            "descriptions": github_scope_descriptions,
        },
        "agents": [
            {"name": "MAESTRO", "role": "Orchestration", "status": "ready" if database == "connected" else "degraded"},
            {"name": "RECON", "role": "Repository clone and stack detection", "status": "ready" if database == "connected" else "degraded"},
            {"name": "SAST", "role": "Secrets and unsafe code analysis", "status": "ready" if database == "connected" else "degraded"},
            {"name": "SANDBOX", "role": "Controlled sandbox validation", "status": sandbox_status},
            {"name": "NETWORK", "role": "Port and service discovery", "status": sandbox_status},
            {"name": "DYNAMIC_VALIDATION", "role": "Authorization-only runtime checks", "status": sandbox_status},
            {"name": "EVIDENCE", "role": "Evidence-backed finding validation", "status": "ready" if database == "connected" else "degraded"},
            {"name": "SCORING", "role": "CVSS prioritization", "status": llm_status if any(payload for payload in [settings.LLM_ATTACK_CHAIN_NAMING, settings.LLM_DASHBOARD_INSIGHT, settings.LLM_CHAT_ASSISTANT, settings.LLM_PR_DESCRIPTION]) else "ready"},
            {"name": "REPORTER", "role": "Report generation", "status": "ready" if database == "connected" else "degraded"},
            {"name": "GITHUB_MCP", "role": "GitMCP issue and PR generation with labels", "status": github_status},
            {"name": "GOOGLE_AGENT", "role": "PR risk assessment and email alerts", "status": email_status},
        ],
    }

    if _is_admin(user):
        payload["debug"] = settings.DEBUG
        payload["sandbox_mode"] = "simulation" if settings.FIRE_CROW_MOCK_SANDBOX else "docker"
        payload["integrations"] = {
            "github_oauth": bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET),
            "google_oauth": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
            "redis": redis_ready,
            "report_storage": bool(
                settings.REPORT_STORE_HTML_IN_DB
                or settings.REPORT_STORE_MARKDOWN_IN_DB
                or settings.REPORT_LOCAL_FALLBACK
                or (
                    settings.R2_ACCESS_KEY_ID
                    and settings.R2_SECRET_ACCESS_KEY
                    and settings.R2_ENDPOINT_URL
                    and settings.R2_BUCKET_NAME
                )
            ),
            "email": email_status == "ready",
            "ai_models": bool(settings.GEMINI_API_KEY or settings.OPENAI_API_KEY),
        }

    # Cache for 30 seconds to reduce DB load on frequent status polls
    query_cache.set(cache_key, payload, ttl=30)
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

    from app.models.database import check_pending_migrations
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
        logger.error(f"Database housekeeping failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database housekeeping failed.",
        )


@router.get("/metrics")
async def prometheus_metrics(
    admin_user: User = Depends(require_admin),
):
    """Prometheus metrics endpoint for monitoring and alerting."""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        metrics_data = generate_latest()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        # Fallback if prometheus_client is not available
        return Response(
            content="# prometheus_client not installed\n",
            media_type="text/plain"
        )

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import AuditJob, FindingModel, get_db


router = APIRouter(prefix="/system", tags=["System"])


@router.get("/status")
async def system_status(db: Session = Depends(get_db)):
    """Return backend readiness and integration configuration for the frontend control panel."""
    try:
        db.execute(text("SELECT 1"))
        database = "connected"
    except Exception as exc:
        database = f"error: {exc}"

    total_jobs = db.query(AuditJob).count()
    total_findings = db.query(FindingModel).count()

    return {
        "api": "online",
        "database": database,
        "debug": settings.DEBUG,
        "sandbox_mode": "simulation" if settings.FIRE_CROW_MOCK_SANDBOX else "docker",
        "stats": {
            "jobs": total_jobs,
            "findings": total_findings,
        },
        "integrations": {
            "github_oauth": bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET),
            "redis": bool(settings.REDIS_URL),
            "report_storage": bool(
                settings.R2_ACCESS_KEY_ID
                and settings.R2_SECRET_ACCESS_KEY
                and settings.R2_ENDPOINT_URL
                and settings.R2_BUCKET_NAME
            ),
            "email": bool(settings.RESEND_API_KEY),
            "ai_models": bool(settings.GEMINI_API_KEY or settings.OPENAI_API_KEY),
        },
        "agents": [
            {"name": "MAESTRO", "role": "Orchestration", "status": "ready"},
            {"name": "RECON", "role": "Repository clone and stack detection", "status": "ready"},
            {"name": "SAST", "role": "Secrets and unsafe code analysis", "status": "ready"},
            {"name": "SANDBOX", "role": "Kali runtime provisioning", "status": "ready"},
            {"name": "NETWORK", "role": "Port and service discovery", "status": "ready"},
            {"name": "ATTACK", "role": "Automated active scanning", "status": "ready"},
            {"name": "EXPLOIT", "role": "Proof generation", "status": "ready"},
            {"name": "SCORING", "role": "CVSS prioritization", "status": "ready"},
            {"name": "REPORTER", "role": "Report generation", "status": "ready"},
            {"name": "GITHUB_MCP", "role": "GitMCP issue and PR generation", "status": "ready"},
            {"name": "GOOGLE_AGENT", "role": "PR risk assessment and email alerts", "status": "ready"},
        ],
    }


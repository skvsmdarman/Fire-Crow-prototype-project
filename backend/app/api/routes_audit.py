import logging
import socket
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse, RedirectResponse
from backend.app.services.limiter import limiter
from sqlalchemy.orm import Session
from typing import List
from urllib.parse import unquote, urlparse

from backend.app.api.audit_queries import get_owned_job_or_404
from backend.app.config import WORKSPACE_DIR, settings
from backend.app.models import get_db, AuditJob, FindingModel, AgentLog
from backend.app.schemas import (
    JobDetailResponse,
    JobResponse,
    JobStatus,
    SubmitJobRequest,
    build_job_detail_response,
    build_job_response,
)
from backend.app.orchestrator.runtime import execute_audit_job
from backend.app.services.auth import get_current_user
from backend.app.services.redaction import redact_text
from backend.app.workers.celery_app import run_audit_job_task, celery_app

logger = logging.getLogger("firecrow.api.audit")
router = APIRouter(prefix="/audit", tags=["Security Auditing"])

MAX_ACTIVE_JOBS_PER_USER = 5
REPORTS_DIR = WORKSPACE_DIR / "workspace" / "reports"


def _is_broker_reachable() -> bool:
    if not settings.REDIS_URL:
        return False
    redis_url = urlparse(settings.REDIS_URL)
    host = redis_url.hostname or "localhost"
    port = redis_url.port or 6379
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _dispatch_audit_job(
    background_tasks: BackgroundTasks,
    *,
    job_id: str,
    user_id: str,
    repo_url: str,
    repo_branch: str,
) -> None:
    if not _is_broker_reachable():
        logger.info("Redis broker is unavailable. Running job %s through local BackgroundTasks fallback.", job_id)
        background_tasks.add_task(
            execute_audit_job,
            job_id,
            user_id,
            repo_url,
            repo_branch,
        )
        return

    try:
        run_audit_job_task.apply_async(
            kwargs={
                "job_id": job_id,
                "user_id": user_id,
                "repo_url": repo_url,
                "repo_branch": repo_branch,
            },
            task_id=job_id,
        )
    except Exception as exc:
        logger.warning(
            "Celery/Redis broker failed (%s). Falling back to local BackgroundTasks thread for job %s.",
            redact_text(str(exc)),
            job_id,
        )
        background_tasks.add_task(
            execute_audit_job,
            job_id,
            user_id,
            repo_url,
            repo_branch,
        )


def _active_job_count(db: Session, user_id: str) -> int:
    return (
        db.query(AuditJob)
        .filter(AuditJob.user_id == user_id)
        .filter(AuditJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
        .count()
    )


def _safe_local_report_path(report_pdf_url: str) -> tuple[Path, str, str]:
    parsed = urlparse(report_pdf_url)
    report_path = parsed.path if parsed.scheme else report_pdf_url
    if not report_path.startswith("/reports/"):
        raise HTTPException(status_code=400, detail="Unsupported local report URL")

    file_name = unquote(report_path.removeprefix("/reports/"))
    if "/" in file_name or "\\" in file_name or Path(file_name).name != file_name:
        raise HTTPException(status_code=400, detail="Invalid report file path")
    if Path(file_name).suffix.lower() not in {".pdf", ".html"}:
        raise HTTPException(status_code=400, detail="Invalid report file type")

    reports_root = REPORTS_DIR.resolve()
    file_path = (reports_root / file_name).resolve()
    try:
        file_path.relative_to(reports_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid report file path") from exc

    media_type = "text/html" if file_path.suffix.lower() == ".html" else "application/pdf"
    return file_path, file_name, media_type


def _allowed_external_report_url(report_pdf_url: str) -> bool:
    parsed = urlparse(report_pdf_url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False

    allowed_hosts: set[str] = set()
    if settings.R2_ENDPOINT_URL:
        endpoint_host = urlparse(settings.R2_ENDPOINT_URL).hostname
        if endpoint_host:
            allowed_hosts.add(endpoint_host.lower())

    hostname = (parsed.hostname or "").lower()
    return any(hostname == allowed_host or hostname.endswith(f".{allowed_host}") for allowed_host in allowed_hosts)


@router.post("/submit", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def submit_audit(
    request: Request,
    payload: SubmitJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Submit a security audit job for a remote repository. Dispatches Celery task or falls back to BackgroundTasks."""
    if _active_job_count(db, user_id) >= MAX_ACTIVE_JOBS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Active audit limit reached. Complete or cancel an audit before starting more than {MAX_ACTIVE_JOBS_PER_USER}.",
        )

    job = AuditJob(
        user_id=user_id,
        repo_url=payload.repo_url,
        repo_branch=payload.repo_branch,
        status=JobStatus.QUEUED
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _dispatch_audit_job(
        background_tasks,
        job_id=job.id,
        user_id=user_id,
        repo_url=payload.repo_url,
        repo_branch=payload.repo_branch or "main",
    )

    return build_job_response(job)


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve all jobs submitted by the current authenticated tenant (Tenant Isolation)."""
    jobs = db.query(AuditJob).filter(AuditJob.user_id == user_id).order_by(AuditJob.created_at.desc()).all()

    return [build_job_response(job) for job in jobs]


@router.get("/job/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(
    job_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve details and findings of a specific job (scoped to authenticated tenant)."""
    job = get_owned_job_or_404(db, job_id, user_id)
    findings = db.query(FindingModel).filter(FindingModel.job_id == job_id).all()

    return build_job_detail_response(job, findings)


@router.delete("/job/{job_id}", status_code=status.HTTP_200_OK)
async def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Request cancellation for a running or queued job and let the runtime finalize cleanup."""
    job = get_owned_job_or_404(db, job_id, user_id)

    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.PARTIAL]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job cannot be cancelled in status {job.status.value}"
        )

    if not job.cancel_requested:
        job.cancel_requested = True
        job.cancel_requested_at = datetime.now(timezone.utc)

    try:
        celery_app.control.revoke(job_id, terminate=True, signal="SIGTERM")
    except Exception as e:
        logger.warning("Failed to notify Celery about cancellation request for task %s: %s", job_id, redact_text(str(e)))

    cancel_log = AgentLog(
        job_id=job_id,
        agent_name="MAESTRO",
        log_level="WARNING",
        message="Audit cancellation requested by user. Waiting for orchestrator to finalize cleanup."
    )
    db.add(cancel_log)
    db.commit()

    return {"message": "Job cancellation request recorded successfully", "job_id": job_id}


@router.get("/job/{job_id}/report", response_class=FileResponse)
async def download_report(
    job_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Authenticated endpoint to download PDF reports."""
    job = get_owned_job_or_404(db, job_id, user_id)
    if not job.report_pdf_url:
        raise HTTPException(status_code=404, detail="Report not ready or missing")

    parsed_report_url = urlparse(job.report_pdf_url)
    is_legacy_local_report = (
        parsed_report_url.scheme in {"http", "https"}
        and (parsed_report_url.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}
        and parsed_report_url.path.startswith("/reports/")
    )
    if job.report_pdf_url.startswith("/reports/") or is_legacy_local_report:
        file_path, file_name, media_type = _safe_local_report_path(job.report_pdf_url)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report file not found on disk")

        return FileResponse(path=file_path, filename=file_name, media_type=media_type)

    if _allowed_external_report_url(job.report_pdf_url):
        return RedirectResponse(job.report_pdf_url)

    logger.warning("Rejected unsafe report URL for job %s: %s", job_id, redact_text(job.report_pdf_url))
    raise HTTPException(status_code=400, detail="Report URL is not from an allowed storage location")

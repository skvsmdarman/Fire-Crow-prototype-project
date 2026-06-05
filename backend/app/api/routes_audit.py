import logging
import socket
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List
import os
from urllib.parse import urlparse

from backend.app.api.audit_queries import get_owned_job_or_404
from backend.app.config import settings
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
from backend.app.workers.celery_app import run_audit_job_task, celery_app

logger = logging.getLogger("firecrow.api.audit")
router = APIRouter(prefix="/audit", tags=["Security Auditing"])


def _is_broker_reachable() -> bool:
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
            str(exc),
            job_id,
        )
        background_tasks.add_task(
            execute_audit_job,
            job_id,
            user_id,
            repo_url,
            repo_branch,
        )


@router.post("/submit", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def submit_audit(
    request: SubmitJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Submit a security audit job for a remote repository. Dispatches Celery task or falls back to BackgroundTasks."""
    job = AuditJob(
        user_id=user_id,
        repo_url=request.repo_url,
        repo_branch=request.repo_branch,
        status=JobStatus.QUEUED
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _dispatch_audit_job(
        background_tasks,
        job_id=job.id,
        user_id=user_id,
        repo_url=request.repo_url,
        repo_branch=request.repo_branch or "main",
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
        logger.warning(f"Failed to notify Celery about cancellation request for task {job_id}: {str(e)}")

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
    
    if not job.report_pdf_url.startswith("/reports/"):
        return RedirectResponse(job.report_pdf_url)
        
    from backend.app.config import WORKSPACE_DIR
    file_name = job.report_pdf_url.split("/reports/")[-1]
    file_path = os.path.join(WORKSPACE_DIR, "workspace", "reports", file_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")
        
    return FileResponse(path=file_path, filename=file_name, media_type="application/pdf")

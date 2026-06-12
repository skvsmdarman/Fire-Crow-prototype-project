import logging
import socket
import re
import os
import httpx
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse, RedirectResponse
from backend.app.services.limiter import limiter
from sqlalchemy.orm import Session
from typing import List, Optional
from urllib.parse import unquote, urlparse

from backend.app.api.audit_queries import get_owned_job_or_404
from backend.app.config import WORKSPACE_DIR, settings
from backend.app.models import get_db, AuditJob, FindingModel, AgentLog, User
from backend.app.schemas import (
    JobDetailResponse,
    JobResponse,
    JobStatus,
    SubmitJobRequest,
    build_job_detail_response,
    build_job_response,
)
from backend.app.orchestrator.runtime import execute_audit_job
from backend.app.services.auth import get_current_user, decrypt_provider_token
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
    custom_email: Optional[str] = None,
) -> None:
    if not _is_broker_reachable():
        logger.info("Redis broker is unavailable. Running job %s through local BackgroundTasks fallback.", job_id)
        background_tasks.add_task(
            execute_audit_job,
            job_id,
            user_id,
            repo_url,
            repo_branch,
            custom_email,
        )
        return

    try:
        run_audit_job_task.apply_async(
            kwargs={
                "job_id": job_id,
                "user_id": user_id,
                "repo_url": repo_url,
                "repo_branch": repo_branch,
                "custom_email": custom_email,
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
            custom_email,
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
        status=JobStatus.QUEUED,
        auto_push=payload.auto_push if payload.auto_push is not None else False
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
        custom_email=payload.custom_email,
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

        # If an HTML version exists, serve that instead of a simulated PDF
        html_path = file_path.with_suffix(".html")
        if file_path.suffix.lower() == ".pdf" and html_path.exists():
            file_path = html_path
            file_name = html_path.name
            media_type = "text/html"

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report file not found on disk")

        return FileResponse(path=file_path, filename=file_name, media_type=media_type)

    if _allowed_external_report_url(job.report_pdf_url):
        return RedirectResponse(job.report_pdf_url)

    logger.warning("Rejected unsafe report URL for job %s: %s", job_id, redact_text(job.report_pdf_url))
    raise HTTPException(status_code=400, detail="Report URL is not from an allowed storage location")


from pydantic import BaseModel

class EmailReportRequest(BaseModel):
    email: Optional[str] = None


@router.post("/job/{job_id}/email")
async def email_report(
    job_id: str,
    payload: EmailReportRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Authenticated endpoint to send report via email."""
    job = get_owned_job_or_404(db, job_id, user_id)
    if not job.report_pdf_url:
        raise HTTPException(status_code=400, detail="Report is not ready or missing")

    recipient = payload.email.strip() if payload.email and payload.email.strip() else None
    if not recipient:
        from backend.app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.email:
            recipient = user.email

    if not recipient or recipient == "audit-recipient@firecrow.dev":
        raise HTTPException(status_code=400, detail="No valid recipient email address found. Please specify one.")

    # Re-calculate finding counts
    findings = db.query(FindingModel).filter(FindingModel.job_id == job_id).all()
    counts = {
        Severity.CRITICAL: len([f for f in findings if f.severity == Severity.CRITICAL]),
        Severity.HIGH: len([f for f in findings if f.severity == Severity.HIGH]),
        Severity.MEDIUM: len([f for f in findings if f.severity == Severity.MEDIUM]),
        Severity.LOW: len([f for f in findings if f.severity == Severity.LOW]),
        Severity.INFO: len([f for f in findings if f.severity == Severity.INFO]),
    }

    # Resolve local PDF path if the report URL points locally
    pdf_path = None
    parsed_report_url = urlparse(job.report_pdf_url)
    is_legacy_local_report = (
        parsed_report_url.scheme in {"http", "https"}
        and (parsed_report_url.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}
        and parsed_report_url.path.startswith("/reports/")
    )
    if job.report_pdf_url.startswith("/reports/") or is_legacy_local_report:
        try:
            file_path, _, _ = _safe_local_report_path(job.report_pdf_url)
            if file_path.exists():
                pdf_path = str(file_path)
        except Exception:
            pass

    # If the file is not on the local disk (e.g. stored in R2 or stateless container),
    # download it from the remote URL to a temporary file so we can attach it.
    temp_file_to_cleanup = None
    if not pdf_path and job.report_pdf_url and (job.report_pdf_url.startswith("http://") or job.report_pdf_url.startswith("https://")):
        import tempfile
        import httpx
        try:
            logger.info("Report PDF is not on local disk. Attempting to download from storage URL: %s", job.report_pdf_url)
            temp_dir = tempfile.gettempdir()
            temp_pdf_path = os.path.join(temp_dir, f"temp_report_{job_id}.pdf")
            
            with httpx.Client(timeout=15.0) as client:
                response = client.get(job.report_pdf_url)
                if response.status_code == 200:
                    with open(temp_pdf_path, "wb") as f:
                        f.write(response.content)
                    pdf_path = temp_pdf_path
                    temp_file_to_cleanup = temp_pdf_path
                    logger.info("Successfully downloaded report from storage to: %s", pdf_path)
                else:
                    logger.error("Failed to download report PDF from storage URL. HTTP Status: %s", response.status_code)
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to retrieve report from storage service"
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error downloading report PDF from storage: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve report from storage service"
            )

    from backend.app.services.reporter import ReportGenerator
    generator = ReportGenerator()
    success = False
    try:
        success = generator.send_email_report(
            to_email=recipient,
            report_url=job.report_pdf_url,
            job_id=job_id,
            counts=counts,
            repo_url=job.repo_url,
            pdf_path=pdf_path
        )
    finally:
        if temp_file_to_cleanup and os.path.exists(temp_file_to_cleanup):
            try:
                os.remove(temp_file_to_cleanup)
                logger.info("Cleaned up temporary report file: %s", temp_file_to_cleanup)
            except Exception as e:
                logger.warning("Failed to delete temp report file: %s", str(e))

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send report email.")

    return {"message": "Report email sent successfully", "recipient": recipient}


class UpdateAutoPushRequest(BaseModel):
    auto_push: bool


@router.patch("/job/{job_id}/auto-push")
async def update_job_auto_push(
    job_id: str,
    payload: UpdateAutoPushRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Update auto-push preference for a queued or running job."""
    job = get_owned_job_or_404(db, job_id, user_id)
    job.auto_push = payload.auto_push
    db.commit()
    return {"message": "Auto-push preference updated", "auto_push": job.auto_push}


# GitHub Repositories List and Bulk Scan Schemas
class GitHubRepoResponse(BaseModel):
    name: str
    full_name: str
    html_url: str
    default_branch: str
    private: bool

class SubmitBulkJobRequest(BaseModel):
    repo_urls: List[str]
    repo_branch: Optional[str] = "main"
    custom_email: Optional[str] = None
    auto_push: Optional[bool] = False


@router.get("/github-repos", response_model=List[GitHubRepoResponse])
@limiter.limit("15/minute")
async def list_github_repos(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve all GitHub repositories for the current authenticated user using their GitHub access token."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    if not user.github_access_token:
        raise HTTPException(
            status_code=400,
            detail="GitHub account not connected. Please authenticate using GitHub Login first."
        )
    
    try:
        token = decrypt_provider_token(user.github_access_token)
    except Exception as e:
        logger.error("Failed to decrypt github token: %s", str(e))
        raise HTTPException(status_code=500, detail="Secure token decryption failed.")

    async with httpx.AsyncClient() as client:
        try:
            # Fetch user's own repositories
            response = await client.get(
                "https://api.github.com/user/repos?per_page=100&sort=updated",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "FireCrow"
                },
                timeout=15.0
            )
            if response.status_code != 200:
                logger.error("GitHub API error: %s - %s", response.status_code, response.text)
                raise HTTPException(
                    status_code=400,
                    detail=f"GitHub API returned error: {response.status_code}"
                )
            
            repos_data = response.json()
            repos = []
            for repo in repos_data:
                repos.append(
                    GitHubRepoResponse(
                        name=repo.get("name", ""),
                        full_name=repo.get("full_name", ""),
                        html_url=repo.get("html_url", ""),
                        default_branch=repo.get("default_branch", "main"),
                        private=repo.get("private", False)
                    )
                )
            return repos
        except httpx.RequestError as exc:
            logger.error("Failed to connect to GitHub API: %s", str(exc))
            raise HTTPException(status_code=503, detail="GitHub API is unreachable.")


@router.get("/github-branches", response_model=List[str])
@limiter.limit("15/minute")
async def list_github_branches(
    request: Request,
    repo_url: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve all branches of a given GitHub repository using the current user's token."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    token = None
    if user.github_access_token:
        try:
            token = decrypt_provider_token(user.github_access_token)
        except Exception as e:
            logger.error("Failed to decrypt github token: %s", str(e))
            raise HTTPException(status_code=500, detail="Secure token decryption failed.")

    # Extract owner and repo from the URL
    url_str = repo_url.strip()
    match = re.match(r"^https?://github\.com/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)(?:\.git)?$", url_str)
    if not match:
        match = re.match(r"^git@github\.com:([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)(?:\.git)?$", url_str)
        
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    
    owner, repo = match.groups()
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "FireCrow"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=100",
                headers=headers,
                timeout=15.0
            )
            if response.status_code != 200:
                logger.error("GitHub API branches error: %s - %s", response.status_code, response.text)
                raise HTTPException(
                    status_code=400,
                    detail=f"GitHub API returned error: {response.status_code}"
                )
            
            branches_data = response.json()
            return [b.get("name") for b in branches_data if b.get("name")]
        except httpx.RequestError as exc:
            logger.error("Failed to connect to GitHub API: %s", str(exc))
            raise HTTPException(status_code=503, detail="GitHub API is unreachable.")


@router.post("/submit-bulk", response_model=List[JobResponse])
@limiter.limit("10/minute")
async def submit_bulk_audit(
    request: Request,
    payload: SubmitBulkJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Submit multiple security audit jobs for remote repositories. Enqueues tasks sequentially."""
    if not payload.repo_urls:
        raise HTTPException(status_code=400, detail="No repository URLs provided.")
    
    # We allow a higher limit for bulk audits (up to 50 active jobs)
    active_count = _active_job_count(db, user_id)
    if active_count + len(payload.repo_urls) > 50:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Active audit limit reached. Adding {len(payload.repo_urls)} jobs would exceed the max limit of 50 active audits.",
        )
    
    jobs = []
    for repo_url in payload.repo_urls:
        repo_url = repo_url.strip()
        # Basic validation (must match Github HTTP/HTTPS format)
        if not re.match(r"^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+(\.git)?$", repo_url):
            logger.warning("Skipping invalid repository URL: %s", repo_url)
            continue
            
        branch = (payload.repo_branch or "main").strip()
        
        job = AuditJob(
            user_id=user_id,
            repo_url=repo_url,
            repo_branch=branch,
            status=JobStatus.QUEUED,
            auto_push=payload.auto_push if payload.auto_push is not None else False
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        _dispatch_audit_job(
            background_tasks,
            job_id=job.id,
            user_id=user_id,
            repo_url=repo_url,
            repo_branch=branch,
            custom_email=payload.custom_email,
        )
        jobs.append(build_job_response(job))
        
    return jobs

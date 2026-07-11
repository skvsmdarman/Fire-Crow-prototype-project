import logging
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from app.services.limiter import limiter
from sqlalchemy.orm import Session
from typing import List
from urllib.parse import unquote, urlparse

from app.api.audit_queries import get_owned_job_or_404
from app.config import WORKSPACE_DIR, settings
from app.graph.store import graph_store
from app.models import (
    AgentLog,
    AuditArtifact,
    AuditJob,
    AuthorizationAttestation,
    FindingModel,
    Membership,
    User,
    DomainVerification,
    get_db,
)
from app.models.database import get_optional_db
from sqlalchemy import or_
from app.schemas import (
    JobDetailResponse,
    JobResponse,
    JobStatus,
    SubmitJobRequest,
    build_job_detail_response,
    build_job_response,
)
from app.orchestrator.runtime import execute_audit_job
from app.services.auth import get_current_user
from app.services.redaction import redact_text
from app.services.safe_llm import is_llm_enabled, safe_llm_call
from app.services.security_log import record_user_activity
from app.workers.celery_app import run_audit_job_task, celery_app

logger = logging.getLogger("firecrow.api.audit")
router = APIRouter(prefix="/audit", tags=["Security Auditing"])

REPORTS_DIR = WORKSPACE_DIR / "workspace" / "reports"

_bg_semaphore = asyncio.Semaphore(5)

import threading
from collections import defaultdict

_submission_locks = defaultdict(threading.Lock)
_locks_mutex = threading.Lock()

def _get_user_lock(user_id: str) -> threading.Lock:
    with _locks_mutex:
        return _submission_locks[user_id]


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
    custom_email: str = "",
) -> None:
    from app.services.auth import _get_redis_client
    redis_client = _get_redis_client()
    
    celery_alive = False
    if redis_client and redis_client.get("celery:heartbeat"):
        celery_alive = True

    if not celery_alive:
        logger.warning("Celery worker heartbeat missing or Redis unreachable. Falling back to local BackgroundTasks.")

        async def _run_with_limit():
            async with _bg_semaphore:
                await asyncio.to_thread(
                    execute_audit_job,
                    job_id,
                    user_id,
                    repo_url,
                    repo_branch,
                    custom_email,
                )
        background_tasks.add_task(_run_with_limit)
        return

    try:
        run_audit_job_task.apply_async(  # type: ignore
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
        async def _run_with_limit():
            async with _bg_semaphore:
                await asyncio.to_thread(
                    execute_audit_job,
                    job_id,
                    user_id,
                    repo_url,
                    repo_branch,
                    custom_email,
                )
        background_tasks.add_task(_run_with_limit)


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


def _persisted_report_html_response(db: Session, job_id: str) -> HTMLResponse | None:
    from app.models.audit_job import AuditReport
    report = db.query(AuditReport).filter(AuditReport.job_id == job_id).first()
    if report and report.html_content:
        return HTMLResponse(content=report.html_content)

    artifact = (
        db.query(AuditArtifact)
        .filter(
            AuditArtifact.job_id == job_id,
            AuditArtifact.artifact_type == "report_html",
        )
        .order_by(AuditArtifact.created_at.desc())
        .first()
    )
    if artifact and artifact.data_text:
        return HTMLResponse(content=artifact.data_text)
    return None


import hashlib

def _sha256_hash(val: str | None) -> str | None:
    if not val:
        return None
    return hashlib.sha256(val.encode("utf-8")).hexdigest()

def _extract_repo_owner_name(url: str) -> tuple[str, str]:
    match = re.match(r"^https://github\.com/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)(\.git)?$", url)
    if match:
        owner = match.group(1)
        name = match.group(2)
        if name.endswith(".git"):
            name = name[:-4]
        return owner, name
    return "unknown", "unknown"


def _extract_domain(url: str) -> str | None:
    try:
        if "github.com" in url:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split("/") if p]
            if len(path_parts) >= 2:
                repo_name = path_parts[1]
                if repo_name.endswith(".git"):
                    repo_name = repo_name[:-4]
                if re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$", repo_name.lower()):
                    return repo_name.lower()
        else:
            parsed = urlparse(url)
            netloc = parsed.netloc or parsed.path
            domain = netloc.split(":")[0].lower()
            if re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$", domain):
                return domain
    except Exception:
        pass
    return None


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
    if settings.DATABASE_BACKEND == "neo4j":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit submission is not enabled in Neo4j mode until the orchestrator persistence path is migrated.",
        )

    if payload.custom_email:
        from email_validator import validate_email, EmailNotValidError
        try:
            validate_email(payload.custom_email, check_deliverability=False)
        except EmailNotValidError as e:
            raise HTTPException(status_code=422, detail="Invalid email address format.")

    lock = _get_user_lock(user_id)
    with lock:
        db.rollback()  # Reset transaction snapshot to read latest committed data

        # Check domain verification if a domain-like target/repo is specified
        target_domain = _extract_domain(payload.repo_url)
        if target_domain:
            verified_record = (
                db.query(DomainVerification)
                .filter(
                    DomainVerification.domain == target_domain,
                    DomainVerification.user_id == user_id,
                    DomainVerification.verified == True,
                )
                .first()
            )
            if not verified_record:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"The domain '{target_domain}' must be verified before initiating a scan. "
                           f"Please register and verify domain '{target_domain}' in Settings.",
                )

        if _active_job_count(db, user_id) >= settings.MAX_ACTIVE_JOBS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Active audit limit reached. Complete or cancel an audit before starting more than {settings.MAX_ACTIVE_JOBS_PER_USER}.",
            )

        from app.services.auth import _get_redis_client
        redis_client = _get_redis_client()
        celery_alive = False
        if redis_client and redis_client.get("celery:heartbeat"):
            celery_alive = True

        if not celery_alive and _bg_semaphore.locked():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Server is currently at maximum background capacity. Please try again later.",
            )

        # Scoping job to user's tenant_id
        user = db.query(User).filter(User.id == user_id).with_for_update(of=User).first()
        tenant_id = user.tenant_id if user else None

        job = AuditJob(
            user_id=user_id,
            tenant_id=tenant_id,
            repo_url=payload.repo_url,
            repo_branch=payload.repo_branch,
            status=JobStatus.QUEUED
        )
        db.add(job)
        db.commit()
        db.refresh(job)

    # Create authorization attestation record for compliance logging
    owner, name = _extract_repo_owner_name(payload.repo_url)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    attestation = AuthorizationAttestation(
        organization_id=tenant_id or "default-tenant",
        user_id=user_id,
        repo_url_normalized=payload.repo_url,
        repo_url_hash=hashlib.sha256(payload.repo_url.encode("utf-8")).hexdigest(),
        repo_owner=owner,
        repo_name=name,
        branch=payload.repo_branch or "main",
        authorization_scope=payload.authorization_scope,
        attestation_text_version="v1",
        ip_hash=_sha256_hash(client_ip),
        user_agent_hash=_sha256_hash(user_agent),
        job_id=job.id,
    )
    db.add(attestation)
    db.commit()
    
    record_user_activity(
        db,
        user_id=user_id,
        action="audit.submit",
        request=request,
        details={
            "job_id": job.id,
            "repo_url": payload.repo_url,
            "repo_branch": payload.repo_branch,
        }
    )

    _dispatch_audit_job(
        background_tasks,
        job_id=job.id,
        user_id=user_id,
        repo_url=payload.repo_url,
        repo_branch=payload.repo_branch or "main",
        custom_email=payload.custom_email or "",
    )

    return build_job_response(job)


@router.get("/jobs", response_model=List[JobResponse])
@limiter.limit("30/minute")
async def list_jobs(
    request: Request,
    db: Session | None = Depends(get_optional_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve all jobs submitted by the current authenticated tenant (Tenant Isolation)."""
    if settings.DATABASE_BACKEND == "neo4j":
        jobs = graph_store.list_jobs_for_user(user_id)
        return [build_job_response(job) for job in jobs]

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    # Get all organization IDs from memberships
    memberships = db.query(Membership).filter(Membership.user_id == user_id).all()
    org_ids = [m.organization_id for m in memberships]
    if user.tenant_id:
        org_ids.append(user.tenant_id)

    query = db.query(AuditJob)
    if org_ids:
        jobs = query.filter(
            or_(
                AuditJob.user_id == user_id,
                AuditJob.tenant_id.in_(org_ids)
            )
        ).order_by(AuditJob.created_at.desc()).all()
    else:
        jobs = query.filter(AuditJob.user_id == user_id).order_by(AuditJob.created_at.desc()).all()

    return [build_job_response(job) for job in jobs]


@router.get("/job/{job_id}", response_model=JobDetailResponse)
@limiter.limit("30/minute")
async def get_job_detail(
    job_id: str,
    request: Request,
    db: Session | None = Depends(get_optional_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve details and findings of a specific job (scoped to authenticated tenant)."""
    job = get_owned_job_or_404(db, job_id, user_id)
    if settings.DATABASE_BACKEND == "neo4j":
        findings = graph_store.list_findings_for_job(job_id)
    else:
        findings = db.query(FindingModel).filter(FindingModel.job_id == job_id).all()

    return build_job_detail_response(job, findings)


@router.delete("/job/{job_id}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def cancel_job(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Request cancellation for a running or queued job and let the runtime finalize cleanup."""
    if settings.DATABASE_BACKEND == "neo4j":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit cancellation is not enabled in Neo4j mode until the orchestrator persistence path is migrated.",
        )

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

    record_user_activity(
        db,
        user_id=user_id,
        action="audit.cancel",
        request=request,
        details={
            "job_id": job_id,
            "repo_url": job.repo_url,
        }
    )

    return {"message": "Job cancellation request recorded successfully", "job_id": job_id}


@router.get("/job/{job_id}/report")
@limiter.limit("15/minute")
async def download_report(
    job_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Authenticated endpoint to download PDF reports."""
    if settings.DATABASE_BACKEND == "neo4j":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report download is not yet enabled in Neo4j mode.",
        )

    import os
    job = get_owned_job_or_404(db, job_id, user_id)

    record_user_activity(
        db,
        user_id=user_id,
        action="report.download",
        request=request,
        details={
            "job_id": job_id,
            "repo_url": job.repo_url,
            "report_pdf_url": job.report_pdf_url,
        }
    )

    # 1. Try structured database report first (on-the-fly compiling)
    from app.models.audit_job import AuditReport
    from app.services.report_service import generate_temp_pdf_report
    
    report = db.query(AuditReport).filter(AuditReport.job_id == job_id).first()
    if report and report.html_content:
        try:
            pdf_path = generate_temp_pdf_report(report.html_content, job_id)
            if os.path.exists(pdf_path):
                def cleanup_temp_pdf(path: str):
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                            logger.info("Deleted temporary PDF report at %s", path)
                    except Exception as e:
                        logger.error("Failed to delete temporary PDF report: %s", str(e))
                
                background_tasks.add_task(cleanup_temp_pdf, pdf_path)
                
                return FileResponse(
                    path=pdf_path,
                    filename=f"fire_crow_report_{job_id}.pdf",
                    media_type="application/pdf"
                )
        except Exception as e:
            logger.error("Failed to generate on-the-fly PDF report: %s", redact_text(str(e)))

    # 2. Legacy fallback
    if not job.report_pdf_url:
        raise HTTPException(status_code=404, detail="Report not ready or missing")

    if job.report_pdf_url.startswith("artifact://"):
        artifact_id = job.report_pdf_url.split("://")[1]
        from app.services.storage import storage_service
        try:
            if storage_service.is_s3_active():
                presigned_url = storage_service.get_presigned_url(db, artifact_id, user_id, expires_in=3600)
                return RedirectResponse(presigned_url)
            else:
                file_path, file_name, media_type = storage_service.download_artifact_local(db, artifact_id, user_id)
                html_path = file_path.with_suffix(".html")
                if file_path.suffix.lower() == ".pdf" and html_path.exists():
                    file_path = html_path
                    file_name = html_path.name
                    media_type = "text/html"

                if not file_path.exists():
                    html_response = _persisted_report_html_response(db, job_id)
                    if html_response is not None:
                        return html_response
                    raise HTTPException(status_code=404, detail="Report file not found on disk")

                return FileResponse(path=file_path, filename=file_name, media_type=media_type)
        except HTTPException as exc:
            if exc.status_code == 404:
                html_response = _persisted_report_html_response(db, job_id)
                if html_response is not None:
                    return html_response
            raise
        except Exception as e:
            logger.error("Failed to retrieve report artifact %s: %s", artifact_id, redact_text(str(e)))
            raise HTTPException(status_code=500, detail="Failed to retrieve report from storage service")

    parsed_report_url = urlparse(job.report_pdf_url)
    is_legacy_local_report = (
        parsed_report_url.scheme in {"http", "https"}
        and (parsed_report_url.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}
        and parsed_report_url.path.startswith("/reports/")
    )
    if job.report_pdf_url.startswith("/reports/") or is_legacy_local_report:
        file_path, file_name, media_type = _safe_local_report_path(job.report_pdf_url)

        html_path = file_path.with_suffix(".html")
        if file_path.suffix.lower() == ".pdf" and html_path.exists():
            file_path = html_path
            file_name = html_path.name
            media_type = "text/html"

        if not file_path.exists():
            html_response = _persisted_report_html_response(db, job_id)
            if html_response is not None:
                return html_response
            raise HTTPException(status_code=404, detail="Report file not found on disk")

        return FileResponse(path=file_path, filename=file_name, media_type=media_type)

    if _allowed_external_report_url(job.report_pdf_url):
        return RedirectResponse(job.report_pdf_url)

    logger.warning("Rejected unsafe report URL for job %s: %s", job_id, redact_text(job.report_pdf_url))
    raise HTTPException(status_code=400, detail="Report URL is not from an allowed storage location")


from pydantic import BaseModel
from typing import Optional

class EmailReportRequest(BaseModel):
    email: Optional[str] = None


_SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


@router.post("/job/{job_id}/email")
@limiter.limit("5/minute")
async def email_report(
    job_id: str,
    payload: EmailReportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """On-demand endpoint to send/resend the PDF report to a user via email."""
    if settings.DATABASE_BACKEND == "neo4j":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email report delivery is not yet enabled in Neo4j mode.",
        )

    if payload.email:
        from email_validator import validate_email, EmailNotValidError
        try:
            validate_email(payload.email, check_deliverability=False)
        except EmailNotValidError as e:
            raise HTTPException(status_code=422, detail="Invalid email address format.")

    import shutil
    from app.schemas.audit_state import Severity
    from app.services.reporter import ReportGenerator

    # 1. Resolves the user job details & compiled findings counts
    job = get_owned_job_or_404(db, job_id, user_id)
    findings = db.query(FindingModel).filter(FindingModel.job_id == job_id).all()

    counts = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 0,
        Severity.MEDIUM: 0,
        Severity.LOW: 0,
        Severity.INFO: 0,
    }
    for f in findings:
        sev = f.severity
        if isinstance(sev, str):
            try:
                sev = Severity(sev.lower())
            except ValueError:
                sev = Severity.INFO
        counts[sev] = counts.get(sev, 0) + 1

    # 2. Determines the recipient (either payload.email, or defaults to the user's GitHub email)
    recipient = payload.email
    if not recipient:
        user = db.query(User).filter(User.id == job.user_id).first()
        if user and user.email:
            recipient = user.email

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipient email could not be determined. Please specify an email address.",
        )

    # 3. Resolves the report and generates a temporary PDF if structured DB report exists
    from app.models.audit_job import AuditReport
    from app.services.report_service import generate_temp_pdf_report
    
    report = db.query(AuditReport).filter(AuditReport.job_id == job_id).first()
    
    temp_pdf_path = None
    email_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard?job_id={job_id}"
    
    if report and report.html_content:
        try:
            temp_pdf_path = generate_temp_pdf_report(report.html_content, job_id)
        except Exception as e:
            logger.error("Failed to generate temporary PDF report for email: %s", redact_text(str(e)))
            raise HTTPException(status_code=500, detail="Failed to prepare report attachment from database.")
    else:
        # Legacy fallback
        if not job.report_pdf_url:
            raise HTTPException(status_code=404, detail="Report not ready or missing")

        pdf_file_path = None
        if job.report_pdf_url.startswith("artifact://"):
            artifact_id = job.report_pdf_url.split("://")[1]
            from app.services.storage import storage_service
            try:
                file_path, file_name, media_type = storage_service.download_artifact_local(db, artifact_id, user_id)
                pdf_file_path = file_path
            except Exception as e:
                logger.error("Failed to retrieve report artifact %s: %s", artifact_id, redact_text(str(e)))
                raise HTTPException(status_code=500, detail="Failed to retrieve report from storage service")
        else:
            parsed_report_url = urlparse(job.report_pdf_url)
            is_legacy_local_report = (
                parsed_report_url.scheme in {"http", "https"}
                and (parsed_report_url.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}
                and parsed_report_url.path.startswith("/reports/")
            )
            if job.report_pdf_url.startswith("/reports/") or is_legacy_local_report:
                file_path, file_name, media_type = _safe_local_report_path(job.report_pdf_url)
                pdf_file_path = file_path

        if not pdf_file_path or not pdf_file_path.exists():
            raise HTTPException(status_code=404, detail="PDF report file not found on disk")

        # Make a copy of the PDF file to a temporary location so that send_email_report's finally block does not delete the original
        reports_dir = WORKSPACE_DIR / "workspace" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        temp_pdf_filename = f"temp_{job_id}_{pdf_file_path.name}"
        temp_pdf_path = reports_dir / temp_pdf_filename

        try:
            shutil.copy2(pdf_file_path, temp_pdf_path)
        except Exception as copy_err:
            logger.error("Failed to copy PDF report to temporary location: %s", redact_text(str(copy_err)))
            raise HTTPException(status_code=500, detail="Internal server error preparing report attachment")

        # Generate presigned URL specifically for the email link if remote storage
        email_url = job.report_pdf_url
        if job.report_pdf_url.startswith("artifact://"):
            artifact_id = job.report_pdf_url.split("://")[1]
            from app.services.storage import storage_service

            if storage_service.is_s3_active():
                try:
                    email_url = storage_service.get_presigned_url(db, artifact_id, user_id, expires_in=604800)  # type: ignore
                except Exception:
                    email_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard?job_id={job_id}"
            else:
                email_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard?job_id={job_id}"

    # 4. Invokes the ReportGenerator service to send the email immediately
    generator = ReportGenerator()

    success = generator.send_email_report(
        to_email=recipient,
        report_url=email_url,
        job_id=job_id,
        counts=counts,
        repo_url=job.repo_url,
        pdf_path=str(temp_pdf_path) if temp_pdf_path else None,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send report email.")

    record_user_activity(
        db,
        user_id=user_id,
        action="report.email",
        request=request,
        details={
            "job_id": job_id,
            "recipient": recipient,
        }
    )

    return {"message": "Email report triggered successfully.", "recipient": recipient}


@router.get("/job/{job_id}/insight")
@limiter.limit("20/minute")
async def get_job_insight(
    job_id: str,
    request: Request,
    db: Session | None = Depends(get_optional_db),
    user_id: str = Depends(get_current_user),
):
    if not is_llm_enabled("dashboard_insight"):
        return {"insight": None, "enabled": False}

    get_owned_job_or_404(db, job_id, user_id)
    if settings.DATABASE_BACKEND == "neo4j":
        findings = graph_store.list_findings_for_job(job_id)
    else:
        findings = db.query(FindingModel).filter(FindingModel.job_id == job_id).all()
    if not findings:
        return {"insight": "No findings to summarize.", "enabled": True}

    ranked_findings = sorted(
        findings,
        key=lambda finding: (
            -_SEVERITY_RANK.get(
                finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity).lower(),
                0,
            ),
            finding.title.lower(),
        ),
    )[:5]

    prompt = "Findings from security audit:\n"
    prompt += "\n".join(
        f"- {(finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)).upper()}: {finding.title}"
        for finding in ranked_findings
    )
    prompt += "\nWrite one short sentence, maximum 15 words, summarizing the overall risk."

    insight = safe_llm_call(prompt, max_tokens=30, temperature=0.2)
    return {"insight": insight, "enabled": True}


@router.get("/job/{job_id}/graph")
@limiter.limit("20/minute")
async def get_attack_graph(
    job_id: str,
    request: Request,
    db: Session | None = Depends(get_optional_db),
    user_id: str = Depends(get_current_user)
):
    job = get_owned_job_or_404(db, job_id, user_id)
    if settings.DATABASE_BACKEND == "neo4j":
        artifact = graph_store.get_artifact_for_job(job_id, "attack_graph")
    else:
        from app.models import AuditArtifact
        artifact = db.query(AuditArtifact).filter(
            AuditArtifact.job_id == job_id,
            AuditArtifact.artifact_type == "attack_graph"
        ).first()
    if not artifact or not artifact.data_json:
        raise HTTPException(404, "Attack graph not generated yet")
    import json
    from fastapi.responses import JSONResponse
    return JSONResponse(content=json.loads(artifact.data_json))

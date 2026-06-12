from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from backend.app.models import AgentLog, AuditJob, FindingModel, SessionLocal, User
from backend.app.orchestrator.maestro import cleanup_resources, maestro_graph
from backend.app.orchestrator.runtime_context import (
    JobCancellationRequested,
    get_runtime_state,
    get_runtime_tracker,
    initialize_runtime_tracker,
    reset_runtime_tracker,
)
from backend.app.schemas import AuditState, JobStatus
from backend.app.services.auth import decrypt_provider_token

logger = logging.getLogger("firecrow.orchestrator.runtime")


def execute_audit_job(job_id: str, user_id: str, repo_url: str, repo_branch: str, custom_email: Optional[str] = None) -> AuditState:
    db = SessionLocal()
    initial_state = AuditState(
        job_id=job_id,
        user_id=user_id,
        repo_url=repo_url,
        repo_branch=repo_branch,
        custom_email=custom_email or "",
        status=JobStatus.RUNNING,
    )
    tracker_token = initialize_runtime_tracker(initial_state)
    result_state: AuditState = initial_state
    job: AuditJob | None = None
    execution_error: Exception | None = None

    try:
        job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
        if not job:
            raise RuntimeError(f"Job {job_id} not found in database.")

        user = db.query(User).filter(User.id == user_id).first()
        if user:
            initial_state.github_access_token = decrypt_provider_token(user.github_access_token)
            initial_state.github_token_scopes = [
                scope.strip()
                for scope in (user.github_token_scopes or "").split(",")
                if scope.strip()
            ]

        if job.cancel_requested:
            raise JobCancellationRequested("Cancellation requested before orchestration started.")

        job.status = JobStatus.RUNNING
        job.finished_at = None
        job.error_message = None
        db.add(
            AgentLog(
                job_id=job_id,
                agent_name="MAESTRO",
                log_level="INFO",
                message=f"Orchestrator pipeline started for {repo_url} (branch: {repo_branch})",
            )
        )
        db.commit()

        graph_result = maestro_graph.invoke(initial_state)
        result_state = AuditState.model_validate(graph_result)
    except Exception as exc:
        execution_error = exc
        if not isinstance(exc, JobCancellationRequested):
            logger.exception("Audit job %s failed during orchestration.", job_id)
    finally:
        tracked_state = get_runtime_state()

        tracker = get_runtime_tracker()
        if tracker is None or not tracker.cleanup_completed:
            try:
                cleanup_resources(tracked_state)
            except Exception as cleanup_error:
                logger.exception("Cleanup failed for job %s: %s", job_id, cleanup_error)
                if execution_error is None:
                    execution_error = cleanup_error

        terminal_status = _resolve_terminal_status(db, job_id, tracked_state, execution_error)

        # Persist final state with retry — this is critical for the SSE stream
        # to detect the terminal status and unblock the frontend.
        persist_succeeded = False
        for attempt in range(3):
            try:
                _persist_final_job_state(db, job_id, tracked_state, terminal_status, execution_error)
                persist_succeeded = True
                break
            except Exception as persist_error:
                logger.error(
                    "Failed to persist final state for job %s (attempt %d/3): %s",
                    job_id, attempt + 1, persist_error,
                )
                if attempt < 2:
                    time.sleep(1)

        if not persist_succeeded:
            # Last-resort: try a minimal status-only update with a fresh session
            try:
                emergency_db = SessionLocal()
                emergency_job = emergency_db.query(AuditJob).filter(AuditJob.id == job_id).first()
                if emergency_job:
                    emergency_job.status = terminal_status
                    emergency_job.finished_at = datetime.now(timezone.utc)
                    emergency_job.error_message = "Job completed but failed to persist full state. Check server logs."
                    emergency_db.commit()
                    logger.warning("Emergency persist succeeded for job %s with status %s", job_id, terminal_status)
                emergency_db.close()
            except Exception as emergency_error:
                logger.critical(
                    "CRITICAL: All attempts to persist final state for job %s failed. "
                    "Job will remain stuck in running state. Error: %s",
                    job_id, emergency_error,
                )

        tracked_state.status = terminal_status
        result_state = tracked_state
        reset_runtime_tracker(tracker_token)
        db.close()

    return result_state


def _resolve_terminal_status(
    db,
    job_id: str,
    state: AuditState,
    execution_error: Exception | None,
) -> JobStatus:
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if job and job.cancel_requested:
        return JobStatus.CANCELLED

    if isinstance(execution_error, JobCancellationRequested):
        return JobStatus.CANCELLED

    if execution_error is None:
        return state.status if state.status in {JobStatus.COMPLETED, JobStatus.PARTIAL} else JobStatus.COMPLETED

    has_partial_output = bool(
        state.report_pdf_url
        or state.static_findings
        or state.dynamic_findings
        or state.exploit_proofs
        or db.query(FindingModel).filter(FindingModel.job_id == job_id).first()
    )
    return JobStatus.PARTIAL if has_partial_output else JobStatus.FAILED


def _persist_final_job_state(
    db,
    job_id: str,
    state: AuditState,
    terminal_status: JobStatus,
    execution_error: Exception | None,
) -> None:
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        return

    job.status = terminal_status
    job.finished_at = datetime.now(timezone.utc)
    job.report_pdf_url = state.report_pdf_url or job.report_pdf_url

    if terminal_status == JobStatus.CANCELLED:
        job.error_message = None
    elif execution_error:
        job.error_message = "Audit job failed during orchestration. Review server logs with the job ID for details."
    else:
        job.error_message = None

    final_message = {
        JobStatus.COMPLETED: "Audit job completed successfully.",
        JobStatus.PARTIAL: "Audit job completed partially after a recoverable orchestration failure.",
        JobStatus.FAILED: "Audit job failed before completing the orchestration pipeline.",
        JobStatus.CANCELLED: "Audit job finalized after user cancellation request.",
    }[terminal_status]
    final_level = "ERROR" if terminal_status == JobStatus.FAILED else "WARNING" if terminal_status in {JobStatus.PARTIAL, JobStatus.CANCELLED} else "INFO"

    db.add(
        AgentLog(
            job_id=job_id,
            agent_name="MAESTRO",
            log_level=final_level,
            message=final_message,
        )
    )
    db.commit()

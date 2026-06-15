from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone

from app.config import settings
from app.models import AgentLog, AuditJob, FindingModel, SessionLocal, User
from app.orchestrator.maestro import cleanup_resources, maestro_graph
from app.orchestrator.runtime_context import (
    JobCancellationRequested,
    get_runtime_state,
    get_runtime_tracker,
    initialize_runtime_tracker,
    reset_runtime_tracker,
)
from app.schemas import AuditState, JobStatus
from app.services.auth import decrypt_provider_token

logger = logging.getLogger("firecrow.orchestrator.runtime")

_executor = ThreadPoolExecutor(max_workers=2)


def execute_audit_job(job_id: str, user_id: str, repo_url: str, repo_branch: str, custom_email: str = "") -> AuditState:
    db = SessionLocal()
    initial_state = AuditState(
        job_id=job_id,
        user_id=user_id,
        repo_url=repo_url,
        repo_branch=repo_branch,
        status=JobStatus.RUNNING,
        custom_email=custom_email,
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

        try:
            future = _executor.submit(maestro_graph.invoke, initial_state)
            graph_result = future.result(timeout=settings.MAX_SCAN_DURATION)
            result_state = AuditState.model_validate(graph_result)
        except FuturesTimeoutError:
            execution_error = TimeoutError(f"Orchestration exceeded maximum scan duration of {settings.MAX_SCAN_DURATION}s")
            logger.error("Audit job %s timed out after %ds", job_id, settings.MAX_SCAN_DURATION)
            
            from app.orchestrator.runtime_context import get_runtime_tracker as get_tracker
            tracker = get_tracker()
            if tracker:
                tracker_state = tracker.state

                result_state = AuditState(
                    job_id=job_id,
                    user_id=user_id,
                    repo_url=repo_url,
                    repo_branch=repo_branch,
                    status=JobStatus.FAILED,
                    errors=[{"phase": "orchestration", "message": f"Scan timed out after {settings.MAX_SCAN_DURATION}s"}],
                    custom_email=custom_email,
                    sandbox_container_id=tracker_state.get("sandbox_container_id", ""),
                )
                from app.orchestrator.runtime_context import sync_runtime_state
                sync_runtime_state(result_state)
        except Exception as exc:
            execution_error = exc
            if not isinstance(exc, JobCancellationRequested):
                logger.exception("Orchestrator graph execution or state validation failed: %s", exc)

                from app.orchestrator.runtime_context import get_runtime_tracker as get_tracker
                tracker = get_tracker()
                if tracker:
                    tracker_state = tracker.state

                    # Fallback to a safe, failed state while preserving state collected so far
                    result_state = AuditState(
                        job_id=job_id,
                        user_id=user_id,
                        repo_url=repo_url,
                        repo_branch=repo_branch,
                        status=JobStatus.FAILED,
                        errors=[{"phase": "orchestration", "message": f"State validation failed: {str(exc)}"}],
                        custom_email=custom_email,
                        sandbox_container_id=tracker_state.get("sandbox_container_id", ""),
                    )
                    # Ensure get_runtime_state() returns this fallback if accessed downstream
                    from app.orchestrator.runtime_context import sync_runtime_state
                    sync_runtime_state(result_state)
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
        _persist_final_job_state(db, job_id, tracked_state, terminal_status, execution_error)
        tracked_state.status = terminal_status
        result_state = tracked_state
        reset_runtime_tracker(tracker_token)
        try:
            from app.services.housekeeping import run_housekeeping
            run_housekeeping(db)
        except Exception as hk_err:
            logger.exception("Failed to run DB housekeeping after job execution: %s", hk_err)
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

    # Trigger Push Notification
    try:
        from app.models import PushSubscription
        from app.services.push_notify import send_web_push
        import json
        
        subscriptions = db.query(PushSubscription).filter(PushSubscription.user_id == job.user_id).all()
        if subscriptions:
            repo_name = job.repo_url.split("/")[-1] if "/" in job.repo_url else job.repo_url
            score_text = f" (Score: {job.security_score:.0f})" if job.security_score is not None else ""
            payload = {
                "title": "Fire Crow Audit Finished",
                "body": f"Audit for {repo_name} finished: {terminal_status.value}{score_text}."
            }
            payload_str = json.dumps(payload)
            for sub in subscriptions:
                sub_info = {
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    }
                }
                send_web_push(sub_info, payload_str)
    except Exception:
        logger.exception("Failed to send push notifications for job finalization")


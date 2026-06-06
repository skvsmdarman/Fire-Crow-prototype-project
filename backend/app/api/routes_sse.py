import asyncio
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import AsyncGenerator

from backend.app.api.audit_queries import get_owned_job_or_404
from backend.app.models import get_db, AuditJob, AgentLog
from backend.app.schemas import JobStatus
from backend.app.services.auth import get_current_user
from backend.app.services.redaction import redact_text

router = APIRouter(prefix="/audit", tags=["Security Auditing Stream"])
logger = logging.getLogger("firecrow.sse")


@router.get("/{job_id}/stream")
async def stream_audit_logs(
    job_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Establish a Server-Sent Events (SSE) stream for live agent log updates.
    Ensures tenant isolation by checking job ownership before streaming.
    """
    get_owned_job_or_404(db, job_id, user_id)

    async def log_generator() -> AsyncGenerator[str, None]:
        last_seen_log_id = 0
        connection_active = True

        # Send initial connection success event
        yield f"event: connect\ndata: {json.dumps({'status': 'connected', 'job_id': job_id})}\n\n"

        while connection_active:
            # We create a new DB session inside the loop to avoid keeping the transaction open long-term
            # and to fetch the latest state updates.
            from backend.app.models import SessionLocal
            loop_db = SessionLocal()
            try:
                # Refresh job status
                current_job = (
                    loop_db.query(AuditJob)
                    .filter(AuditJob.id == job_id, AuditJob.user_id == user_id)
                    .first()
                )
                if not current_job:
                    yield f"event: error\ndata: {json.dumps({'error': 'Job is unavailable or access is no longer authorized'})}\n\n"
                    break

                # Fetch new logs
                new_logs = (
                    loop_db.query(AgentLog)
                    .filter(AgentLog.job_id == job_id, AgentLog.id > last_seen_log_id)
                    .order_by(AgentLog.id.asc())
                    .all()
                )

                for log in new_logs:
                    payload = {
                        "id": log.id,
                        "agent_name": log.agent_name,
                        "log_level": log.log_level,
                        "message": log.message,
                        "timestamp": log.timestamp.isoformat()
                    }
                    yield f"event: log\ndata: {json.dumps(payload)}\n\n"
                    last_seen_log_id = log.id

                # If job finished, send terminal event and terminate stream
                if current_job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.PARTIAL]:
                    terminal_payload = {
                        "status": current_job.status.value,
                        "finished_at": current_job.finished_at.isoformat() if current_job.finished_at else None,
                        "cancel_requested": current_job.cancel_requested,
                        "cancel_requested_at": current_job.cancel_requested_at.isoformat() if current_job.cancel_requested_at else None,
                        "report_pdf_url": current_job.report_pdf_url,
                        "error_message": "Audit did not complete successfully. Review job logs for operational context."
                        if current_job.error_message
                        else None,
                    }
                    yield f"event: complete\ndata: {json.dumps(terminal_payload)}\n\n"
                    connection_active = False
                    break

            except Exception as e:
                logger.exception("Error in SSE stream for job %s: %s", job_id, redact_text(str(e)))
                yield f"event: error\ndata: {json.dumps({'error': 'Stream interrupted. Please reconnect.'})}\n\n"
                break
            finally:
                loop_db.close()

            # Wait 1.5 seconds before querying database again
            await asyncio.sleep(1.5)

    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for Nginx reverse proxies
        }
    )

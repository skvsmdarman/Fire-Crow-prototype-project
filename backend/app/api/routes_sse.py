import asyncio
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import AsyncGenerator

from app.api.audit_queries import get_owned_job_or_404
from app.models import get_db, AuditJob, AgentLog
from app.schemas import JobStatus
from app.services.auth import get_current_user
from app.services.redaction import redact_text
from collections import defaultdict
import uuid

MAX_SSE_CONNECTIONS_PER_USER = 3
_active_connections = defaultdict(set)

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
    if user_id in _active_connections and len(_active_connections[user_id]) >= MAX_SSE_CONNECTIONS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum number of active streams ({MAX_SSE_CONNECTIONS_PER_USER}) reached."
        )

    try:
        get_owned_job_or_404(db, job_id, user_id)
    finally:
        db.close()

    conn_id = str(uuid.uuid4())

    async def log_generator() -> AsyncGenerator[str, None]:
        _active_connections[user_id].add(conn_id)
        try:
            from datetime import datetime, timezone

            last_seen_log_id = 0
            connection_active = True
            last_heartbeat_time = datetime.now(timezone.utc).timestamp()

            # Send initial connection success event
            yield f"event: connect\ndata: {json.dumps({'status': 'connected', 'job_id': job_id})}\n\n"

            while connection_active:
                # We create a new DB session inside the loop to avoid keeping the transaction open long-term
                # and to fetch the latest state updates.
                from app.models import SessionLocal
                loop_db = SessionLocal()
                try:
                    # Refresh job status
                    try:
                        current_job = get_owned_job_or_404(loop_db, job_id, user_id)
                    except HTTPException:
                        yield f"event: error\ndata: {json.dumps({'error': 'Job is unavailable or access is no longer authorized'})}\n\n"
                        break

                    # Fetch new logs
                    new_logs = (
                        loop_db.query(AgentLog)
                        .filter(AgentLog.job_id == job_id, AgentLog.id > last_seen_log_id)
                        .order_by(AgentLog.id.asc())
                        .all()
                    )

                    # Map progress deterministically
                    def get_progress(status_val, current_agent):
                        if status_val in ["completed"]: return 100
                        if status_val in ["failed", "cancelled"]: return 100 # Frontend will handle state

                        mapping = {
                            "MAESTRO": 5,
                            "RECON": 15,
                            "SANDBOX": 25,
                            "SAST": 40,
                            "DEPENDENCY": 50,
                            "IAC": 55,
                            "ATTACK": 60,
                            "API_SURFACE": 65,
                            "AI_ANALYZER": 75,
                            "REPORTER": 90,
                            "STORAGE": 95
                        }
                        return mapping.get(current_agent, 50)

                    for log in new_logs:
                        prog = get_progress(current_job.status.value, log.agent_name)

                        payload = {
                            "id": log.id,
                            "agent_name": log.agent_name,
                            "log_level": log.log_level,
                            "message": log.message,
                            "timestamp": log.timestamp.isoformat(),
                            "progress": prog,
                            "stage": log.agent_name.lower()
                        }
                        yield f"event: log\ndata: {json.dumps(payload)}\n\n"
                        last_seen_log_id = log.id

                    if new_logs:
                        last_heartbeat_time = datetime.now(timezone.utc).timestamp()
                    else:
                        current_time = datetime.now(timezone.utc).timestamp()
                        if current_time - last_heartbeat_time >= 15.0:
                            yield ": keepalive\n\n"
                            last_heartbeat_time = current_time

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
        
        # Outer finally block (cleanup when generator exits)
        except GeneratorExit:
            pass
        finally:
            _active_connections[user_id].discard(conn_id)
            if not _active_connections[user_id]:
                del _active_connections[user_id]

    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for Nginx reverse proxies
        }
    )

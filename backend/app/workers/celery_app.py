import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

from app.config import settings
from app.orchestrator.runtime import execute_audit_job

logger = logging.getLogger("firecrow.celery")

# Initialize Celery
celery_app = Celery(
    "firecrow",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_timeout=1,
    broker_transport_options={"socket_connect_timeout": 1, "socket_timeout": 1},
    result_backend_transport_options={"socket_connect_timeout": 1, "socket_timeout": 1},
)


@celery_app.task(bind=True, name="run_audit_job_task")
def run_audit_job_task(self, job_id: str, user_id: str, repo_url: str, repo_branch: str, custom_email: str = ""):
    """Celery task that executes the orchestrator LangGraph pipeline for an audit job."""
    logger.info(f"Starting Celery background job {job_id} for user {user_id}")
    final_state = execute_audit_job(
        job_id=job_id,
        user_id=user_id,
        repo_url=repo_url,
        repo_branch=repo_branch,
        custom_email=custom_email,
    )
    logger.info(f"Celery background job {job_id} finished with terminal status {final_state.status.value}.")
    return final_state.model_dump(mode="json")


@celery_app.task(name="heartbeat")
def heartbeat():
    from app.services.auth import _get_redis_client
    redis_client = _get_redis_client()
    if redis_client:
        redis_client.setex("celery:heartbeat", 60, "alive")


# Update Prometheus metrics for job processing
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kw):
    """Update metrics when a task starts"""
    try:
        from prometheus_client import Gauge  # type: ignore
        # Update active jobs gauge (we'll need to query DB for actual counts)
        # This is a placeholder - in reality we'd query the database
        task_name = task.name if task else "unknown"
        logger.debug(f"Task {task_name}[{task_id}] started with args={args}, kwargs={kwargs}")
    except Exception as e:
        logger.debug(f"Could not update task start metrics: {e}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kw):
    """Update metrics when a task completes successfully"""
    try:
        if task and hasattr(task, 'name') and task.name and 'run_audit_job_task' in task.name:
            # This is an audit job task - update audit job metrics
            from app.middleware.telemetry import AUDIT_JOBS_TOTAL
            if AUDIT_JOBS_TOTAL is not None:
                AUDIT_JOBS_TOTAL.labels(status="completed").inc()
            logger.debug(f"Task {task.name}[{task_id}] completed successfully")
    except Exception as e:
        logger.debug(f"Could not update task completion metrics: {e}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kw):
    """Update metrics when a task fails"""
    try:
        if sender and hasattr(sender, 'name') and sender.name and 'run_audit_job_task' in sender.name:
            # This is an audit job task that failed
            from app.middleware.telemetry import AUDIT_JOBS_TOTAL
            if AUDIT_JOBS_TOTAL is not None:
                AUDIT_JOBS_TOTAL.labels(status="failed").inc()
            logger.debug(f"Task {sender.name}[{task_id}] failed: {exception}")
    except Exception as e:
        logger.debug(f"Could not update task failure metrics: {e}")


celery_app.conf.beat_schedule = {
    'heartbeat-every-30s': {
        'task': 'heartbeat',
        'schedule': 30.0,
    },
}


from celery.signals import worker_ready
@worker_ready.connect
def on_worker_ready(**kwargs):
    """Mark jobs that were running when worker died as failed/interrupted."""
    logger.info("Worker ready. Checking for orphaned jobs.")
    try:
        from app.models import AuditJob, AgentLog, get_db, SessionLocal
        from app.schemas import JobStatus
        from datetime import datetime, timezone

        db = SessionLocal()
        orphaned = db.query(AuditJob).filter(AuditJob.status == JobStatus.RUNNING).all()
        for job in orphaned:
            job.status = JobStatus.FAILED
            job.error_message = "Audit job was interrupted by a server restart or deployment. Please try again."
            job.finished_at = datetime.now(timezone.utc)
            db.add(AgentLog(
                job_id=job.id,
                agent_name="SYSTEM",
                log_level="ERROR",
                message="Job marked as FAILED due to unexpected worker restart."
            ))
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to check for orphaned jobs on startup: {e}")

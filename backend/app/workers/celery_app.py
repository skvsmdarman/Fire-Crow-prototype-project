import logging
from celery import Celery

from backend.app.config import settings
from backend.app.orchestrator.runtime import execute_audit_job

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
    from backend.app.services.auth import _get_redis_client
    redis_client = _get_redis_client()
    if redis_client:
        redis_client.setex("celery:heartbeat", 60, "alive")

celery_app.conf.beat_schedule = {
    'heartbeat-every-30s': {
        'task': 'heartbeat',
        'schedule': 30.0,
    },
}

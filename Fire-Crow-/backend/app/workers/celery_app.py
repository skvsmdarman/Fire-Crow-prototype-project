import logging
from typing import Any, Callable

from app.config import settings
from app.orchestrator.runtime import execute_audit_job

logger = logging.getLogger("firecrow.celery")


class _FallbackSignal:
    def __init__(self, name: str) -> None:
        self.name = name
        self.handlers: list[Callable[..., Any]] = []

    def connect(self, func: Callable[..., Any] | None = None, **kwargs: Any):
        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            self.handlers.append(handler)
            return handler

        if func is not None:
            return decorator(func)
        return decorator


class _FallbackConf:
    def __init__(self) -> None:
        self.beat_schedule: dict[str, Any] = {}

    def update(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FallbackControl:
    def revoke(self, *args: Any, **kwargs: Any) -> None:
        logger.info("Celery is unavailable; skipping revoke request for args=%s kwargs=%s", args, kwargs)


class _FallbackSignature:
    def __init__(self, task_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.task_name = task_name
        self.args = args
        self.kwargs = kwargs

    def __repr__(self) -> str:
        return f"<FallbackSignature task={self.task_name!r} args={self.args!r} kwargs={self.kwargs!r}>"


class _FallbackCeleryApp:
    def __init__(self) -> None:
        self.main = "firecrow"
        self.conf = _FallbackConf()
        self.control = _FallbackControl()
        self.on_after_configure = _FallbackSignal("on_after_configure")
        self.tasks: dict[str, Callable[..., Any]] = {}

    def task(self, *task_args: Any, **task_kwargs: Any):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            task_name = task_kwargs.get("name", func.__name__)
            self.tasks[task_name] = func

            def apply_async(*args: Any, **kwargs: Any) -> Any:
                raise RuntimeError(
                    "Celery is unavailable in this environment. "
                    "The audit task will fall back to synchronous execution."
                )

            def delay(*args: Any, **kwargs: Any) -> Any:
                return apply_async(*args, **kwargs)

            def signature(*args: Any, **kwargs: Any) -> _FallbackSignature:
                return _FallbackSignature(task_name, args, kwargs)

            func.apply_async = apply_async  # type: ignore[attr-defined]
            func.delay = delay  # type: ignore[attr-defined]
            func.s = signature  # type: ignore[attr-defined]
            func.si = signature  # type: ignore[attr-defined]
            func.name = task_name  # type: ignore[attr-defined]
            return func

        if len(task_args) == 1 and callable(task_args[0]) and not task_kwargs:
            return decorator(task_args[0])
        return decorator


try:
    from celery import Celery
    from celery.signals import task_failure, task_postrun, task_prerun, worker_ready

    CELERY_AVAILABLE = True
    celery_import_error: Exception | None = None
except Exception as exc:
    Celery = None  # type: ignore[assignment]
    task_prerun = _FallbackSignal("task_prerun")  # type: ignore[assignment]
    task_postrun = _FallbackSignal("task_postrun")  # type: ignore[assignment]
    task_failure = _FallbackSignal("task_failure")  # type: ignore[assignment]
    worker_ready = _FallbackSignal("worker_ready")  # type: ignore[assignment]
    CELERY_AVAILABLE = False
    celery_import_error = exc
    logger.warning(
        "Celery import failed; using fallback task wrappers. Root cause: %s: %s",
        type(exc).__name__,
        exc,
    )


celery_app = (
    Celery(
        "firecrow",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )
    if CELERY_AVAILABLE
    else _FallbackCeleryApp()
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


def _execute_audit_job_task(
    job_id: str,
    user_id: str,
    repo_url: str,
    repo_branch: str,
    custom_email: str = "",
):
    """Run the audit pipeline and return the serialized terminal state."""
    logger.info("Starting Celery background job %s for user %s", job_id, user_id)
    final_state = execute_audit_job(
        job_id=job_id,
        user_id=user_id,
        repo_url=repo_url,
        repo_branch=repo_branch,
        custom_email=custom_email,
    )
    logger.info(
        "Celery background job %s finished with terminal status %s.",
        job_id,
        final_state.status.value,
    )
    return final_state.model_dump(mode="json")


if CELERY_AVAILABLE:

    @celery_app.task(bind=True, name="run_audit_job_task")
    def run_audit_job_task(self, job_id: str, user_id: str, repo_url: str, repo_branch: str, custom_email: str = ""):
        """Celery task that executes the orchestrator LangGraph pipeline for an audit job."""
        return _execute_audit_job_task(job_id, user_id, repo_url, repo_branch, custom_email)

else:

    def run_audit_job_task(self, job_id: str, user_id: str, repo_url: str, repo_branch: str, custom_email: str = ""):
        """Fallback entry point kept import-safe when Celery cannot initialize."""
        return _execute_audit_job_task(job_id, user_id, repo_url, repo_branch, custom_email)

    def _fallback_apply_async(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            "Celery is unavailable in this environment. "
            "The audit task will fall back to synchronous execution."
        )

    run_audit_job_task.apply_async = _fallback_apply_async  # type: ignore[attr-defined]
    run_audit_job_task.delay = _fallback_apply_async  # type: ignore[attr-defined]
    run_audit_job_task.s = lambda *args, **kwargs: _FallbackSignature("run_audit_job_task", args, kwargs)  # type: ignore[attr-defined]
    run_audit_job_task.si = run_audit_job_task.s  # type: ignore[attr-defined]
    run_audit_job_task.name = "run_audit_job_task"  # type: ignore[attr-defined]


if CELERY_AVAILABLE:

    @celery_app.task(name="heartbeat")
    def heartbeat():
        from app.services.auth import _get_redis_client

        redis_client = _get_redis_client()
        if redis_client:
            redis_client.setex("celery:heartbeat", 60, "alive")

else:

    def heartbeat():
        from app.services.auth import _get_redis_client

        redis_client = _get_redis_client()
        if redis_client:
            redis_client.setex("celery:heartbeat", 60, "alive")

    heartbeat.apply_async = _fallback_apply_async  # type: ignore[attr-defined]
    heartbeat.delay = _fallback_apply_async  # type: ignore[attr-defined]
    heartbeat.s = lambda *args, **kwargs: _FallbackSignature("heartbeat", args, kwargs)  # type: ignore[attr-defined]
    heartbeat.si = heartbeat.s  # type: ignore[attr-defined]
    heartbeat.name = "heartbeat"  # type: ignore[attr-defined]


# Update Prometheus metrics for job processing
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kw):
    """Update metrics when a task starts"""
    try:
        from prometheus_client import Gauge  # type: ignore

        # Update active jobs gauge (we'll need to query DB for actual counts)
        # This is a placeholder - in reality we'd query the database
        task_name = task.name if task else "unknown"
        logger.debug("Task %s[%s] started with args=%s, kwargs=%s", task_name, task_id, args, kwargs)
    except Exception as e:
        logger.debug("Could not update task start metrics: %s", e)


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kw):
    """Update metrics when a task completes successfully"""
    try:
        if task and hasattr(task, "name") and task.name and "run_audit_job_task" in task.name:
            # This is an audit job task - update audit job metrics
            from app.middleware.telemetry import AUDIT_JOBS_TOTAL

            if AUDIT_JOBS_TOTAL is not None:
                AUDIT_JOBS_TOTAL.labels(status="completed").inc()
            logger.debug("Task %s[%s] completed successfully", task.name, task_id)
    except Exception as e:
        logger.debug("Could not update task completion metrics: %s", e)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kw):
    """Update metrics when a task fails"""
    try:
        if sender and hasattr(sender, "name") and sender.name and "run_audit_job_task" in sender.name:
            # This is an audit job task that failed
            from app.middleware.telemetry import AUDIT_JOBS_TOTAL

            if AUDIT_JOBS_TOTAL is not None:
                AUDIT_JOBS_TOTAL.labels(status="failed").inc()
            logger.debug("Task %s[%s] failed: %s", sender.name, task_id, exception)
    except Exception as e:
        logger.debug("Could not update task failure metrics: %s", e)


celery_app.conf.beat_schedule = {
    "heartbeat-every-30s": {
        "task": "heartbeat",
        "schedule": 30.0,
    },
}


@worker_ready.connect
def on_worker_ready(**kwargs):
    """Mark jobs that were running when worker died as failed/interrupted."""
    logger.info("Worker ready. Checking for orphaned jobs.")
    try:
        from datetime import datetime, timezone

        from app.models import AgentLog, AuditJob, SessionLocal
        from app.schemas import JobStatus

        db = SessionLocal()
        orphaned = db.query(AuditJob).filter(AuditJob.status == JobStatus.RUNNING).all()
        for job in orphaned:
            job.status = JobStatus.FAILED
            job.error_message = "Audit job was interrupted by a server restart or deployment. Please try again."
            job.finished_at = datetime.now(timezone.utc)
            db.add(
                AgentLog(
                    job_id=job.id,
                    agent_name="SYSTEM",
                    log_level="ERROR",
                    message="Job marked as FAILED due to unexpected worker restart.",
                )
            )
        db.commit()
        db.close()
    except Exception as e:
        logger.error("Failed to check for orphaned jobs on startup: %s", e)

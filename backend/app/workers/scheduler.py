import logging
from datetime import datetime
from backend.app.workers.celery_app import celery_app

logger = logging.getLogger("firecrow.scheduler")

from typing import Any

celery_any: Any = celery_app

@celery_any.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls trigger_scheduled_scans every day
    sender.add_periodic_task(
        86400.0,
        trigger_scheduled_scans.s(),  # type: ignore
        name='daily_scheduled_scans'
    )

@celery_app.task
def trigger_scheduled_scans():
    """
    Looks up all scheduled recurring scans in the database and dispatches Celery tasks.
    """
    logger.info(f"Triggering scheduled recurring scans at {datetime.now()}")
    # DB logic to find due scans and dispatch would go here.

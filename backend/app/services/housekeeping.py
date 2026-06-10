from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.models.audit_job import AuditJob, AgentLog, AuditArtifact

logger = logging.getLogger("firecrow.services.housekeeping")

# Storage Policy Configuration
RETENTION_DAYS_BULKY = 7      # Days to keep detailed logs and raw artifacts
RETENTION_DAYS_JOB = 30       # Days to keep audit job records entirely
MAX_JOBS_PER_USER = 20        # Maximum number of audit jobs retained per user


def run_housekeeping(db: Session) -> dict[str, int]:
    """
    Performs smart database pruning to keep storage usage low while retaining key security findings:
    1. Prunes detailed logs (AgentLog) and raw artifacts (AuditArtifact) for completed/failed runs older than 7 days.
    2. Deletes entire audit jobs (AuditJob) older than 30 days.
    3. Retains only the 20 most recent audit jobs per user, deleting older jobs.
    
    Returns a dictionary summarizing the count of deleted/pruned rows.
    """
    now = datetime.now(timezone.utc)
    deleted_counts = {
        "pruned_logs": 0,
        "pruned_artifacts": 0,
        "deleted_jobs_expiry": 0,
        "deleted_jobs_overflow": 0,
    }

    try:
        # 1. Prune bulky logs and raw artifacts older than RETENTION_DAYS_BULKY
        bulky_cutoff = now - timedelta(days=RETENTION_DAYS_BULKY)
        
        # We query the jobs that are finalized (not queued/running) and older than the cutoff
        old_finished_jobs = db.query(AuditJob.id).filter(
            AuditJob.created_at < bulky_cutoff
        ).all()
        old_job_ids = [job_id for (job_id,) in old_finished_jobs]

        if old_job_ids:
            # Delete agent logs for these old jobs
            deleted_logs = db.query(AgentLog).filter(AgentLog.job_id.in_(old_job_ids)).delete(synchronize_session=False)
            deleted_counts["pruned_logs"] = deleted_logs

            # Delete bulky artifacts for these old jobs
            deleted_artifacts = db.query(AuditArtifact).filter(AuditArtifact.job_id.in_(old_job_ids)).delete(synchronize_session=False)
            deleted_counts["pruned_artifacts"] = deleted_artifacts

            if deleted_logs > 0 or deleted_artifacts > 0:
                logger.info("Pruned %d logs and %d artifacts from old finished jobs.", deleted_logs, deleted_artifacts)

        # 2. Delete entire jobs older than RETENTION_DAYS_JOB
        job_cutoff = now - timedelta(days=RETENTION_DAYS_JOB)
        expired_jobs = db.query(AuditJob).filter(AuditJob.created_at < job_cutoff).all()
        for job in expired_jobs:
            db.delete(job)
            deleted_counts["deleted_jobs_expiry"] += 1
        
        if deleted_counts["deleted_jobs_expiry"] > 0:
            logger.info("Deleted %d expired audit jobs (older than %d days).", deleted_counts["deleted_jobs_expiry"], RETENTION_DAYS_JOB)

        # 3. Limit total jobs per user to MAX_JOBS_PER_USER
        # Group jobs by user_id to count them
        users_with_jobs = db.query(AuditJob.user_id).group_by(AuditJob.user_id).all()
        for (user_id,) in users_with_jobs:
            # Get all jobs for this user, ordered by creation date descending
            user_jobs = db.query(AuditJob).filter(AuditJob.user_id == user_id).order_by(desc(AuditJob.created_at)).all()
            if len(user_jobs) > MAX_JOBS_PER_USER:
                overflow_jobs = user_jobs[MAX_JOBS_PER_USER:]
                for job in overflow_jobs:
                    db.delete(job)
                    deleted_counts["deleted_jobs_overflow"] += 1
                
                logger.info("Pruned %d overflow jobs for user %s to enforce limit of %d.", len(overflow_jobs), user_id, MAX_JOBS_PER_USER)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Error during database housekeeping execution: %s", str(e))

    return deleted_counts

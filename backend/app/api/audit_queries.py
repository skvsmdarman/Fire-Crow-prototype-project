from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models import AuditJob


def get_owned_job_or_404(db: Session, job_id: str, user_id: str) -> AuditJob:
    job = db.query(AuditJob).filter(AuditJob.id == job_id, AuditJob.user_id == user_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied",
        )
    return job

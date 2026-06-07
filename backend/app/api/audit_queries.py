from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models import AuditJob, User, Membership


def get_owned_job_or_404(db: Session, job_id: str, user_id: str) -> AuditJob:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.user_id == user_id:
        return job

    if job.tenant_id:
        if user.tenant_id == job.tenant_id:
            return job

        # Check memberships
        member = db.query(Membership).filter(
            Membership.user_id == user_id,
            Membership.organization_id == job.tenant_id
        ).first()
        if member:
            return job

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Job not found or access denied",
    )



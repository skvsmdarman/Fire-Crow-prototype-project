from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.graph.store import graph_store
from app.models import AuditJob, User, Membership


def get_owned_job_or_404(db: Session | None, job_id: str, user_id: str):
    if settings.DATABASE_BACKEND == "neo4j":
        job = graph_store.get_owned_job(user_id, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or access denied",
            )
        return job

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



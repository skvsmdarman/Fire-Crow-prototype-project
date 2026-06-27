"""GDPR compliance endpoints – user data export & right‑to‑be‑forgotten."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.limiter import limiter
from app.services.security_log import record_security_event

router = APIRouter(prefix="/user", tags=["User GDPR"])


@router.get("/export")
@limiter.limit("5/minute")
async def export_user_data(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Export all personal data for the authenticated user.

    Returns a JSON blob containing the user record (excluding ``password_hash``)
    and the activity log.  This satisfies the GDPR *right of access* (Art. 15).
    """
    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    # Build export payload – exclude secret / irrelevant fields
    export_data = {
        "id": user_obj.id,
        "username": user_obj.username,
        "email": user_obj.email,
        "created_at": user_obj.created_at.isoformat() if user_obj.created_at is not None else None,
        "activity_log": user_obj.activity_log,
        "privacy_policy_version": user_obj.privacy_policy_version,
        "privacy_policy_accepted_at": user_obj.privacy_policy_accepted_at.isoformat() if user_obj.privacy_policy_accepted_at is not None else None,
        "terms_version": user_obj.terms_version,
        "terms_accepted_at": user_obj.terms_accepted_at.isoformat() if user_obj.terms_accepted_at is not None else None,
    }

    record_security_event(
        db,
        action="user.export",
        request=request,
        user_id=user_id,
        details={"exported_fields": list(export_data.keys())},
    )
    return JSONResponse(content=export_data)


@router.delete("/delete")
@limiter.limit("2/minute")
async def delete_user(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Anonymize the current user's personal data (right‑to‑be‑forgotten).

    The user record is **soft‑deleted**: PII fields are cleared and the
    account is marked inactive.  The row is kept for referential integrity
    (audit jobs, reports, etc.) but contains no personally identifiable data.
    """
    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    # Anonymize PII – keep the row for foreign‑key integrity
    user_obj.username = f"deleted_{uuid.uuid4().hex[:8]}"
    user_obj.email = None
    user_obj.password_hash = None
    user_obj.activity_log = None
    if hasattr(user_obj, "is_active"):
        user_obj.is_active = False
    db.commit()

    record_security_event(
        db,
        action="user.delete",
        request=request,
        user_id=user_id,
        details={"anonymized": True},
    )
    return {"status": "deleted"}

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.pam import PrivilegedAccessRequest, PrivilegedAccessGrant, PrivilegedAccessAudit
from app.models.user import User
from app.services.security_log import record_security_event

logger = logging.getLogger("firecrow.services.pam")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def create_privilege_request(
    user_id: str,
    role_name: str,
    permission: str,
    reason: str,
    requested_duration_minutes: int,
    db: Session,
    ticket_ref: Optional[str] = None,
) -> PrivilegedAccessRequest:
    if requested_duration_minutes < 1:
        raise HTTPException(status_code=400, detail="Requested duration must be at least 1 minute.")
    if requested_duration_minutes > 480:
        raise HTTPException(status_code=400, detail="Requested duration cannot exceed 8 hours (480 minutes).")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    pending = db.query(PrivilegedAccessRequest).filter(
        PrivilegedAccessRequest.user_id == user_id,
        PrivilegedAccessRequest.status == "pending",
    ).count()
    if pending >= 3:
        raise HTTPException(
            status_code=429, detail="Too many pending privilege requests. Complete or cancel existing requests first."
        )

    request_obj = PrivilegedAccessRequest(
        user_id=user_id,
        role_name=role_name,
        permission=permission,
        reason=reason,
        ticket_ref=ticket_ref,
        requested_duration_minutes=requested_duration_minutes,
        status="pending",
    )
    db.add(request_obj)
    db.commit()
    db.refresh(request_obj)
    return request_obj


def approve_privilege_request(
    request_id: str,
    approver_id: str,
    db: Session,
    duration_minutes: Optional[int] = None,
) -> PrivilegedAccessGrant:
    req = db.query(PrivilegedAccessRequest).filter(PrivilegedAccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Privilege request not found.")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already {req.status}.")

    approver = db.query(User).filter(User.id == approver_id).first()
    if not approver or not approver.is_admin:
        raise HTTPException(status_code=403, detail="Only administrators can approve privilege requests.")

    duration = duration_minutes or req.requested_duration_minutes
    if duration < 1 or duration > 480:
        raise HTTPException(status_code=400, detail="Duration must be between 1 and 480 minutes.")

    now = _utc_now()
    expires_at = now + timedelta(minutes=duration)

    req.status = "approved"
    req.approved_by = approver_id
    req.approved_at = now
    req.expires_at = expires_at
    db.commit()

    grant = PrivilegedAccessGrant(
        request_id=req.id,
        user_id=req.user_id,
        role_name=req.role_name,
        permission=req.permission,
        granted_by=approver_id,
        expires_at=expires_at,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)

    _record_audit(db, grant_id=grant.id, user_id=req.user_id, action="privilege.granted",
                  details={"request_id": req.id, "role": req.role_name, "permission": req.permission,
                           "duration_minutes": duration, "granted_by": approver_id,
                           "expires_at": expires_at.isoformat()})
    return grant


def deny_privilege_request(
    request_id: str,
    approver_id: str,
    db: Session,
    reason: Optional[str] = None,
) -> PrivilegedAccessRequest:
    req = db.query(PrivilegedAccessRequest).filter(PrivilegedAccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Privilege request not found.")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already {req.status}.")

    req.status = "denied"
    req.approved_by = approver_id
    req.approved_at = _utc_now()
    req.denied_reason = reason
    req.completed_at = _utc_now()
    db.commit()
    db.refresh(req)
    return req


def cancel_privilege_request(request_id: str, user_id: str, db: Session) -> PrivilegedAccessRequest:
    req = db.query(PrivilegedAccessRequest).filter(PrivilegedAccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Privilege request not found.")
    if req.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only cancel your own requests.")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already {req.status}.")

    req.status = "cancelled"
    req.completed_at = _utc_now()
    db.commit()
    db.refresh(req)
    return req


def check_active_grant(user_id: str, permission: str, db: Session) -> bool:
    now = _utc_now()
    grant = db.query(PrivilegedAccessGrant).filter(
        PrivilegedAccessGrant.user_id == user_id,
        PrivilegedAccessGrant.permission == permission,
        PrivilegedAccessGrant.is_active == True,
        PrivilegedAccessGrant.expires_at > now,
    ).first()
    return grant is not None


def get_active_grants(user_id: str, db: Session) -> list[PrivilegedAccessGrant]:
    now = _utc_now()
    return db.query(PrivilegedAccessGrant).filter(
        PrivilegedAccessGrant.user_id == user_id,
        PrivilegedAccessGrant.is_active == True,
        PrivilegedAccessGrant.expires_at > now,
    ).all()


def revoke_grant(grant_id: str, revoked_by: str, db: Session) -> None:
    grant = db.query(PrivilegedAccessGrant).filter(PrivilegedAccessGrant.id == grant_id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found.")
    if not grant.is_active:
        raise HTTPException(status_code=409, detail="Grant is already revoked or expired.")

    grant.is_active = False
    grant.revoked_at = _utc_now()
    grant.revoked_by = revoked_by
    db.commit()

    _record_audit(db, grant_id=grant.id, user_id=grant.user_id, action="privilege.revoked",
                  details={"grant_id": grant.id, "role": grant.role_name, "revoked_by": revoked_by})


def expire_stale_grants(db: Session) -> int:
    now = _utc_now()
    expired = db.query(PrivilegedAccessGrant).filter(
        PrivilegedAccessGrant.is_active == True,
        PrivilegedAccessGrant.expires_at <= now,
    ).all()

    count = 0
    for grant in expired:
        grant.is_active = False
        _record_audit(db, grant_id=grant.id, user_id=grant.user_id, action="privilege.expired",
                      details={"role": grant.role_name, "expires_at": grant.expires_at.isoformat()})
        count += 1

    if count:
        db.commit()
    return count


def get_pending_requests(db: Session, user_id: Optional[str] = None) -> list[PrivilegedAccessRequest]:
    query = db.query(PrivilegedAccessRequest).filter(PrivilegedAccessRequest.status == "pending")
    if user_id:
        query = query.filter(PrivilegedAccessRequest.user_id == user_id)
    return query.order_by(PrivilegedAccessRequest.created_at.desc()).all()


def _record_audit(
    db: Session,
    grant_id: Optional[str],
    user_id: str,
    action: str,
    details: Optional[dict] = None,
) -> None:
    db.add(PrivilegedAccessAudit(
        grant_id=grant_id,
        user_id=user_id,
        action=action,
        details=json.dumps(details) if details else None,
    ))


def request_to_dict(req: PrivilegedAccessRequest) -> dict:
    return {
        "id": req.id,
        "user_id": req.user_id,
        "role_name": req.role_name,
        "permission": req.permission,
        "reason": req.reason,
        "ticket_ref": req.ticket_ref,
        "requested_duration_minutes": req.requested_duration_minutes,
        "status": req.status,
        "approved_by": req.approved_by,
        "approved_at": req.approved_at.isoformat() if req.approved_at else None,
        "denied_reason": req.denied_reason,
        "expires_at": req.expires_at.isoformat() if req.expires_at else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "completed_at": req.completed_at.isoformat() if req.completed_at else None,
    }


def grant_to_dict(grant: PrivilegedAccessGrant) -> dict:
    return {
        "id": grant.id,
        "request_id": grant.request_id,
        "user_id": grant.user_id,
        "role_name": grant.role_name,
        "permission": grant.permission,
        "granted_by": grant.granted_by,
        "granted_at": grant.granted_at.isoformat() if grant.granted_at else None,
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "is_active": grant.is_active,
        "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at else None,
        "revoked_by": grant.revoked_by,
    }

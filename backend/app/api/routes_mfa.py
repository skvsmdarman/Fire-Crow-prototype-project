from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.limiter import limiter
from app.services.mfa_service import (
    enroll_mfa, activate_mfa, verify_mfa, verify_recovery_code,
    disable_mfa, regenerate_recovery_codes, get_mfa_status,
    enforce_mfa_for_admin, get_users_without_mfa, record_mfa_event,
    get_totp_uri,
)
from app.services.security_log import record_security_event

router = APIRouter(prefix="/mfa", tags=["MFA"])


class MFARegisterResponse(BaseModel):
    secret: str
    uri: str
    recovery_codes: list[str]


class MFAActivateRequest(BaseModel):
    token: str


class MFAVerifyRequest(BaseModel):
    token: str


class MFAVerifyResponse(BaseModel):
    verified: bool


class MFADisableResponse(BaseModel):
    status: str


class RecoveryCodeRequest(BaseModel):
    code: str


class MFAComplianceResponse(BaseModel):
    requires_mfa: bool
    users_without_mfa: list[dict]


@router.post("/enroll")
@limiter.limit("5/minute")
async def enroll(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    config, recovery_codes = enroll_mfa(user_id, db)
    uri = get_totp_uri(config.secret, user.username)

    record_mfa_event(db, user_id, "mfa.enrolled", request)
    record_security_event(
        db, action="mfa.enrolled", request=request, user_id=user_id,
        details={"method": "totp"},
    )

    return MFARegisterResponse(
        secret=config.secret,
        uri=uri,
        recovery_codes=recovery_codes,
    )


@router.post("/activate")
@limiter.limit("10/minute")
async def activate(
    payload: MFAActivateRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = activate_mfa(user_id, payload.token, db)
    record_mfa_event(db, user_id, "mfa.activated", request)
    record_security_event(
        db, action="mfa.activated", request=request, user_id=user_id,
    )
    return {"status": "activated", "activated_at": result.activated_at.isoformat() if result.activated_at else None}


@router.post("/verify")
@limiter.limit("10/minute")
async def verify(
    payload: MFAVerifyRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verified = verify_mfa(user_id, payload.token, db)
    if verified:
        record_mfa_event(db, user_id, "mfa.verified", request)
        record_security_event(
            db, action="mfa.verified", request=request, user_id=user_id,
        )
    else:
        record_mfa_event(db, user_id, "mfa.verify_failed", request)

    return MFAVerifyResponse(verified=verified)


@router.post("/recovery")
@limiter.limit("3/minute")
async def use_recovery_code(
    payload: RecoveryCodeRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    valid = verify_recovery_code(user_id, payload.code, db)
    if valid:
        record_mfa_event(db, user_id, "mfa.recovery_used", request)
        record_security_event(
            db, action="mfa.recovery_used", request=request, user_id=user_id,
        )
    else:
        record_mfa_event(db, user_id, "mfa.recovery_failed", request)

    return {"verified": valid}


@router.post("/regenerate-codes")
@limiter.limit("2/minute")
async def regenerate_codes(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    codes = regenerate_recovery_codes(user_id, db)
    record_mfa_event(db, user_id, "mfa.recovery_codes_regenerated", request)
    return {"recovery_codes": codes}


@router.post("/disable")
@limiter.limit("3/minute")
async def disable(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    disable_mfa(user_id, db)
    record_mfa_event(db, user_id, "mfa.disabled", request)
    record_security_event(
        db, action="mfa.disabled", request=request, user_id=user_id,
    )
    return MFADisableResponse(status="mfa_disabled")


@router.get("/status")
async def status(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_mfa_status(user_id, db)


@router.get("/admin/compliance")
async def compliance_check(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")

    users_without = get_users_without_mfa(db, admin_only=True)
    return MFAComplianceResponse(
        requires_mfa=True,
        users_without_mfa=users_without,
    )


@router.post("/admin/enforce")
async def enforce(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")

    users_without = get_users_without_mfa(db, admin_only=True)
    for entry in users_without:
        target_user = db.query(User).filter(User.id == entry["user_id"]).first()
        if target_user:
            target_user.is_active = False
            record_security_event(
                db, action="mfa.enforce.deactivated", request=request, user_id=entry["user_id"],
                details={"reason": "MFA not enabled for admin account"},
            )

    db.commit()
    return {"status": "enforced", "deactivated_count": len(users_without)}

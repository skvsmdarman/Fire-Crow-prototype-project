from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import pyotp
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.mfa import MFAConfiguration, MFARecoveryCode, MFAAuditLog
from app.models.user import User
from app.services.crypto import crypto_manager

logger = logging.getLogger("firecrow.services.mfa")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str, issuer: str = "Fire Crow") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def verify_totp(secret: str, token: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)


def enroll_mfa(
    user_id: str,
    db: Session,
    method: str = "totp",
) -> tuple[MFAConfiguration, list[str]]:
    existing = db.query(MFAConfiguration).filter(MFAConfiguration.user_id == user_id).first()
    if existing and existing.is_active:
        raise HTTPException(status_code=409, detail="MFA is already enabled for this account.")

    secret = generate_totp_secret()
    if existing:
        existing.secret = secret
        existing.is_active = False
        existing.method = method
        existing.failed_attempts = 0
        mfa_config = existing
    else:
        mfa_config = MFAConfiguration(
            user_id=user_id,
            secret=secret,
            is_active=False,
            method=method,
        )
        db.add(mfa_config)

    recovery_codes = _generate_recovery_codes(user_id, db)
    db.commit()
    db.refresh(mfa_config)

    return mfa_config, recovery_codes


def _generate_recovery_codes(user_id: str, db: Session, count: int = 8) -> list[str]:
    db.query(MFARecoveryCode).filter(
        MFARecoveryCode.user_id == user_id,
        MFARecoveryCode.is_used == False,
    ).delete()

    codes: list[str] = []
    for _ in range(count):
        code = secrets.token_hex(8)
        code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        db.add(MFARecoveryCode(user_id=user_id, code_hash=code_hash))
        codes.append(code)
    return codes


def activate_mfa(user_id: str, token: str, db: Session) -> MFAConfiguration:
    mfa_config = db.query(MFAConfiguration).filter(MFAConfiguration.user_id == user_id).first()
    if not mfa_config:
        raise HTTPException(status_code=404, detail="MFA not enrolled. Enroll first.")

    if not verify_totp(mfa_config.secret, token):
        raise HTTPException(status_code=401, detail="Invalid TOTP token.")

    mfa_config.is_active = True
    mfa_config.activated_at = _utc_now()
    db.commit()
    db.refresh(mfa_config)
    return mfa_config


def verify_mfa(user_id: str, token: str, db: Session) -> bool:
    mfa_config = db.query(MFAConfiguration).filter(
        MFAConfiguration.user_id == user_id,
        MFAConfiguration.is_active == True,
    ).first()
    if not mfa_config:
        return False

    if mfa_config.failed_attempts >= 5:
        raise HTTPException(status_code=429, detail="MFA temporarily locked due to too many failed attempts.")

    if verify_totp(mfa_config.secret, token):
        mfa_config.failed_attempts = 0
        mfa_config.last_verified_at = _utc_now()
        db.commit()
        return True

    mfa_config.failed_attempts += 1
    db.commit()
    return False


def verify_recovery_code(user_id: str, code: str, db: Session) -> bool:
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    stored = db.query(MFARecoveryCode).filter(
        MFARecoveryCode.user_id == user_id,
        MFARecoveryCode.code_hash == code_hash,
        MFARecoveryCode.is_used == False,
    ).first()
    if not stored:
        return False

    stored.is_used = True
    stored.used_at = _utc_now()
    db.commit()

    mfa_config = db.query(MFAConfiguration).filter(MFAConfiguration.user_id == user_id).first()
    if mfa_config:
        mfa_config.failed_attempts = 0
        db.commit()
    return True


def disable_mfa(user_id: str, db: Session) -> None:
    mfa_config = db.query(MFAConfiguration).filter(MFAConfiguration.user_id == user_id).first()
    if mfa_config:
        mfa_config.is_active = False
        mfa_config.failed_attempts = 0

    db.query(MFARecoveryCode).filter(MFARecoveryCode.user_id == user_id).delete()
    db.commit()


def regenerate_recovery_codes(user_id: str, db: Session) -> list[str]:
    return _generate_recovery_codes(user_id, db)


def get_mfa_status(user_id: str, db: Session) -> dict:
    mfa_config = db.query(MFAConfiguration).filter(MFAConfiguration.user_id == user_id).first()
    if not mfa_config:
        return {"enrolled": False, "active": False, "method": None}

    recovery_codes_count = db.query(MFARecoveryCode).filter(
        MFARecoveryCode.user_id == user_id,
        MFARecoveryCode.is_used == False,
    ).count()

    return {
        "enrolled": True,
        "active": mfa_config.is_active,
        "method": mfa_config.method,
        "activated_at": mfa_config.activated_at.isoformat() if mfa_config.activated_at else None,
        "last_verified_at": mfa_config.last_verified_at.isoformat() if mfa_config.last_verified_at else None,
        "recovery_codes_remaining": recovery_codes_count,
    }


def mfa_required_for_admin(request: Request, user_id: str, db: Session) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return True

    if not user.is_admin:
        return False

    mfa_config = db.query(MFAConfiguration).filter(
        MFAConfiguration.user_id == user_id,
        MFAConfiguration.is_active == True,
    ).first()

    return not mfa_config


def enforce_mfa_for_admin(user_id: str, db: Session) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        return

    mfa_config = db.query(MFAConfiguration).filter(
        MFAConfiguration.user_id == user_id,
        MFAConfiguration.is_active == True,
    ).first()

    if not mfa_config:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA is required for administrative access. Please enroll in MFA first.",
        )


def get_users_without_mfa(db: Session, admin_only: bool = True) -> list[dict]:
    query = db.query(User, MFAConfiguration).outerjoin(
        MFAConfiguration, MFAConfiguration.user_id == User.id
    ).filter(
        User.is_active == True,
    )

    if admin_only:
        from app.models.role import Role
        query = query.join(Role, User.role_id == Role.id).filter(
            Role.name.in_(["admin", "owner", "security_admin", "platform_admin", "superadmin"])
        )

    results = []
    for user, mfa in query.all():
        results.append({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "mfa_enrolled": mfa is not None,
            "mfa_active": (mfa.is_active if mfa else False),
        })
    return results


def record_mfa_event(
    db: Session,
    user_id: str,
    action: str,
    request: Request,
    details: Optional[dict] = None,
) -> None:
    import json
    db.add(MFAAuditLog(
        user_id=user_id,
        action=action,
        ip_address=_client_ip(request),
        details=json.dumps(details) if details else None,
    ))
    db.commit()

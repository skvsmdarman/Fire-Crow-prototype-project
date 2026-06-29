import logging
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.models.user import User
from app.models.mfa import MFAConfiguration

logger = logging.getLogger("firecrow.middleware.mfa")


ADMIN_PATHS = {
    "/api/v1/iam",
    "/api/v1/sso/providers",
    "/api/v1/mfa/admin",
    "/api/v1/pam/requests/pending",
    "/api/v1/pam/requests/{id}/approve",
    "/api/v1/pam/requests/{id}/deny",
    "/api/v1/pam/grants/revoke",
    "/api/v1/pam/cleanup",
    "/api/v1/user/export",
    "/api/v1/user/delete",
}


class MFAEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            return await call_next(request)

        if not settings.MFA_ENFORCE_FOR_ADMINS:
            return await call_next(request)

        if not _is_admin_path(request.url.path):
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return await call_next(request)

        try:
            from app.models.database import SessionLocal
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_admin:
                    mfa = db.query(MFAConfiguration).filter(
                        MFAConfiguration.user_id == user_id,
                        MFAConfiguration.is_active == True,
                    ).first()
                    if not mfa:
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": "MFA is required for administrative actions. "
                                          "Please enroll and activate MFA before proceeding.",
                                "mfa_required": True,
                                "mfa_enroll_url": "/api/v1/mfa/enroll",
                            },
                        )
            finally:
                db.close()
        except Exception as e:
            logger.error("MFA enforcement check failed: %s", e)

        return await call_next(request)


def _is_admin_path(path: str) -> bool:
    for admin_path in ADMIN_PATHS:
        if path.startswith(admin_path.split("{")[0]) if "{" in admin_path else path.startswith(admin_path):
            return True
    return False

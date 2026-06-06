from datetime import datetime, timezone
from typing import Literal, Optional
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.services.auth import (
    create_access_token,
    create_oauth_state,
    get_current_user,
    get_optional_current_user,
    hash_password,
    verify_oauth_state,
    verify_password,
)
from backend.app.services.security_log import record_security_event
from backend.app.services.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

PRIVACY_POLICY_VERSION = "2026-06-06"
TERMS_VERSION = "2026-06-06"


class LoginRequest(BaseModel):
    username: str
    password: str
    privacy_policy_accepted: bool
    privacy_policy_version: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    privacy_policy_accepted: bool
    privacy_policy_version: str


class PolicyEventRequest(BaseModel):
    policy: Literal["terms", "privacy_policy"]
    event_type: Literal["link_click", "page_view"]
    policy_version: str
    source: Optional[str] = None
    href: Optional[str] = None
    page_path: Optional[str] = None
    referrer_path: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    user_id: str


def _normalize_username(username: str) -> str:
    return username.strip()


def _user_id_for(username: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "_" for char in username).strip("_")
    return f"usr_{safe or 'workspace'}"


def _validate_privacy_consent(accepted: bool, version: str) -> None:
    if not accepted:
        raise HTTPException(status_code=400, detail="Privacy Policy consent is required.")
    if version != PRIVACY_POLICY_VERSION:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported Privacy Policy version. Expected {PRIVACY_POLICY_VERSION}.",
        )


def _apply_privacy_consent(user: User, version: str) -> None:
    user.privacy_policy_version = version
    user.privacy_policy_accepted_at = datetime.now(timezone.utc)


def _current_policy_version(policy: Literal["terms", "privacy_policy"]) -> str:
    if policy == "terms":
        return TERMS_VERSION
    return PRIVACY_POLICY_VERSION


def _ensure_unique_username(db: Session, username: str) -> str:
    candidate = username
    suffix = 1
    while db.query(User).filter(User.username == candidate).first():
        candidate = f"{username}{suffix}"
        suffix += 1
    return candidate


def _oauth_redirect_url(request: Request, route_name: str) -> str:
    url = request.url_for(route_name)
    proto = request.headers.get("x-forwarded-proto")
    if proto:
        url = url.replace(scheme=proto)
    elif not settings.DEBUG or settings.FRONTEND_URL.startswith("https://"):
        url = url.replace(scheme="https")
    return str(url)


@router.get("/policy-context")
async def policy_context():
    return {
        "privacy_policy_version": PRIVACY_POLICY_VERSION,
        "terms_version": TERMS_VERSION,
        "providers": {
            "github": bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET),
            "google": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
            "password": True,
        },
    }


@router.post("/policy-events", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("60/minute")
async def create_policy_event(
    payload: PolicyEventRequest,
    request: Request,
    user_id: Optional[str] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    current_version = _current_policy_version(payload.policy)
    record_security_event(
        db,
        action=f"policy.{payload.policy}.{payload.event_type}",
        request=request,
        user_id=user_id,
        details={
            "policy": payload.policy,
            "policy_version": payload.policy_version,
            "current_policy_version": current_version,
            "policy_version_matches_current": payload.policy_version == current_version,
            "source": payload.source,
            "href": payload.href,
            "page_path": payload.page_path,
            "referrer_path": payload.referrer_path,
            "api_path": request.url.path,
        },
    )
    return {"status": "recorded"}


@router.post("/register", response_model=TokenResponse)
@limiter.limit("10/minute")
async def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    _validate_privacy_consent(payload.privacy_policy_accepted, payload.privacy_policy_version)

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username is already registered.")

    new_user = User(
        id=_user_id_for(username),
        username=username,
        password_hash=hash_password(payload.password),
        email=payload.email.strip() if payload.email else None,
    )
    _apply_privacy_consent(new_user, payload.privacy_policy_version)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(user_id=new_user.id, username=new_user.username)

    record_security_event(
        db,
        action="auth.register.success",
        request=request,
        user_id=new_user.id,
        details={"username": new_user.username},
    )
    record_security_event(
        db,
        action="policy.privacy_policy.accepted",
        request=request,
        user_id=new_user.id,
        details={
            "policy_version": payload.privacy_policy_version,
            "source": "register_form",
        },
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=new_user.username,
        user_id=new_user.id,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    if not username:
        raise HTTPException(status_code=400, detail="Workspace name is required.")
    if not payload.password:
        raise HTTPException(status_code=400, detail="Workspace password is required.")
    _validate_privacy_consent(payload.privacy_policy_accepted, payload.privacy_policy_version)

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        record_security_event(
            db,
            action="auth.login.failed",
            request=request,
            user_id=user.id if user else None,
            details={"username": username},
        )
        raise HTTPException(status_code=401, detail="Invalid workspace name or password.")

    _apply_privacy_consent(user, payload.privacy_policy_version)
    db.commit()

    token = create_access_token(user_id=user.id, username=user.username)

    record_security_event(
        db,
        action="auth.login.success",
        request=request,
        user_id=user.id,
        details={"username": user.username},
    )
    record_security_event(
        db,
        action="policy.privacy_policy.accepted",
        request=request,
        user_id=user.id,
        details={
            "policy_version": payload.privacy_policy_version,
            "source": "login_form",
        },
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        user_id=user.id,
    )


@router.post("/logout")
async def logout(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record_security_event(
        db,
        action="auth.logout",
        request=request,
        user_id=user_id,
        details={"source": "frontend"},
    )
    return {"status": "logged_out"}


@router.get("/me")
async def get_me(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User session could not be resolved.")

    return {
        "user_id": user_id,
        "username": user.username,
        "email": user.email,
        "role": "security_engineer",
        "privacy_policy_version": user.privacy_policy_version,
        "privacy_policy_accepted_at": user.privacy_policy_accepted_at.isoformat()
        if user.privacy_policy_accepted_at
        else None,
    }


@router.get("/github")
@limiter.limit("20/minute")
async def github_login(
    request: Request,
    privacy_policy_accepted: bool,
    privacy_policy_version: str,
    db: Session = Depends(get_db),
):
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured.")

    _validate_privacy_consent(privacy_policy_accepted, privacy_policy_version)
    oauth_state = create_oauth_state("github", privacy_policy_version)

    record_security_event(
        db,
        action="auth.oauth.github.initiated",
        request=request,
        details={"policy_version": privacy_policy_version},
    )

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": _oauth_redirect_url(request, "github_callback"),
        "scope": "user:email",
        "state": oauth_state,
    }
    url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured.")

    oauth_state = verify_oauth_state(state)
    if not oauth_state or oauth_state.get("provider") != "github":
        raise HTTPException(status_code=400, detail="Invalid or expired GitHub OAuth state.")

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": _oauth_redirect_url(request, "github_callback"),
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve access token from GitHub.")

        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail=f"GitHub OAuth error: {token_data.get('error_description', 'No access token')}",
            )

        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve user profile from GitHub.")

        profile = user_res.json()
        github_id = str(profile.get("id"))
        username = profile.get("login") or f"github_{github_id}"
        email = profile.get("email")

        if not email:
            emails_res = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"token {access_token}"},
            )
            if emails_res.status_code == 200:
                for email_obj in emails_res.json():
                    if email_obj.get("primary"):
                        email = email_obj.get("email")
                        break

    user = db.query(User).filter(User.github_id == github_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.github_id = github_id

    if not user:
        username = _ensure_unique_username(db, username)
        user = User(
            id=_user_id_for(username),
            username=username,
            email=email,
            github_id=github_id,
        )
        db.add(user)

    _apply_privacy_consent(user, oauth_state["privacy_policy_version"])
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, username=user.username)

    record_security_event(
        db,
        action="auth.oauth.github.success",
        request=request,
        user_id=user.id,
        details={"username": user.username},
    )
    record_security_event(
        db,
        action="policy.privacy_policy.accepted",
        request=request,
        user_id=user.id,
        details={
            "policy_version": oauth_state["privacy_policy_version"],
            "source": "github_oauth",
        },
    )

    redirect_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/signin"
        f"?token={token}&username={urllib.parse.quote(user.username)}&user_id={urllib.parse.quote(user.id)}"
    )
    return RedirectResponse(redirect_url)


@router.get("/google")
@limiter.limit("20/minute")
async def google_login(
    request: Request,
    privacy_policy_accepted: bool,
    privacy_policy_version: str,
    db: Session = Depends(get_db),
):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")

    _validate_privacy_consent(privacy_policy_accepted, privacy_policy_version)
    oauth_state = create_oauth_state("google", privacy_policy_version)

    record_security_event(
        db,
        action="auth.oauth.google.initiated",
        request=request,
        details={"policy_version": privacy_policy_version},
    )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _oauth_redirect_url(request, "google_callback"),
        "response_type": "code",
        "scope": "openid email profile",
        "state": oauth_state,
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")

    oauth_state = verify_oauth_state(state)
    if not oauth_state or oauth_state.get("provider") != "google":
        raise HTTPException(status_code=400, detail="Invalid or expired Google OAuth state.")

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _oauth_redirect_url(request, "google_callback"),
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve access token from Google.")

        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token returned by Google.")

        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve user profile from Google.")

        profile = user_res.json()
        google_id = str(profile.get("id"))
        email = profile.get("email")
        username = email.split("@")[0] if email else f"google_{google_id}"

    user = db.query(User).filter(User.google_id == google_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_id = google_id

    if not user:
        username = _ensure_unique_username(db, username)
        user = User(
            id=_user_id_for(username),
            username=username,
            email=email,
            google_id=google_id,
        )
        db.add(user)

    _apply_privacy_consent(user, oauth_state["privacy_policy_version"])
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, username=user.username)

    record_security_event(
        db,
        action="auth.oauth.google.success",
        request=request,
        user_id=user.id,
        details={"username": user.username},
    )
    record_security_event(
        db,
        action="policy.privacy_policy.accepted",
        request=request,
        user_id=user.id,
        details={
            "policy_version": oauth_state["privacy_policy_version"],
            "source": "google_oauth",
        },
    )

    redirect_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/signin"
        f"?token={token}&username={urllib.parse.quote(user.username)}&user_id={urllib.parse.quote(user.id)}"
    )
    return RedirectResponse(redirect_url)

from __future__ import annotations

import importlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.models.sso import SSOProvider, SSOSession
from app.models.user import User
from app.services.crypto import crypto_manager
from app.services.auth import create_access_token

logger = logging.getLogger("firecrow.services.sso")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def create_sso_provider(
    db: Session,
    name: str,
    provider_type: str,
    issuer_url: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    authorization_url: Optional[str] = None,
    token_url: Optional[str] = None,
    userinfo_url: Optional[str] = None,
    jwks_url: Optional[str] = None,
    certificate: Optional[str] = None,
    attribute_mapping: Optional[dict] = None,
    domains: Optional[list[str]] = None,
    enforce_mfa: bool = False,
    auto_provision: bool = False,
    default_role_id: Optional[str] = None,
) -> SSOProvider:
    existing = db.query(SSOProvider).filter(SSOProvider.name == name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"SSO provider '{name}' already exists.")

    provider = SSOProvider(
        name=name,
        provider_type=provider_type,
        issuer_url=issuer_url,
        client_id=client_id,
        client_secret_encrypted=crypto_manager.encrypt_secret(client_secret) if client_secret else None,
        authorization_url=authorization_url,
        token_url=token_url,
        userinfo_url=userinfo_url,
        jwks_url=jwks_url,
        certificate=certificate,
        attribute_mapping=json.dumps(attribute_mapping) if attribute_mapping else None,
        domains=",".join(domains) if domains else None,
        enforce_mfa=enforce_mfa,
        auto_provision=auto_provision,
        default_role_id=default_role_id,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def update_sso_provider(
    provider_id: str,
    db: Session,
    **kwargs,
) -> SSOProvider:
    provider = db.query(SSOProvider).filter(SSOProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found.")

    for key, value in kwargs.items():
        if key == "client_secret" and value:
            setattr(provider, "client_secret_encrypted", crypto_manager.encrypt_secret(value))
        elif key == "attribute_mapping" and value:
            setattr(provider, "attribute_mapping", json.dumps(value))
        elif key == "domains" and value:
            setattr(provider, "domains", ",".join(value))
        elif value is not None and hasattr(provider, key):
            setattr(provider, key, value)

    provider.updated_at = _utc_now()
    db.commit()
    db.refresh(provider)
    return provider


def delete_sso_provider(provider_id: str, db: Session) -> None:
    provider = db.query(SSOProvider).filter(SSOProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found.")
    db.delete(provider)
    db.commit()


def get_sso_provider(provider_id: str, db: Session) -> SSOProvider:
    provider = db.query(SSOProvider).filter(SSOProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found.")
    return provider


def list_sso_providers(db: Session, active_only: bool = True) -> list[SSOProvider]:
    query = db.query(SSOProvider)
    if active_only:
        query = query.filter(SSOProvider.is_active == True)
    return query.all()


def get_oidc_authorization_url(provider: SSOProvider, redirect_uri: str, state: str) -> str:
    if not provider.authorization_url:
        raise HTTPException(status_code=400, detail="OIDC provider missing authorization URL.")

    params = {
        "client_id": provider.client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    import urllib.parse
    return f"{provider.authorization_url}?{urllib.parse.urlencode(params)}"


async def exchange_oidc_code(
    provider: SSOProvider,
    code: str,
    redirect_uri: str,
) -> dict:
    if not provider.client_secret_encrypted:
        raise HTTPException(status_code=400, detail="OIDC provider missing client secret.")
    if not provider.token_url:
        raise HTTPException(status_code=400, detail="OIDC provider missing token URL.")

    client_secret = crypto_manager.decrypt_secret(provider.client_secret_encrypted)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            provider.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.client_id,
                "client_secret": client_secret,
            },
            headers={"Accept": "application/json"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange OIDC authorization code.")

        token_data = resp.json()
        if "id_token" not in token_data:
            raise HTTPException(status_code=400, detail="No id_token returned by OIDC provider.")

        userinfo = await _get_oidc_userinfo(provider, token_data.get("access_token"))
        return {
            "external_id": userinfo.get("sub"),
            "email": userinfo.get("email"),
            "username": userinfo.get("preferred_username") or userinfo.get("email", "").split("@")[0],
            "id_token": token_data.get("id_token"),
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
        }


async def _get_oidc_userinfo(provider: SSOProvider, access_token: Optional[str]) -> dict:
    if not access_token or not provider.userinfo_url:
        return {}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            provider.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch OIDC userinfo.")
        return resp.json()


async def authenticate_saml_assertion(
    provider: SSOProvider,
    saml_response: str,
) -> dict:
    try:
        saml_response_module = importlib.import_module("onelogin.saml2.response")
        saml_settings_module = importlib.import_module("onelogin.saml2.settings")
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="SAML support requires 'python3-saml' package. Install with: pip install python3-saml",
        )

    settings_dict = _build_saml_settings(provider)
    saml_settings = saml_settings_module.OneLogin_Saml2_Settings(settings_dict)
    response = saml_response_module.OneLogin_Saml2_Response(saml_settings, saml_response)

    if not response.is_valid():
        raise HTTPException(status_code=401, detail="Invalid SAML assertion.")

    attributes = response.get_attributes()
    name_id = response.get_nameid()

    mapped_attributes = {}
    if provider.attribute_mapping:
        mapping = json.loads(provider.attribute_mapping)
        for saml_attr, target_key in mapping.items():
            if saml_attr in attributes:
                mapped_attributes[target_key] = attributes[saml_attr][0] if attributes[saml_attr] else None

    return {
        "external_id": name_id,
        "email": mapped_attributes.get("email") or attributes.get("email", [None])[0],
        "username": mapped_attributes.get("username") or name_id,
        "attributes": mapped_attributes,
    }


def _build_saml_settings(provider: SSOProvider) -> dict:
    return {
        "sp": {
            "entityId": f"{settings.FRONTEND_URL}/saml/metadata",
            "assertionConsumerService": {
                "url": f"{settings.FRONTEND_URL}/auth/saml/callback",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
        },
        "idp": {
            "entityId": provider.issuer_url or "",
            "singleSignOnService": {
                "url": provider.authorization_url or "",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": provider.certificate or "",
        },
    }


def find_or_create_sso_user(
    db: Session,
    provider: SSOProvider,
    external_id: str,
    email: Optional[str],
    username: str,
    request: Request,
) -> User:
    session = db.query(SSOSession).filter(
        SSOSession.provider_id == provider.id,
        SSOSession.external_id == external_id,
        SSOSession.is_revoked == False,
    ).first()

    user = None
    if session:
        user = db.query(User).filter(User.id == session.user_id).first()

    if not user and email:
        from sqlalchemy import func
        user = db.query(User).filter(func.lower(User.email) == email.lower()).first()

    if not user and provider.auto_provision:
        from app.services.auth import hash_password
        from app.models.user import User as UserModel
        new_id = str(uuid.uuid4())
        safe_username = _ensure_unique_username(db, username)
        user = UserModel(
            id=new_id,
            username=safe_username,
            email=email,
            role_id=provider.default_role_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user:
        raise HTTPException(
            status_code=403,
            detail="No matching account found. Contact your administrator to provision access.",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account has been deactivated.")

    return user


def _ensure_unique_username(db: Session, username: str) -> str:
    from app.models.user import User
    candidate = username
    suffix = 1
    while db.query(User).filter(User.username == candidate).first():
        candidate = f"{username}{suffix}"
        suffix += 1
    return candidate


def create_sso_session(
    db: Session,
    provider: SSOProvider,
    user: User,
    external_id: str,
    id_token: Optional[str] = None,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    expires_in: Optional[int] = None,
) -> SSOSession:
    expires_at = None
    if expires_in:
        expires_at = _utc_now() + timedelta(seconds=expires_in)

    sso_session = SSOSession(
        provider_id=provider.id,
        user_id=user.id,
        external_id=external_id,
        id_token=id_token,
        access_token_encrypted=crypto_manager.encrypt_secret(access_token) if access_token else None,
        refresh_token_encrypted=crypto_manager.encrypt_secret(refresh_token) if refresh_token else None,
        expires_at=expires_at,
    )
    db.add(sso_session)
    db.commit()
    db.refresh(sso_session)
    return sso_session


def revoke_sso_session(session_id: str, db: Session) -> None:
    session = db.query(SSOSession).filter(SSOSession.id == session_id).first()
    if session:
        session.is_revoked = True
        db.commit()


def revoke_all_user_sso_sessions(user_id: str, db: Session) -> None:
    db.query(SSOSession).filter(
        SSOSession.user_id == user_id,
        SSOSession.is_revoked == False,
    ).update({"is_revoked": True})
    db.commit()


def provider_to_dict(provider: SSOProvider) -> dict:
    return {
        "id": provider.id,
        "name": provider.name,
        "provider_type": provider.provider_type,
        "issuer_url": provider.issuer_url,
        "client_id": provider.client_id,
        "authorization_url": provider.authorization_url,
        "token_url": provider.token_url,
        "userinfo_url": provider.userinfo_url,
        "jwks_url": provider.jwks_url,
        "has_certificate": bool(provider.certificate),
        "has_client_secret": bool(provider.client_secret_encrypted),
        "attribute_mapping": json.loads(provider.attribute_mapping) if provider.attribute_mapping else None,
        "domains": provider.domains.split(",") if provider.domains else [],
        "is_active": provider.is_active,
        "enforce_mfa": provider.enforce_mfa,
        "auto_provision": provider.auto_provision,
        "default_role_id": provider.default_role_id,
        "created_at": provider.created_at.isoformat() if provider.created_at else None,
        "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
    }

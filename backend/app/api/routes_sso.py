from datetime import datetime, timezone
import importlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db
from app.models.user import User
from app.services.auth import (
    create_access_token, create_refresh_token, create_oauth_state,
    verify_oauth_state, get_current_user, create_exchange_code,
)
from app.services.limiter import limiter
from app.services.security_log import record_security_event
from app.services.sso_service import (  # type: ignore
    create_sso_provider, update_sso_provider, delete_sso_provider,
    get_sso_provider, list_sso_providers, provider_to_dict,
    get_oidc_authorization_url, exchange_oidc_code,
    authenticate_saml_assertion, find_or_create_sso_user,
    create_sso_session, revoke_sso_session,
)
from app.services.mfa_service import enforce_mfa_for_admin

router = APIRouter(prefix="/sso", tags=["SSO"])


class SSOProviderCreate(BaseModel):
    name: str
    provider_type: str
    issuer_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    jwks_url: Optional[str] = None
    certificate: Optional[str] = None
    attribute_mapping: Optional[dict] = None
    domains: Optional[list[str]] = None
    enforce_mfa: bool = False
    auto_provision: bool = False
    default_role_id: Optional[str] = None


class SSOProviderUpdate(BaseModel):
    name: Optional[str] = None
    issuer_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    jwks_url: Optional[str] = None
    certificate: Optional[str] = None
    attribute_mapping: Optional[dict] = None
    domains: Optional[list[str]] = None
    enforce_mfa: Optional[bool] = None
    auto_provision: Optional[bool] = None
    default_role_id: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/providers")
@limiter.limit("20/minute")
async def list_providers(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    providers = list_sso_providers(db, active_only=False)
    return {"providers": [provider_to_dict(p) for p in providers]}


@router.post("/providers")
@limiter.limit("10/minute")
async def create_provider(
    payload: SSOProviderCreate,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    enforce_mfa_for_admin(user_id, db)

    provider = create_sso_provider(
        db, name=payload.name, provider_type=payload.provider_type,
        issuer_url=payload.issuer_url, client_id=payload.client_id,
        client_secret=payload.client_secret,
        authorization_url=payload.authorization_url, token_url=payload.token_url,
        userinfo_url=payload.userinfo_url, jwks_url=payload.jwks_url,
        certificate=payload.certificate, attribute_mapping=payload.attribute_mapping,
        domains=payload.domains, enforce_mfa=payload.enforce_mfa,
        auto_provision=payload.auto_provision, default_role_id=payload.default_role_id,
    )
    record_security_event(
        db, action="sso.provider.created", request=request, user_id=user_id,
        details={"provider_name": payload.name, "provider_type": payload.provider_type},
    )
    return provider_to_dict(provider)


@router.get("/providers/{provider_id}")
@limiter.limit("20/minute")
async def get_provider(
    provider_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    provider = get_sso_provider(provider_id, db)
    return provider_to_dict(provider)


@router.put("/providers/{provider_id}")
@limiter.limit("10/minute")
async def update_provider(
    provider_id: str,
    payload: SSOProviderUpdate,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    enforce_mfa_for_admin(user_id, db)

    provider = update_sso_provider(provider_id, db, **payload.model_dump(exclude_none=True))
    record_security_event(
        db, action="sso.provider.updated", request=request, user_id=user_id,
        details={"provider_id": provider_id},
    )
    return provider_to_dict(provider)


@router.delete("/providers/{provider_id}")
@limiter.limit("10/minute")
async def delete_provider(
    provider_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    enforce_mfa_for_admin(user_id, db)

    provider = get_sso_provider(provider_id, db)
    record_security_event(
        db, action="sso.provider.deleted", request=request, user_id=user_id,
        details={"provider_name": provider.name},
    )
    delete_sso_provider(provider_id, db)
    return {"status": "deleted"}


@router.get("/oidc/{provider_id}/login")
@limiter.limit("10/minute")
async def oidc_login(
    provider_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    provider = get_sso_provider(provider_id, db)
    if not provider.is_active:
        raise HTTPException(status_code=403, detail="SSO provider is inactive.")

    oauth_state = create_oauth_state(f"sso_{provider_id}", settings.PRIVACY_POLICY_VERSION)
    redirect_uri = str(request.url_for("oidc_callback")).replace(request.url.scheme, "https") if not settings.DEBUG else request.url_for("oidc_callback")
    auth_url = get_oidc_authorization_url(provider, str(redirect_uri), oauth_state)

    record_security_event(
        db, action="sso.oidc.login_initiated", request=request,
        details={"provider_name": provider.name, "provider_id": provider_id},
    )
    return RedirectResponse(auth_url)


@router.get("/oidc/callback")
@limiter.limit("20/minute")
async def oidc_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    oauth_state = verify_oauth_state(state)
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    provider_id = oauth_state.get("provider", "").removeprefix("sso_")
    provider = get_sso_provider(provider_id, db)
    if not provider.is_active:
        raise HTTPException(status_code=403, detail="SSO provider is inactive.")

    redirect_uri = str(request.url_for("oidc_callback")).replace(request.url.scheme, "https") if not settings.DEBUG else request.url_for("oidc_callback")
    identity = await exchange_oidc_code(provider, code, str(redirect_uri))

    user = find_or_create_sso_user(db, provider, identity["external_id"],
                                    identity.get("email"), identity.get("username", ""), request)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    if provider.enforce_mfa:
        enforce_mfa_for_admin(user.id, db)

    sso_session = create_sso_session(db, provider, user, identity["external_id"],
                                      id_token=identity.get("id_token"),
                                      access_token=identity.get("access_token"),
                                      refresh_token=identity.get("refresh_token"))

    token = create_access_token(user_id=user.id, username=user.username, db=db)
    refresh_token = create_refresh_token(user_id=user.id, username=user.username, db=db)
    code = create_exchange_code(user_id=user.id, username=user.username, token=token, db=db)

    from app.api.routes_auth import _frontend_signin_url
    response = RedirectResponse(f"{_frontend_signin_url(request)}?code={code}")

    record_security_event(
        db, action="sso.oidc.login_success", request=request, user_id=user.id,
        details={"provider_name": provider.name, "sso_session_id": sso_session.id},
    )
    return response


@router.post("/saml/{provider_id}/login")
@limiter.limit("10/minute")
async def saml_login(
    provider_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    provider = get_sso_provider(provider_id, db)
    if not provider.is_active:
        raise HTTPException(status_code=403, detail="SSO provider is inactive.")

    try:
        saml_authn_request = importlib.import_module("onelogin.saml2.authn_request")
        saml_settings = importlib.import_module("onelogin.saml2.settings")
    except ImportError:
        raise HTTPException(status_code=501, detail="SAML support requires 'python3-saml' package.")

    req = saml_authn_request.OneLogin_Saml2_Authn_Request(
        saml_settings.OneLogin_Saml2_Settings(_build_saml_settings(provider))
    )
    redirect_url = req.get_redirect_url()

    record_security_event(
        db, action="sso.saml.login_initiated", request=request,
        details={"provider_name": provider.name},
    )
    return RedirectResponse(redirect_url)


def _build_saml_settings(provider):
    return {
        "sp": {
            "entityId": f"{settings.FRONTEND_URL}/saml/metadata",
            "assertionConsumerService": {
                "url": f"{settings.FRONTEND_URL.rstrip('/')}/auth/saml/callback",
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


@router.post("/saml/{provider_id}/callback")
@limiter.limit("20/minute")
async def saml_callback(
    provider_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    provider = get_sso_provider(provider_id, db)
    if not provider.is_active:
        raise HTTPException(status_code=403, detail="SSO provider is inactive.")

    form = await request.form()
    saml_response = form.get("SAMLResponse")
    if not saml_response or not isinstance(saml_response, str):
        raise HTTPException(status_code=400, detail="Missing SAMLResponse.")

    identity = await authenticate_saml_assertion(provider, saml_response)
    user = find_or_create_sso_user(db, provider, identity["external_id"],
                                    identity.get("email"), identity.get("username", ""), request)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    if provider.enforce_mfa:
        enforce_mfa_for_admin(user.id, db)

    sso_session = create_sso_session(db, provider, user, identity["external_id"])
    token = create_access_token(user_id=user.id, username=user.username, db=db)
    refresh_token = create_refresh_token(user_id=user.id, username=user.username, db=db)
    code = create_exchange_code(user_id=user.id, username=user.username, token=token, db=db)

    from app.api.routes_auth import _frontend_signin_url
    response = RedirectResponse(f"{_frontend_signin_url(request)}?code={code}")

    record_security_event(
        db, action="sso.saml.login_success", request=request, user_id=user.id,
        details={"provider_name": provider.name, "sso_session_id": sso_session.id},
    )
    return response

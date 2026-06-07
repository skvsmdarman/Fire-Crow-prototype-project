from __future__ import annotations

import hashlib
import hmac
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import settings
from backend.app.services.crypto import crypto_manager

logger = logging.getLogger("firecrow.services.auth")

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
JWT_ISSUER = "firecrow-api"
JWT_AUDIENCE = "firecrow-web"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
ACCESS_TOKEN_EXPIRE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60
OAUTH_STATE_EXPIRE_MINUTES = 15
AUTH_COOKIE_NAME = "fc_access_token"

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

_revoked_jtis: dict[str, datetime] = {}
_redis_client = None
_redis_checked = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> int:
    return int(value.timestamp())


def _get_redis_client():
    global _redis_checked, _redis_client
    if _redis_checked:
        return _redis_client

    _redis_checked = True
    if not settings.REDIS_URL:
        return None

    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.25, socket_timeout=0.25)
        client.ping()
        _redis_client = client
    except Exception:
        if settings.DEBUG:
            logger.info("Redis token denylist unavailable in DEBUG mode; using in-memory fallback.")
        else:
            logger.error("Redis token denylist unavailable in production; token validation will fail closed.")
        _redis_client = None

    return _redis_client


def _denylist_key(jti: str) -> str:
    return f"firecrow:revoked_jti:{jti}"


def _cleanup_memory_denylist() -> None:
    now = _utc_now()
    expired = [jti for jti, expires_at in _revoked_jtis.items() if expires_at <= now]
    for jti in expired:
        _revoked_jtis.pop(jti, None)


def _claims(expires_delta: timedelta) -> tuple[datetime, datetime, datetime, str]:
    now = _utc_now()
    not_before = now - timedelta(seconds=5)
    expire = now + expires_delta
    return now, not_before, expire, str(uuid.uuid4())


def create_access_token(user_id: str, username: Optional[str] = None) -> str:
    now, not_before, expire, jti = _claims(timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": user_id,
        "username": username,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": _timestamp(now),
        "nbf": _timestamp(not_before),
        "exp": _timestamp(expire),
        "jti": jti,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_oauth_state(
    provider: str,
    privacy_policy_version: str,
    timezone_name: Optional[str] = None,
    region: Optional[str] = None,
) -> str:
    now, not_before, expire, jti = _claims(timedelta(minutes=OAUTH_STATE_EXPIRE_MINUTES))
    to_encode = {
        "type": "oauth_state",
        "provider": provider,
        "privacy_policy_version": privacy_policy_version,
        "timezone": timezone_name,
        "region": region,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": _timestamp(now),
        "nbf": _timestamp(not_before),
        "exp": _timestamp(expire),
        "jti": jti,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def is_token_revoked(payload: dict) -> bool:
    jti = payload.get("jti")
    if not jti:
        return True

    client = _get_redis_client()
    if client is not None:
        try:
            return bool(client.exists(_denylist_key(str(jti))))
        except Exception:
            if not settings.DEBUG:
                logger.error("Redis denylist lookup failed; rejecting token jti=%s.", jti)
                return True
            logger.info("Redis denylist lookup failed in DEBUG mode; using in-memory fallback.")

    if not settings.DEBUG and settings.REDIS_URL:
        return True

    _cleanup_memory_denylist()
    return str(jti) in _revoked_jtis


def revoke_access_token(payload: dict) -> bool:
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return False

    try:
        expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except (TypeError, ValueError):
        return False

    ttl = max(int((expires_at - _utc_now()).total_seconds()), 1)
    client = _get_redis_client()
    if client is not None:
        try:
            client.setex(_denylist_key(str(jti)), ttl, "1")
            return True
        except Exception:
            logger.error("Failed to write token jti=%s to Redis denylist.", jti)
            if not settings.DEBUG and settings.REDIS_URL:
                return False

    if not settings.DEBUG and settings.REDIS_URL:
        return False

    _revoked_jtis[str(jti)] = expires_at
    _cleanup_memory_denylist()
    return True


def verify_access_token(token: str, *, check_revocation: bool = True) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            leeway=5,
        )
    except jwt.PyJWTError:
        return None

    if check_revocation and is_token_revoked(payload):
        return None
    return payload


def verify_oauth_state(token: str) -> Optional[dict]:
    payload = verify_access_token(token, check_revocation=False)
    if not payload or payload.get("type") != "oauth_state":
        return None
    return payload


def _extract_bearer_or_cookie_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        return credentials.credentials
    return request.cookies.get(AUTH_COOKIE_NAME)


def get_current_token_payload(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    token = _extract_bearer_or_cookie_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(payload: dict = Depends(get_current_token_payload)) -> str:
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return str(user_id)


def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    token = _extract_bearer_or_cookie_token(request, credentials)
    if not token:
        return None
    payload = verify_access_token(token)
    if not payload:
        return None
    subject = payload.get("sub")
    return str(subject) if subject else None


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def _is_legacy_pbkdf2_hash(hashed_password: str) -> bool:
    parts = hashed_password.split(":")
    if len(parts) != 2:
        return False
    salt_hex, hash_hex = parts
    try:
        bytes.fromhex(salt_hex)
        bytes.fromhex(hash_hex)
    except ValueError:
        return False
    return bool(salt_hex and hash_hex)


def _verify_legacy_password(password: str, hashed_password: str) -> bool:
    try:
        salt_hex, hash_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(pw_hash, expected_hash)
    except Exception:
        return False


def verify_password(password: str, hashed_password: str) -> bool:
    if _is_legacy_pbkdf2_hash(hashed_password):
        return _verify_legacy_password(password, hashed_password)

    try:
        return _password_hasher.verify(hashed_password, password)
    except (InvalidHashError, VerifyMismatchError, VerificationError):
        return False


def password_needs_rehash(hashed_password: str) -> bool:
    if _is_legacy_pbkdf2_hash(hashed_password):
        return True
    try:
        return _password_hasher.check_needs_rehash(hashed_password)
    except (InvalidHashError, VerificationError):
        return True


def legacy_hash_password_for_tests(password: str) -> str:
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{pw_hash.hex()}"


def encrypt_provider_token(token: str) -> str:
    return crypto_manager.encrypt_secret(token)


def decrypt_provider_token(token: str | None) -> str:
    if not token:
        return ""
    decrypted = crypto_manager.decrypt_secret(token)
    return "" if decrypted == "ERROR_DECRYPTING" else decrypted


_exchange_codes: dict[str, dict] = {}


def create_exchange_code(user_id: str, username: str, token: str) -> str:
    import secrets
    import json
    code = secrets.token_urlsafe(32)
    data = {
        "user_id": user_id,
        "username": username,
        "access_token": token,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    client = _get_redis_client()
    if client is not None:
        try:
            client.setex(f"firecrow:exchange_code:{code}", 60, json.dumps(data))
            return code
        except Exception:
            logger.error("Failed to store exchange code in Redis")
    
    _exchange_codes[code] = {
        **data,
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=60)
    }
    return code


def verify_and_consume_exchange_code(code: str) -> Optional[dict]:
    import json
    client = _get_redis_client()
    if client is not None:
        try:
            val = client.get(f"firecrow:exchange_code:{code}")
            if val:
                client.delete(f"firecrow:exchange_code:{code}")
                return json.loads(val)
        except Exception:
            logger.error("Failed to retrieve exchange code from Redis")
            
    now = datetime.now(timezone.utc)
    expired = [c for c, d in _exchange_codes.items() if d.get("expires_at", now) <= now]
    for c in expired:
        _exchange_codes.pop(c, None)
        
    data = _exchange_codes.pop(code, None)
    if data and data.get("expires_at", now) > now:
        return {
            "user_id": data["user_id"],
            "username": data["username"],
            "access_token": data["access_token"]
        }
    return None

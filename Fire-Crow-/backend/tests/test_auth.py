import json
import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.api.routes_auth import PRIVACY_POLICY_VERSION
from app.main import app
from app.models import AuthExchangeCode, SecurityLog, SessionLocal, User, UserActivityEvent
from app.services.auth import (
    AUTH_COOKIE_NAME,
    create_access_token,
    create_exchange_code,
    legacy_hash_password_for_tests,
    verify_access_token,
)
from app.config import settings

client = TestClient(app)


def _register_payload(username: str, password: str = "supersecretpassword") -> dict:
    return {
        "username": username,
        "password": password,
        "privacy_policy_accepted": True,
        "privacy_policy_version": PRIVACY_POLICY_VERSION,
    }


def test_jwt_generation_and_verification():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id=user_id, username="tester")

    assert token is not None
    assert isinstance(token, str)

    payload = verify_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["username"] == "tester"
    assert payload["iss"] == "firecrow-api"
    assert payload["aud"] == "firecrow-web"
    assert payload["jti"]


def test_auth_me_unauthorized():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_auth_me_authorized():
    reg_response = client.post("/api/v1/auth/register", json=_register_payload("supertester"))
    assert reg_response.status_code == 200
    token = reg_response.json()["access_token"]
    user_id = reg_response.json()["user_id"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    uuid.UUID(user_id)
    assert response.json()["role"] == "security_engineer"
    assert response.json()["privacy_policy_version"] == PRIVACY_POLICY_VERSION


def test_auth_session_accepts_cookie():
    reg_response = client.post("/api/v1/auth/register", json=_register_payload("cookietester"))
    token = reg_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/session",
        cookies={AUTH_COOKIE_NAME: token},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "cookietester"
    assert response.json()["providers"]["github"]["connected"] is False


def test_logout_revokes_token():
    reg_response = client.post("/api/v1/auth/register", json=_register_payload("revoketester"))
    token = reg_response.json()["access_token"]

    logout_response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_response.status_code == 200

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_logout_revokes_token_with_redis_configured(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.revoked: dict[str, tuple[int, str]] = {}

        def exists(self, key: str) -> int:
            return int(key in self.revoked)

        def setex(self, key: str, ttl: int, value: str) -> None:
            self.revoked[key] = (ttl, value)

    fake_redis = FakeRedis()
    monkeypatch.setattr("app.services.auth._get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://cache.firecrow.test:6379/0")

    reg_response = client.post("/api/v1/auth/register", json=_register_payload("redisrevoker"))
    assert reg_response.status_code == 200
    token = reg_response.json()["access_token"]

    logout_response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_response.status_code == 200
    assert fake_redis.revoked

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_legacy_pbkdf2_hash_rehashes_on_login():
    db = SessionLocal()
    try:
        user = User(
            id=str(uuid.uuid4()),
            username="legacyuser",
            password_hash=legacy_hash_password_for_tests("supersecretpassword"),
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/login",
        json={
            **_register_payload("legacyuser"),
            "password": "supersecretpassword",
        },
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "legacyuser").first()
        assert user is not None
        assert user.password_hash is not None
        assert user.password_hash.startswith("$argon2id$")
    finally:
        db.close()


def test_registration_and_login_flow():
    original_frontend_url = settings.FRONTEND_URL
    original_debug = settings.DEBUG
    settings.FRONTEND_URL = "https://app.firecrow.test"
    settings.DEBUG = False

    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            **_register_payload("newuser"),
            "email": "newuser@example.com",
        },
    )
    try:
        assert reg_response.status_code == 200
        assert reg_response.json()["username"] == "newuser"
        reg_cookie = reg_response.headers["set-cookie"]
        assert f"{AUTH_COOKIE_NAME}=" in reg_cookie
        assert "HttpOnly" in reg_cookie
        assert "Secure" in reg_cookie
        assert "SameSite=strict" in reg_cookie

        login_ok = client.post(
            "/api/v1/auth/login",
            json={
                **_register_payload("newuser"),
                "password": "supersecretpassword",
            },
        )
        assert login_ok.status_code == 200
        assert login_ok.json()["access_token"] is not None
        login_cookie = login_ok.headers["set-cookie"]
        assert f"{AUTH_COOKIE_NAME}=" in login_cookie
        assert "HttpOnly" in login_cookie
        assert "Secure" in login_cookie
        assert "SameSite=strict" in login_cookie

        login_fail = client.post(
            "/api/v1/auth/login",
            json={
                **_register_payload("newuser"),
                "password": "wrongpassword",
            },
        )
        assert login_fail.status_code == 401
        assert "Invalid" in login_fail.json()["detail"]
    finally:
        settings.FRONTEND_URL = original_frontend_url
        settings.DEBUG = original_debug


def test_login_requires_privacy_consent():
    client.post("/api/v1/auth/register", json=_register_payload("policyuser"))

    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "policyuser",
            "password": "supersecretpassword",
            "privacy_policy_accepted": False,
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
    )

    assert response.status_code == 400
    assert "Privacy Policy consent" in response.json()["detail"]


def test_policy_context_hides_unconfigured_oauth_providers(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "")

    response = client.get("/api/v1/auth/policy-context")

    assert response.status_code == 200
    providers = response.json()["providers"]
    assert providers["github"] is False
    assert providers["google"] is False
    assert providers["password"] is True


def test_policy_context_sets_local_csrf_cookie_without_secure_flag_in_debug(monkeypatch):
    monkeypatch.setattr(settings, "CSRF_ENABLED", True)
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", True)
    with TestClient(app) as local_client:
        response = local_client.get("/api/v1/auth/policy-context")

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "fc_csrf_token=" in set_cookie
    assert "Secure" not in set_cookie


def test_oauth_redirects_fail_when_provider_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "")
    github_response = client.get(
        "/api/v1/auth/github",
        params={
            "privacy_policy_accepted": "true",
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
    )
    assert github_response.status_code == 503
    assert "not configured" in github_response.json()["detail"]

    google_response = client.get(
        "/api/v1/auth/google",
        params={
            "privacy_policy_accepted": "true",
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
    )
    assert google_response.status_code == 503
    assert "not configured" in google_response.json()["detail"]


def test_github_oauth_requests_private_repo_pr_scopes(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "github-client")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", "github-secret")

    response = client.get(
        "/api/v1/auth/github",
        params={
            "privacy_policy_accepted": "true",
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
        follow_redirects=False,
    )

    assert response.status_code in {302, 307}
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["scope"] == ["repo,workflow,read:org,user:email"]


def test_github_oauth_callback_sets_cookie_without_token_url(monkeypatch):
    class FakeResponse:
        def __init__(self, payload: Any, status_code: int = 200, headers: dict[str, str] | None = None):
            self._payload = payload
            self.status_code = status_code
            self.headers = headers or {}

        def json(self):
            return self._payload

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse({"access_token": "github-oauth-token", "scope": "repo,workflow,read:org,user:email"})

        async def get(self, url, *args, **kwargs):
            if url.endswith("/user"):
                return FakeResponse(
                    {"id": 123, "login": "octo", "email": "Octo@Example.com"},
                    headers={"X-OAuth-Scopes": "repo,workflow,read:org,user:email"},
                )
            return FakeResponse([])

    monkeypatch.setattr("app.api.routes_auth.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "github-client")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", "github-secret")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.firecrow.test")
    monkeypatch.setattr(settings, "DEBUG", False)

    state = client.get(
        "/api/v1/auth/github",
        params={
            "privacy_policy_accepted": "true",
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
        follow_redirects=False,
    ).headers["location"].split("state=", 1)[1].split("&", 1)[0]

    response = client.get(
        "/api/v1/auth/github/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )

    assert response.headers["location"].startswith("https://app.firecrow.test/signin?code=")
    assert "token=" not in response.headers["location"]
    set_cookie = response.headers["set-cookie"]
    assert f"{AUTH_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=strict" in set_cookie

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "octo").first()
        assert user is not None
        assert user.github_access_token is not None
        assert user.github_access_token.startswith("ENC[")
        assert user.github_token_scopes == "read:org,repo,user:email,workflow"
    finally:
        db.close()


def test_github_oauth_callback_uses_request_origin_when_frontend_url_missing(monkeypatch):
    class FakeResponse:
        def __init__(self, payload: Any, status_code: int = 200, headers: dict[str, str] | None = None):
            self._payload = payload
            self.status_code = status_code
            self.headers = headers or {}

        def json(self):
            return self._payload

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse({"access_token": "github-oauth-token", "scope": "repo,workflow,read:org,user:email"})

        async def get(self, url, *args, **kwargs):
            if url.endswith("/user"):
                return FakeResponse(
                    {"id": 456, "login": "originfallback", "email": "originfallback@example.com"},
                    headers={"X-OAuth-Scopes": "repo,workflow,read:org,user:email"},
                )
            return FakeResponse([])

    monkeypatch.setattr("app.api.routes_auth.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "github-client")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", "github-secret")
    monkeypatch.setattr(settings, "FRONTEND_URL", "")
    monkeypatch.setattr(settings, "DEBUG", True)

    state = client.get(
        "/api/v1/auth/github",
        params={
            "privacy_policy_accepted": "true",
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
        follow_redirects=False,
    ).headers["location"].split("state=", 1)[1].split("&", 1)[0]

    response = client.get(
        "/api/v1/auth/github/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )

    assert response.headers["location"].startswith("http://testserver/signin?code=")
    assert "localhost" not in response.headers["location"]


def test_google_oauth_callback_sets_cookie_without_token_url(monkeypatch):
    class FakeResponse:
        def __init__(self, payload: dict, status_code: int = 200):
            self._payload = payload
            self.status_code = status_code

        def json(self):
            return self._payload

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse({"access_token": "google-oauth-token"})

        async def get(self, *args, **kwargs):
            return FakeResponse({"id": "google-123", "email": "GoogleUser@Example.com"})

    monkeypatch.setattr("app.api.routes_auth.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "google-client")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.firecrow.test")
    monkeypatch.setattr(settings, "DEBUG", False)

    state = client.get(
        "/api/v1/auth/google",
        params={
            "privacy_policy_accepted": "true",
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
        follow_redirects=False,
    ).headers["location"].split("state=", 1)[1].split("&", 1)[0]

    response = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )

    assert response.headers["location"].startswith("https://app.firecrow.test/signin?code=")
    assert "token=" not in response.headers["location"]
    set_cookie = response.headers["set-cookie"]
    assert f"{AUTH_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=strict" in set_cookie


def test_policy_event_logging_records_security_log():
    response = client.post(
        "/api/v1/auth/policy-events",
        json={
            "policy": "privacy_policy",
            "event_type": "page_view",
            "policy_version": PRIVACY_POLICY_VERSION,
            "source": "pytest",
            "href": "/privacy-policy",
            "page_path": "/privacy-policy",
            "referrer_path": "/signin",
        },
    )
    assert response.status_code == 202

    db = SessionLocal()
    try:
      log = db.query(SecurityLog).filter(SecurityLog.action == "policy.privacy_policy.page_view").first()
      assert log is not None
      assert log.details is not None
      assert '"page_path":"/privacy-policy"' in log.details
      assert '"policy_version_matches_current":true' in log.details
      assert '"source":"pytest"' in log.details
    finally:
      db.close()


def test_policy_event_logging_redacts_sensitive_details():
    response = client.post(
        "/api/v1/auth/policy-events",
        json={
            "policy": "privacy_policy",
            "event_type": "link_click",
            "policy_version": PRIVACY_POLICY_VERSION,
            "source": "pytest",
            "href": "https://app.example/path?token=secret-token-value",
            "page_path": "/signin",
            "referrer_path": "https://app.example/start?access_token=secret",
        },
    )
    assert response.status_code == 202

    db = SessionLocal()
    try:
        log = db.query(SecurityLog).filter(SecurityLog.action == "policy.privacy_policy.link_click").first()
        assert log is not None
        serialized_details = str(log.details or "{}")
        details = json.loads(serialized_details)
        assert details["href"] == "https://app.example/path"
        assert details["referrer_path"] == "https://app.example/start"
        assert "secret-token-value" not in serialized_details
    finally:
        db.close()


def test_oauth_code_exchange():
    original_frontend_url = settings.FRONTEND_URL
    original_debug = settings.DEBUG
    settings.FRONTEND_URL = "https://app.firecrow.test"
    settings.DEBUG = False

    db = SessionLocal()
    try:
        token = create_access_token(user_id="usr_test_oauth", username="oauth_tester", db=db)
        code = create_exchange_code(user_id="usr_test_oauth", username="oauth_tester", token=token, db=db)

        stored_code = db.query(AuthExchangeCode).filter(AuthExchangeCode.code == code).first()
        assert stored_code is not None

        response = client.post("/api/v1/auth/exchange", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == token
        assert data["username"] == "oauth_tester"
        assert data["user_id"] == "usr_test_oauth"
        set_cookie = response.headers["set-cookie"]
        assert f"{AUTH_COOKIE_NAME}=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "SameSite=strict" in set_cookie

        db.expire_all()
        consumed_code = db.query(AuthExchangeCode).filter(AuthExchangeCode.code == code).first()
        assert consumed_code is None

        response_retry = client.post("/api/v1/auth/exchange", json={"code": code})
        assert response_retry.status_code == 400
    finally:
        db.close()
        settings.FRONTEND_URL = original_frontend_url
        settings.DEBUG = original_debug


def test_policy_context_reports_password_auth_available():
    response = client.get("/api/v1/auth/policy-context")
    assert response.status_code == 200
    assert response.json()["providers"]["password"] is True


def test_user_activity_logging():
    username = f"logtester_{uuid.uuid4().hex[:6]}"

    def fetch_activity_rows(db_session, target_user_id: str) -> list[UserActivityEvent]:
        return (
            db_session.query(UserActivityEvent)
            .filter(UserActivityEvent.user_id == target_user_id)
            .order_by(UserActivityEvent.created_at.desc())
            .all()
        )

    # 1. Register a new user
    reg_payload = _register_payload(username)
    reg_payload["email"] = f"{username}@example.com"
    reg_response = client.post(
        "/api/v1/auth/register",
        json=reg_payload,
    )
    assert reg_response.status_code == 200
    user_id = reg_response.json()["user_id"]
    token = reg_response.json()["access_token"]

    from app.api.routes_auth import TERMS_VERSION
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.terms_version == TERMS_VERSION
        assert user.terms_accepted_at is not None
        assert user.first_login_at is not None
        assert user.last_login_at is not None
        activity_history = fetch_activity_rows(db, user_id)
        activity_actions = [entry.action for entry in activity_history]
        assert "login" in activity_actions
        assert "register" in activity_actions
    finally:
        db.close()

    # 2. Login again
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            **_register_payload(username),
            "password": "supersecretpassword",
        },
    )
    assert login_response.status_code == 200

    db = SessionLocal()
    try:
        activity_history = fetch_activity_rows(db, user_id)
        assert len(activity_history) >= 3
        assert activity_history[0].action == "login"
        assert activity_history[0].details_json is not None
        assert json.loads(activity_history[0].details_json)["provider"] == "password"
    finally:
        db.close()

    # 3. Post a policy event
    policy_response = client.post(
        "/api/v1/auth/policy-events",
        json={
            "policy": "privacy_policy",
            "policy_version": PRIVACY_POLICY_VERSION,
            "event_type": "link_click",
            "source": "footer",
            "href": "https://app.example/path",
            "page_path": "/dashboard",
            "referrer_path": "/home"
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert policy_response.status_code == 202

    db = SessionLocal()
    try:
        activity_history = fetch_activity_rows(db, user_id)
        assert len(activity_history) >= 4
        assert activity_history[0].action == "policy_privacy_policy_link_click"
    finally:
        db.close()

    # 4. Logout
    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.last_logout_at is not None
        activity_history = fetch_activity_rows(db, user_id)
        assert len(activity_history) >= 5
        assert activity_history[0].action == "logout"
    finally:
        db.close()

def test_redis_miss_falls_back_to_db(monkeypatch):
    class FakeRedis:
        def exists(self, key: str) -> int:
            return 0  # Cache miss

        def setex(self, key: str, ttl: int, value: str) -> None:
            pass

    fake_redis = FakeRedis()
    monkeypatch.setattr("app.services.auth._get_redis_client", lambda: fake_redis)

    reg_response = client.post("/api/v1/auth/register", json=_register_payload("redis_miss"))
    token = reg_response.json()["access_token"]

    # Log out (this should write to DB)
    logout_response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_response.status_code == 200

    # Test that /me rejects it despite Redis missing the key, because it falls back to DB
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

def test_redis_outage_falls_back_to_db(monkeypatch):
    class CrashingRedis:
        def exists(self, key: str) -> int:
            raise Exception("Connection timeout")

        def setex(self, key: str, ttl: int, value: str) -> None:
            raise Exception("Connection timeout")

    crashing_redis = CrashingRedis()
    monkeypatch.setattr("app.services.auth._get_redis_client", lambda: crashing_redis)

    reg_response = client.post("/api/v1/auth/register", json=_register_payload("redis_outage"))
    token = reg_response.json()["access_token"]

    # Log out
    client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})

    # Token should still be revoked
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_auth_me_bearer_no_cookies():
    # Register user with standard client (sets cookies on standard client)
    reg_response = client.post("/api/v1/auth/register", json=_register_payload("cleanclient"))
    assert reg_response.status_code == 200
    token = reg_response.json()["access_token"]
    user_id = reg_response.json()["user_id"]

    # Use a brand new client with no cookies
    clean_client = TestClient(app)
    response = clean_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    assert response.json()["username"] == "cleanclient"


def test_github_mock_oauth_flow(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "mock_github_client_id")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", "mock_github_client_secret")

    # Step 1: Login redirect
    login_response = client.get(
        "/api/v1/auth/github",
        params={
            "privacy_policy_accepted": "true",
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
        follow_redirects=False,
    )
    assert login_response.status_code in {302, 307}
    location = login_response.headers["location"]
    
    # Parse the redirect URL
    parsed = urlparse(location)
    query_params = parse_qs(parsed.query)
    assert "code" in query_params
    assert "state" in query_params
    
    code = query_params["code"][0]
    state = query_params["state"][0]
    assert code == "mock_github_code"
    
    # Step 2: Callback
    callback_response = client.get(
        "/api/v1/auth/github/callback",
        params={
            "code": code,
            "state": state,
        },
        follow_redirects=False,
    )
    assert callback_response.status_code in {302, 307}
    callback_location = callback_response.headers["location"]
    assert "code=" in callback_location


def test_google_mock_oauth_flow(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "mock_google_client_id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "mock_google_client_secret")

    # Step 1: Login redirect
    login_response = client.get(
        "/api/v1/auth/google",
        params={
            "privacy_policy_accepted": "true",
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
        follow_redirects=False,
    )
    assert login_response.status_code in {302, 307}
    location = login_response.headers["location"]
    
    # Parse the redirect URL
    parsed = urlparse(location)
    query_params = parse_qs(parsed.query)
    assert "code" in query_params
    assert "state" in query_params
    
    code = query_params["code"][0]
    state = query_params["state"][0]
    assert code == "mock_google_code"
    
    # Step 2: Callback
    callback_response = client.get(
        "/api/v1/auth/google/callback",
        params={
            "code": code,
            "state": state,
        },
        follow_redirects=False,
    )
    assert callback_response.status_code in {302, 307}
    callback_location = callback_response.headers["location"]
    assert "code=" in callback_location


def test_csrf_bypass_for_bearer_tokens():
    original_csrf_enabled = settings.CSRF_ENABLED
    settings.CSRF_ENABLED = True
    try:
        response_no_auth = client.post("/api/v1/auth/logout")
        assert response_no_auth.status_code == 403
        assert "CSRF token missing or invalid" in response_no_auth.json()["detail"]

        response_bearer = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid_or_expired_token"}
        )
        assert response_bearer.status_code == 401
        assert "Could not validate credentials" in response_bearer.json()["detail"]
    finally:
        settings.CSRF_ENABLED = original_csrf_enabled




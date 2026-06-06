from fastapi.testclient import TestClient

from backend.app.api.routes_auth import PRIVACY_POLICY_VERSION
from backend.app.main import app
from backend.app.models import SecurityLog, SessionLocal
from backend.app.services.auth import create_access_token, verify_access_token

client = TestClient(app)


def _register_payload(username: str, password: str = "supersecretpassword") -> dict:
    return {
        "username": username,
        "password": password,
        "privacy_policy_accepted": True,
        "privacy_policy_version": PRIVACY_POLICY_VERSION,
    }


def test_jwt_generation_and_verification():
    user_id = "usr_tester"
    token = create_access_token(user_id=user_id, username="tester")

    assert token is not None
    assert isinstance(token, str)

    payload = verify_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["username"] == "tester"


def test_auth_me_unauthorized():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_auth_me_authorized():
    reg_response = client.post("/api/v1/auth/register", json=_register_payload("supertester"))
    assert reg_response.status_code == 200
    token = reg_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == "usr_supertester"
    assert response.json()["role"] == "security_engineer"
    assert response.json()["privacy_policy_version"] == PRIVACY_POLICY_VERSION


def test_registration_and_login_flow():
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            **_register_payload("newuser"),
            "email": "newuser@example.com",
        },
    )
    assert reg_response.status_code == 200
    assert reg_response.json()["username"] == "newuser"

    login_ok = client.post(
        "/api/v1/auth/login",
        json={
            **_register_payload("newuser"),
            "password": "supersecretpassword",
        },
    )
    assert login_ok.status_code == 200
    assert login_ok.json()["access_token"] is not None

    login_fail = client.post(
        "/api/v1/auth/login",
        json={
            **_register_payload("newuser"),
            "password": "wrongpassword",
        },
    )
    assert login_fail.status_code == 401
    assert "Invalid" in login_fail.json()["detail"]


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


def test_oauth_redirects_fail_when_provider_not_configured():
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

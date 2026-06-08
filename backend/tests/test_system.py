from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app.api.routes_auth import PRIVACY_POLICY_VERSION
from backend.app.models import SessionLocal, User, get_db

client = TestClient(app)


def _register_user(username: str, role: str) -> tuple[dict[str, str], str]:
    # Register the user
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "supersecretpassword",
            "privacy_policy_accepted": True,
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
    )
    user_id = register_response.json()["user_id"]
    
    # Update the user's role in the DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.role_id = role
            db.commit()
    finally:
        db.close()
        
    # Login to get the access token
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "supersecretpassword",
            "privacy_policy_accepted": True,
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


def test_system_status_endpoint():
    headers, _ = _register_user("test_sys_status", "security_engineer")
    response = client.get("/api/v1/system/status", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["api"] == "online"
    # Integrations should not be in the response for non-admins
    assert "integrations" not in payload


def test_system_status_admin_endpoint():
    headers, _ = _register_user("test_sys_status_admin", "admin")
    response = client.get("/api/v1/system/status", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["api"] == "online"
    # Integrations should be in the response for admins
    assert "integrations" in payload


def test_database_stats_admin_required():
    # Test non-admin access (Forbidden)
    normal_headers, _ = _register_user("normal_user_stats", "security_engineer")
    response = client.get("/api/v1/system/database/stats", headers=normal_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Administrative privileges required to access database management."

    # Test admin access (Success)
    admin_headers, _ = _register_user("admin_user_stats", "admin")
    response = client.get("/api/v1/system/database/stats", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert "dialect" in payload
    assert "row_counts" in payload
    assert "pending_migrations" in payload
    assert "users" in payload["row_counts"]


def test_database_housekeeping_admin_required():
    # Test non-admin access (Forbidden)
    normal_headers, _ = _register_user("normal_user_hk", "security_engineer")
    response = client.post("/api/v1/system/database/housekeeping", headers=normal_headers)
    assert response.status_code == 403

    # Test admin access (Success)
    admin_headers, _ = _register_user("admin_user_hk", "admin")
    response = client.post("/api/v1/system/database/housekeeping", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "counts" in payload
    assert "pruned_logs" in payload["counts"]

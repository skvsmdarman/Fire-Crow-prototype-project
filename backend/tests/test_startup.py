import pytest
from app.main import app
from app.models.database import SessionLocal
from app.models.user import User
from fastapi.testclient import TestClient

def test_startup_does_not_delete_smoke_user():
    # Arrange: ensure smoke user exists in database
    db = SessionLocal()
    try:
        # Check if smoke user exists, if not create one
        smoke = db.query(User).filter(User.username == "smoke").first()
        if not smoke:
            smoke = User(
                id="usr_smoke",
                username="smoke",
                password_hash="somehash",
                email="smoke@example.com"
            )
            db.add(smoke)
            db.commit()
    finally:
        db.close()

    # Act: run the application startup using test client context manager
    with TestClient(app) as client:
        # This triggers the lifespan events (startup & shutdown)
        pass

    # Assert: verify that the smoke user was NOT deleted during startup
    db = SessionLocal()
    try:
        smoke = db.query(User).filter(User.username == "smoke").first()
        assert smoke is not None, "Smoke user should not be deleted on startup"
        assert smoke.username == "smoke"
    finally:
        db.close()


def test_global_exception_handler_returns_generic_error():
    from app.models.database import get_db
    
    def mock_get_db():
        raise ValueError("This is a sensitive database connection error")
        
    app.dependency_overrides[get_db] = mock_get_db
    
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/auth/policy-events",
                json={
                    "policy": "privacy_policy",
                    "event_type": "link_click",
                    "policy_version": "2026-06-06",
                    "source": "pytest",
                    "href": "https://app.example/path",
                    "page_path": "/signin",
                    "referrer_path": "https://app.example/start",
                }
            )
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Internal Server Error"
            assert "request_id" in data
            assert "ValueError" not in str(data)
            assert "sensitive" not in str(data)
    finally:
        app.dependency_overrides.clear()

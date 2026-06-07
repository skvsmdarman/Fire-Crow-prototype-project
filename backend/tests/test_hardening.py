import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings

def test_health_live_endpoint():
    with TestClient(app) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "live"}

def test_health_ready_endpoint():
    with TestClient(app) as client:
        response = client.get("/health/ready")
        # May be 200 or 503 depending on redis availability in test environment
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data

def test_health_deep_endpoint():
    with TestClient(app) as client:
        response = client.get("/health/deep")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "local_storage" in data
        assert "object_storage" in data

def test_oversized_payload_rejection():
    # Store old threshold
    old_threshold = settings.MAX_REQUEST_BODY_BYTES
    try:
        # Set a very low body size limit
        settings.MAX_REQUEST_BODY_BYTES = 10
        with TestClient(app) as client:
            # Send a request with a large body
            large_body = "a" * 100
            response = client.post(
                "/api/v1/auth/login",
                content=large_body,
                headers={"Content-Type": "application/json"}
            )
            # Should be rejected with 413 Payload Too Large
            assert response.status_code == 413
            assert response.json()["detail"] == "Payload Too Large"
    finally:
        settings.MAX_REQUEST_BODY_BYTES = old_threshold

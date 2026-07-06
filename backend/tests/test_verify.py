import json
import uuid
import pytest
import re
from typing import Any
from fastapi.testclient import TestClient
from app.main import app
from app.models import SessionLocal, User, DomainVerification
from app.services.auth import create_access_token
from app.config import settings

client = TestClient(app)

def _get_auth_header(username: str = "verify_tester") -> dict:
    user_id = f"usr_{username}"
    # Ensure user exists in database
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(
                id=user_id,
                username=username,
                email=f"{username}@example.com",
                is_active=True,
            )
            db.add(user)
            db.commit()
    finally:
        db.close()
    
    token = create_access_token(user_id=user_id, username=username)
    return {"Authorization": f"Bearer {token}"}


def test_verify_unauthorized():
    response = client.get("/api/v1/verify/domains")
    assert response.status_code == 401

    response = client.post("/api/v1/verify/domain", json={"domain": "example.com"})
    assert response.status_code == 401


def test_verify_initiate_invalid_domain():
    headers = _get_auth_header("invalid_tester")
    response = client.post(
        "/api/v1/verify/domain",
        json={"domain": "not-a-valid-domain!"},
        headers=headers,
    )
    assert response.status_code == 422


def test_verify_flow_dns_success(monkeypatch):
    headers = _get_auth_header("dns_tester")
    
    # 1. Initiate domain verification
    init_resp = client.post(
        "/api/v1/verify/domain",
        json={"domain": "dns-ok.com"},
        headers=headers,
    )
    assert init_resp.status_code == 200
    data = init_resp.json()
    assert data["domain"] == "dns-ok.com"
    token = data["verification_token"]
    assert token.startswith("firecrow-challenge-")
    assert data["verified"] is False

    # 2. List domains
    list_resp = client.get("/api/v1/verify/domains", headers=headers)
    assert list_resp.status_code == 200
    records = list_resp.json()
    assert len(records) == 1
    assert records[0]["domain"] == "dns-ok.com"
    assert records[0]["verified"] is False

    # 3. Mock DNS lookup success
    class MockTXTRecord:
        def __init__(self, token_val):
            self.strings = [token_val.encode("utf-8")]

    class MockResolver:
        def __init__(self):
            self.timeout = 5.0
            self.lifetime = 5.0
        def resolve(self, name, rdtype):
            assert name == "_firecrow-challenge.dns-ok.com"
            assert rdtype == "TXT"
            return [MockTXTRecord(token)]

    monkeypatch.setattr("dns.resolver.Resolver", MockResolver)

    # 4. Trigger check via DNS
    check_resp = client.post(
        "/api/v1/verify/domain/check",
        json={"domain": "dns-ok.com", "method": "dns"},
        headers=headers,
    )
    assert check_resp.status_code == 200
    check_data = check_resp.json()
    assert check_data["verified"] is True
    assert "verified successfully" in check_data["message"]

    # 5. List domains again to check status is now True
    list_resp2 = client.get("/api/v1/verify/domains", headers=headers)
    assert list_resp2.status_code == 200
    records2 = list_resp2.json()
    assert records2[0]["verified"] is True


def test_verify_flow_dns_failure(monkeypatch):
    headers = _get_auth_header("dns_fail_tester")
    
    init_resp = client.post(
        "/api/v1/verify/domain",
        json={"domain": "dns-fail.com"},
        headers=headers,
    )
    assert init_resp.status_code == 200

    # Mock DNS lookup returning incorrect token
    class MockTXTRecord:
        def __init__(self):
            self.strings = [b"wrong-token"]

    class MockResolver:
        def __init__(self):
            self.timeout = 5.0
            self.lifetime = 5.0
        def resolve(self, name, rdtype):
            return [MockTXTRecord()]

    monkeypatch.setattr("dns.resolver.Resolver", MockResolver)

    check_resp = client.post(
        "/api/v1/verify/domain/check",
        json={"domain": "dns-fail.com", "method": "dns"},
        headers=headers,
    )
    assert check_resp.status_code == 200
    assert check_resp.json()["verified"] is False


def test_verify_flow_html_success(monkeypatch):
    headers = _get_auth_header("html_tester")
    
    init_resp = client.post(
        "/api/v1/verify/domain",
        json={"domain": "html-ok.com"},
        headers=headers,
    )
    assert init_resp.status_code == 200
    token = init_resp.json()["verification_token"]

    # Mock httpx response containing the meta tag
    class FakeResponse:
        def __init__(self, text_val, status_code=200):
            self.text = text_val
            self.status_code = status_code

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return None
        async def get(self, url, *args, **kwargs):
            html_content = f'<html><head><meta name="firecrow-verification" content="{token}"></head></html>'
            return FakeResponse(html_content)

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    # Check verification
    check_resp = client.post(
        "/api/v1/verify/domain/check",
        json={"domain": "html-ok.com", "method": "html"},
        headers=headers,
    )
    assert check_resp.status_code == 200
    assert check_resp.json()["verified"] is True


def test_verify_flow_file_success(monkeypatch):
    headers = _get_auth_header("file_tester")
    
    init_resp = client.post(
        "/api/v1/verify/domain",
        json={"domain": "file-ok.com"},
        headers=headers,
    )
    assert init_resp.status_code == 200
    token = init_resp.json()["verification_token"]

    # Mock httpx response containing the exact file content
    class FakeResponse:
        def __init__(self, text_val, status_code=200):
            self.text = text_val
            self.status_code = status_code

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return None
        async def get(self, url, *args, **kwargs):
            assert "/.well-known/firecrow.txt" in url
            return FakeResponse(token)

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    # Check verification
    check_resp = client.post(
        "/api/v1/verify/domain/check",
        json={"domain": "file-ok.com", "method": "file"},
        headers=headers,
    )
    assert check_resp.status_code == 200
    assert check_resp.json()["verified"] is True


def test_delete_domain():
    headers = _get_auth_header("delete_tester")
    
    init_resp = client.post(
        "/api/v1/verify/domain",
        json={"domain": "delete-me.com"},
        headers=headers,
    )
    record_id = init_resp.json()["id"]

    # Delete the domain record
    del_resp = client.delete(
        f"/api/v1/verify/domain/{record_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # Listing should now be empty
    list_resp = client.get("/api/v1/verify/domains", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0

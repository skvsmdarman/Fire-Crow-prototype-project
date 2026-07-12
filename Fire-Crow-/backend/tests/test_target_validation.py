import pytest
from unittest.mock import MagicMock, patch
from app.agents.network import is_allowed_sandbox_target, is_external_target, run_network_scan
from app.models import SessionLocal, DomainVerification
from datetime import datetime, timezone

def test_is_allowed_sandbox_target_private_ips_and_sandbox_hosts():
    assert is_allowed_sandbox_target("fc-target-job123") is True
    assert is_allowed_sandbox_target("fc-kali-scanner") is True
    assert is_allowed_sandbox_target("172.20.0.3") is True
    assert is_allowed_sandbox_target("192.168.1.100") is True
    assert is_allowed_sandbox_target("10.0.0.1") is True
    assert is_allowed_sandbox_target("127.0.0.1") is False  # Loopback is not allowed
    assert is_allowed_sandbox_target("google.com") is False  # Unverified domain is not allowed


def test_is_allowed_sandbox_target_verified_domains():
    db = SessionLocal()
    try:
        # Create a mock verified domain
        verification = DomainVerification(
            id="test-verify-id",
            user_id="test-user",
            domain="verified-target-site.com",
            verification_token="firecrow-challenge-xyz",
            verified=True,
            verified_at=datetime.now(timezone.utc)
        )
        db.add(verification)
        db.commit()

        # Check if the sandbox target check returns True
        assert is_allowed_sandbox_target("verified-target-site.com") is True

        # Clean up
        db.delete(verification)
        db.commit()
    finally:
        db.close()


def test_is_external_target():
    assert is_external_target("fc-target-xyz") is False
    assert is_external_target("172.20.0.3") is False
    assert is_external_target("192.168.1.1") is False
    assert is_external_target("google.com") is True
    assert is_external_target("8.8.8.8") is True


@patch("app.services.sandbox.SandboxManager.execute_kali_command")
def test_run_network_scan_rate_limiting(mock_execute):
    mock_execute.return_value = (0, "80/tcp open http\n443/tcp open ssl")

    # Scanning internal sandbox target should NOT include rate limiting timing/rate options
    run_network_scan("kali-1", "fc-target-internal")
    args, _ = mock_execute.call_args
    command_run = args[1]
    assert "-T2" not in command_run
    assert "--max-rate" not in command_run

    # Scanning external target (verified in DB) should include timing/rate limiting options
    db = SessionLocal()
    try:
        verification = DomainVerification(
            id="test-verify-ext",
            user_id="test-user",
            domain="verified-external.com",
            verification_token="token-ext",
            verified=True,
            verified_at=datetime.now(timezone.utc)
        )
        db.add(verification)
        db.commit()

        run_network_scan("kali-1", "verified-external.com")
        args, _ = mock_execute.call_args
        command_run = args[1]
        assert "-T2" in command_run
        assert "--max-rate" in command_run
        assert "10" in command_run

        # Clean up
        db.delete(verification)
        db.commit()
    finally:
        db.close()

import pytest
from backend.app.services.evidence_normalizer import normalize_finding
from backend.app.schemas.audit_state import Severity

def test_test_fixture_secret_downgrade():
    result = normalize_finding(
        title="Hardcoded AWS Access Key",
        description="A secret was found.",
        severity=Severity.CRITICAL,
        agent_source="SECRETS",
        file_path="tests/test_aws.py",
        evidence="aws_access_key_id='AKIAIOSFODNN7EXAMPLE'"
    )

    assert result["severity"] == Severity.INFO
    import json
    metadata = json.loads(result["metadata_json"])
    assert metadata["path_role"] == "test_fixture"
    assert metadata["suppressed_reason"] == "fake_example_secret"

def test_test_fixture_real_secret_downgrade():
    result = normalize_finding(
        title="Hardcoded Password",
        description="A password was found.",
        severity=Severity.HIGH,
        agent_source="SAST",
        file_path="src/__tests__/auth.test.ts",
        evidence="password='MySuperSecretPassword123!'"
    )

    assert result["severity"] == Severity.LOW
    import json
    metadata = json.loads(result["metadata_json"])
    assert metadata["path_role"] == "test_fixture"
    assert metadata["suppressed_reason"] == "test_fixture_secret"

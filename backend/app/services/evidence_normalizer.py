import json
import uuid
from typing import Any, Dict, List, Optional
from backend.app.schemas.audit_state import Finding, Severity


def is_test_fixture_path(path: str) -> bool:
    if not path:
        return False
    path = path.lower()
    test_patterns = [
        "tests/", "test/", "__tests__/", "spec/", "fixtures/",
        "mocks/", "mock/", "examples/", "sample/"
    ]
    test_suffixes = [
        "test_.py", "_test.py", ".spec.ts", ".test.ts",
        ".spec.js", ".test.js"
    ]
    for pattern in test_patterns:
        if pattern in path:
            return True
    for suffix in test_suffixes:
        if path.endswith(suffix):
            return True
    return False

def check_fake_markers(evidence: str) -> bool:
    if not evidence:
        return False
    evidence = evidence.lower()
    markers = ["example", "dummy", "fake", "test", "placeholder", "changeme", "sample", "mock"]
    for marker in markers:
        if marker in evidence:
            return True
    return False


def redact_secret_string(value: str) -> str:
    """Basic redaction to prevent secret leakage in logs/db."""
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return value[:3] + "*" * (len(value) - 6) + value[-3:]


def normalize_finding(
    title: str,
    description: str,
    severity: Severity,
    agent_source: str,
    confidence: Optional[str] = "LOW",
    scanner_name: Optional[str] = None,
    scanner_mode: Optional[str] = None,
    file_path: Optional[str] = None,
    line_number: Optional[int] = None,
    route: Optional[str] = None,
    evidence: Optional[str] = None,
    remediation: Optional[str] = None,
    cwe_id: Optional[str] = None,
    owasp_category: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Produce a normalized dictionary representing a finding.
    Applies test/fixture false-positive hygiene.
    """
    import uuid
    import json
    is_test = is_test_fixture_path(file_path or "")
    has_fake_markers = check_fake_markers(evidence or "")

    if is_test:
        if not metadata:
            metadata = {}
        metadata["path_role"] = "test_fixture"

        # Downgrade secrets in test files
        if agent_source in ["SECRETS", "SAST", "SEMGREP"]:
            if has_fake_markers:
                severity = Severity.INFO
                confidence = "LOW"
                metadata["suppressed_reason"] = "fake_example_secret"
            elif severity in [Severity.CRITICAL, Severity.HIGH]:
                severity = Severity.LOW
                confidence = "LOW"
                metadata["suppressed_reason"] = "test_fixture_secret"

    return {
        "id": str(uuid.uuid4()),
        "agent_source": agent_source,
        "title": title,
        "description": description,
        "severity": severity,
        "confidence": confidence,
        "scanner_name": scanner_name,
        "scanner_mode": scanner_mode,
        "file_path": file_path,
        "line_number": line_number,
        "route": route,
        "evidence": evidence,
        "remediation": remediation,
        "cwe_id": cwe_id,
        "owasp_category": owasp_category,
        "metadata_json": json.dumps(metadata) if metadata else None
    }



def to_finding_model(normalized: Dict[str, Any]) -> Finding:
    """
    Convert a normalized finding dict back to the Pydantic Finding model,
    preserving backward compatibility for existing logic.
    """
    return Finding(
        id=normalized["id"],
        agent_source=normalized["agent_source"],
        title=normalized["title"],
        description=normalized["description"],
        severity=normalized["severity"],
        evidence=normalized["evidence"],
        remediation=normalized["remediation"],
        cwe_id=normalized.get("cwe_id"),
        owasp_category=normalized.get("owasp_category"),
        confidence=normalized.get("confidence"),
        scanner_name=normalized.get("scanner_name"),
        scanner_mode=normalized.get("scanner_mode"),
        file_path=normalized.get("file_path"),
        line_number=normalized.get("line_number"),
        route=normalized.get("route"),
        metadata_json=normalized.get("metadata_json")
    )

def deduplicate_normalized_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate normalized findings based on title, file, and line."""
    seen = set()
    deduped = []
    for f in findings:
        key = f"{f['title']}|{f.get('file_path', '')}|{f.get('line_number', '')}|{f.get('route', '')}"
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    return deduped

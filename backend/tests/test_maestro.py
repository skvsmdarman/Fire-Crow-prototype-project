from backend.app.orchestrator.maestro import ai_analyzer_body
from backend.app.schemas.audit_state import AuditState, Finding, Severity
from unittest.mock import MagicMock

def test_maestro_ai_analyzer_routing():
    state = AuditState(
        job_id="test_job",
        static_findings=[
            Finding(
                id="finding-1",
                agent_source="SAST",
                title="Command Injection",
                description="Unsanitized subprocess call",
                severity=Severity.CRITICAL,
                file_path="app/run.py",
                line_number=42,
            )
        ],
    )
    db_mock = MagicMock()

    result = ai_analyzer_body(db_mock, state)
    assert len(result["deduplicated_findings"]) == 1
    assert result["false_positives"] == []
    assert result["remediations"] == []

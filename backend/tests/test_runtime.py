from datetime import datetime, timezone

from backend.app.models import AuditJob, SessionLocal
from backend.app.orchestrator.runtime import execute_audit_job
from backend.app.schemas import JobStatus


def test_execute_audit_job_completes_happy_path():
    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-runtime-ok",
                user_id="usr_runtime",
                repo_url="https://github.com/example/standard-repo",
                repo_branch="main",
                status=JobStatus.QUEUED,
            )
        )
        db.commit()
    finally:
        db.close()

    final_state = execute_audit_job(
        job_id="job-runtime-ok",
        user_id="usr_runtime",
        repo_url="https://github.com/example/standard-repo",
        repo_branch="main",
    )

    db = SessionLocal()
    try:
        job = db.query(AuditJob).filter(AuditJob.id == "job-runtime-ok").first()
        assert final_state.status == JobStatus.COMPLETED
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.finished_at is not None
        assert job.report_pdf_url
    finally:
        db.close()


def test_execute_audit_job_cancelled_before_sandbox(monkeypatch):
    def cancel_after_sast(clone_path: str, repo_url: str):
        db = SessionLocal()
        try:
            job = db.query(AuditJob).filter(AuditJob.id == "job-cancel-before-sandbox").first()
            assert job is not None
            job.cancel_requested = True
            job.cancel_requested_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
        return []

    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-cancel-before-sandbox",
                user_id="usr_runtime",
                repo_url="https://github.com/example/standard-repo",
                repo_branch="main",
                status=JobStatus.QUEUED,
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr("backend.app.orchestrator.maestro.run_sast", cancel_after_sast)

    final_state = execute_audit_job(
        job_id="job-cancel-before-sandbox",
        user_id="usr_runtime",
        repo_url="https://github.com/example/standard-repo",
        repo_branch="main",
    )

    db = SessionLocal()
    try:
        job = db.query(AuditJob).filter(AuditJob.id == "job-cancel-before-sandbox").first()
        assert final_state.status == JobStatus.CANCELLED
        assert job is not None
        assert job.status == JobStatus.CANCELLED
        assert job.cancel_requested is True
        assert job.report_pdf_url is None
    finally:
        db.close()


def test_execute_audit_job_cancels_during_attack_and_cleans_up(monkeypatch):
    cleanup_calls = []

    def cancel_during_attack(*args, **kwargs):
        db = SessionLocal()
        try:
            job = db.query(AuditJob).filter(AuditJob.id == "job-cancel-attack").first()
            assert job is not None
            job.cancel_requested = True
            job.cancel_requested_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
        return []

    def cleanup_spy(state):
        cleanup_calls.append((state.job_id, state.sandbox_container_id))

    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-cancel-attack",
                user_id="usr_runtime",
                repo_url="https://github.com/example/vulnerable-app",
                repo_branch="main",
                status=JobStatus.QUEUED,
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr("backend.app.orchestrator.maestro.run_dynamic_attack", cancel_during_attack)
    monkeypatch.setattr("backend.app.orchestrator.runtime.cleanup_resources", cleanup_spy)

    final_state = execute_audit_job(
        job_id="job-cancel-attack",
        user_id="usr_runtime",
        repo_url="https://github.com/example/vulnerable-app",
        repo_branch="main",
    )

    db = SessionLocal()
    try:
        job = db.query(AuditJob).filter(AuditJob.id == "job-cancel-attack").first()
        assert final_state.status == JobStatus.CANCELLED
        assert job is not None
        assert job.status == JobStatus.CANCELLED
        assert cleanup_calls == [("job-cancel-attack", "fc-kali-job-cancel-attack")]
    finally:
        db.close()


def test_execute_audit_job_cleans_up_after_mid_pipeline_exception(monkeypatch):
    cleanup_calls = []

    def failing_network_scan(*args, **kwargs):
        raise RuntimeError("network scan exploded")

    def cleanup_spy(state):
        cleanup_calls.append((state.job_id, state.sandbox_container_id))

    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-runtime-fail",
                user_id="usr_runtime",
                repo_url="https://github.com/example/vulnerable-app",
                repo_branch="main",
                status=JobStatus.QUEUED,
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr("backend.app.orchestrator.maestro.run_network_scan", failing_network_scan)
    monkeypatch.setattr("backend.app.orchestrator.maestro.run_dependency_scan", lambda *args, **kwargs: [])
    monkeypatch.setattr("backend.app.orchestrator.maestro.run_semgrep_scan", lambda *args, **kwargs: [])
    monkeypatch.setattr("backend.app.orchestrator.runtime.cleanup_resources", cleanup_spy)

    final_state = execute_audit_job(
        job_id="job-runtime-fail",
        user_id="usr_runtime",
        repo_url="https://github.com/example/vulnerable-app",
        repo_branch="main",
    )

    db = SessionLocal()
    try:
        job = db.query(AuditJob).filter(AuditJob.id == "job-runtime-fail").first()
        assert final_state.status == JobStatus.FAILED
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert "network scan exploded" in (job.error_message or "")
        assert cleanup_calls == [("job-runtime-fail", "fc-kali-job-runtime-fail")]
    finally:
        db.close()


def test_execute_audit_job_marks_partial_when_reporter_fails(monkeypatch):
    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-runtime-partial",
                user_id="usr_runtime",
                repo_url="https://github.com/example/standard-repo",
                repo_branch="main",
                status=JobStatus.QUEUED,
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr("backend.app.orchestrator.maestro.ReportGenerator.compile_pdf", lambda self, html, path: False)

    final_state = execute_audit_job(
        job_id="job-runtime-partial",
        user_id="usr_runtime",
        repo_url="https://github.com/example/standard-repo",
        repo_branch="main",
    )

    db = SessionLocal()
    try:
        job = db.query(AuditJob).filter(AuditJob.id == "job-runtime-partial").first()
        assert final_state.status == JobStatus.PARTIAL
        assert job is not None
        assert job.status == JobStatus.PARTIAL
        assert "Failed to compile report PDF" in (job.error_message or "")
    finally:
        db.close()

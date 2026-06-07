from datetime import datetime, timedelta, timezone
from backend.app.models.database import SessionLocal
from backend.app.models.audit_job import AuditJob, AgentLog, AuditArtifact
from backend.app.services.housekeeping import run_housekeeping, MAX_JOBS_PER_USER


def test_housekeeping_pruning():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # 1. Create a job older than 30 days (should be deleted entirely)
        job_old_30 = AuditJob(
            id="job_old_30",
            user_id="user_1",
            repo_url="https://github.com/test/repo1",
            created_at=now - timedelta(days=31),
        )
        db.add(job_old_30)

        # 2. Create a job older than 7 days (logs/artifacts should be pruned, job details should remain)
        job_old_7 = AuditJob(
            id="job_old_7",
            user_id="user_1",
            repo_url="https://github.com/test/repo2",
            created_at=now - timedelta(days=8),
        )
        db.add(job_old_7)

        # 3. Create a recent job (logs/artifacts/job should remain intact)
        job_recent = AuditJob(
            id="job_recent",
            user_id="user_1",
            repo_url="https://github.com/test/repo3",
            created_at=now - timedelta(hours=2),
        )
        db.add(job_recent)

        db.commit()

        # Add logs and artifacts to the jobs
        log1 = AgentLog(job_id="job_old_30", agent_name="MAESTRO", message="Old log")
        log2 = AgentLog(job_id="job_old_7", agent_name="MAESTRO", message="Log older than 7 days")
        log3 = AgentLog(job_id="job_recent", agent_name="MAESTRO", message="Recent log")

        art1 = AuditArtifact(job_id="job_old_30", artifact_type="raw", name="Old artifact")
        art2 = AuditArtifact(job_id="job_old_7", artifact_type="raw", name="Artifact older than 7 days")
        art3 = AuditArtifact(job_id="job_recent", artifact_type="raw", name="Recent artifact")

        db.add_all([log1, log2, log3, art1, art2, art3])
        db.commit()

        # Execute housekeeping
        counts = run_housekeeping(db)

        # Verify job_old_30 was deleted entirely (and cascaded its logs/artifacts)
        assert db.query(AuditJob).filter(AuditJob.id == "job_old_30").first() is None
        assert db.query(AgentLog).filter(AgentLog.job_id == "job_old_30").first() is None
        assert db.query(AuditArtifact).filter(AuditArtifact.job_id == "job_old_30").first() is None

        # Verify job_old_7 itself remains, but its logs/artifacts were deleted/pruned
        assert db.query(AuditJob).filter(AuditJob.id == "job_old_7").first() is not None
        assert db.query(AgentLog).filter(AgentLog.job_id == "job_old_7").first() is None
        assert db.query(AuditArtifact).filter(AuditArtifact.job_id == "job_old_7").first() is None

        # Verify job_recent and its logs/artifacts remain intact
        assert db.query(AuditJob).filter(AuditJob.id == "job_recent").first() is not None
        assert db.query(AgentLog).filter(AgentLog.job_id == "job_recent").first() is not None
        assert db.query(AuditArtifact).filter(AuditArtifact.job_id == "job_recent").first() is not None

    finally:
        db.close()


def test_housekeeping_max_jobs_per_user():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        user_id = "overflow_user"

        # Create MAX_JOBS_PER_USER + 5 jobs for this user
        total_created = MAX_JOBS_PER_USER + 5
        for i in range(total_created):
            job = AuditJob(
                id=f"overflow_job_{i}",
                user_id=user_id,
                repo_url="https://github.com/test/overflow",
                # Make older jobs have earlier created_at timestamps
                created_at=now - timedelta(minutes=total_created - i),
            )
            db.add(job)
        db.commit()

        # Verify all total_created jobs exist before housekeeping
        initial_count = db.query(AuditJob).filter(AuditJob.user_id == user_id).count()
        assert initial_count == total_created

        # Run housekeeping
        run_housekeeping(db)

        # Verify only MAX_JOBS_PER_USER jobs remain
        final_count = db.query(AuditJob).filter(AuditJob.user_id == user_id).count()
        assert final_count == MAX_JOBS_PER_USER

        # Verify that the oldest 5 jobs were deleted (overflow_job_0 to overflow_job_4)
        for i in range(5):
            assert db.query(AuditJob).filter(AuditJob.id == f"overflow_job_{i}").first() is None

        # Verify that the newest ones remain (e.g. overflow_job_5 to overflow_job_24)
        for i in range(5, total_created):
            assert db.query(AuditJob).filter(AuditJob.id == f"overflow_job_{i}").first() is not None

    finally:
        db.close()

import logging
from backend.app.orchestrator.runtime import execute_audit_job
from backend.app.models import SessionLocal, AuditJob

logger = logging.getLogger("firecrow.verification")

def verify_fix_on_branch(original_job_id: str, repo_url: str, branch_name: str, original_finding_ids: list) -> dict:
    job_id = f"verify_{original_job_id}_{branch_name[:8]}"
    db = SessionLocal()
    try:
        job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
        if not job:
            job = AuditJob(
                id=job_id,
                user_id="system_verifier",
                repo_url=repo_url,
                repo_branch=branch_name,
            )
            db.add(job)
            db.commit()
    except Exception as e:
        logger.error(f"Error creating audit job for verification: {e}")
        db.rollback()
    finally:
        db.close()

    verify_state = execute_audit_job(
        job_id=job_id,
        user_id="system_verifier",
        repo_url=repo_url,
        repo_branch=branch_name,
        custom_email=""
    )
    still_present = [fid for fid in original_finding_ids if any(f.id == fid for f in verify_state.deduplicated_findings)]
    report_url = f"/api/v1/audit/job/{job_id}/report"
    return {
        "verified": len(still_present) == 0,
        "still_present": still_present,
        "new_findings": len(verify_state.deduplicated_findings),
        "report_url": report_url
    }

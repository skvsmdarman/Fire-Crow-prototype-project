import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "backend"
sys.path.append(str(BASE))

# Stub service to avoid DB requirement
class StubReportService:
    def fetch_job(self, job_id):
        # Return a minimal AuditJob‑like object
        class DummyJob:
            def __init__(self):
                self.id = job_id
                self.status = "completed"
                self.results = []
        return DummyJob()

    def save_report(self, job_id, data):
        print(f"[Stub] Report for {job_id} would be saved (size={len(str(data))} chars)")
        return None

# Import the real Reporter after path is set
from app.services.reporter import Reporter

def main():
    job_id = "dryrun-001"
    service = StubReportService()
    reporter = Reporter(report_service=service)
    try:
        payload = reporter.generate_report(job_id=job_id)
        print("✅ Reporter succeeded – payload keys:", payload.keys())
    except Exception as exc:  # noqa: BLE001
        print("❌ Reporter raised an exception:", exc)

if __name__ == "__main__":
    main()

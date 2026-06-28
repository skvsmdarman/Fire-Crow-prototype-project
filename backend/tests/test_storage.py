from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.storage import StorageService


def test_storage_service_persists_artifact_locally(tmp_path):
    with patch("app.services.storage.LOCAL_STORAGE_DIR", tmp_path):
        service = StorageService()
        service.storage_root = tmp_path

        db_mock = MagicMock()
        retention_query = MagicMock()
        retention_query.filter.return_value.first.side_effect = [None, None]
        db_mock.query.return_value = retention_query

        artifact = service.upload_artifact(
            db=db_mock,
            file_data=b"test data",
            organization_id="org1",
            artifact_type="report_pdf",
            file_name="test.pdf",
            user_id="user-1",
            job_id="job-1",
        )

        stored_path = tmp_path / artifact.object_key
        assert artifact.storage_provider == "local_db"
        assert stored_path.exists()
        assert stored_path.read_bytes() == b"test data"
        assert service.is_s3_active() is False


def test_download_artifact_local_returns_saved_file(tmp_path):
    with patch("app.services.storage.LOCAL_STORAGE_DIR", tmp_path):
        service = StorageService()
        service.storage_root = tmp_path

        artifact_path = tmp_path / "tenants" / "org1" / "finding_evidence" / "artifact.txt"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("evidence", encoding="utf-8")

        artifact = MagicMock()
        artifact.object_key = "tenants/org1/finding_evidence/artifact.txt"
        artifact.mime_type = "text/plain"
        artifact.organization_id = "org1"
        artifact.job_id = None

        db_mock = MagicMock()
        db_mock.query.return_value.filter.return_value.first.return_value = artifact

        with patch.object(service, "verify_tenant_access", return_value=True):
            file_path, file_name, media_type = service.download_artifact_local(db_mock, "artifact-id", "user-1")

        assert Path(file_path) == artifact_path
        assert file_name == "artifact.txt"
        assert media_type == "text/plain"

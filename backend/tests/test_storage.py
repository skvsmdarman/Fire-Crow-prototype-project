import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock boto3 and botocore before importing anything that might need it
mock_boto3 = MagicMock()
mock_s3_client = MagicMock()
mock_boto3.client.return_value = mock_s3_client
sys.modules['boto3'] = mock_boto3

mock_botocore = MagicMock()
sys.modules['botocore'] = mock_botocore
sys.modules['botocore.client'] = MagicMock()

from backend.app.services.storage import StorageService
from backend.app.config import _global_state

def test_storage_service_r2_disable_on_auth_failure():
    # Reset the disabled flag
    _global_state["r2_disabled"] = False
    
    with patch("backend.app.services.storage.settings") as mock_settings:
        mock_settings.R2_ENDPOINT_URL = "http://localhost:9000"
        mock_settings.R2_ACCESS_KEY_ID = "invalid_key"
        mock_settings.R2_SECRET_ACCESS_KEY = "invalid_secret"
        mock_settings.R2_BUCKET_NAME = "test-bucket"
        mock_settings.REPORT_LOCAL_FALLBACK = True
        
        # Reset mock_s3_client behavior
        mock_s3_client.reset_mock()
        mock_s3_client.put_object.reset_mock()
        
        service = StorageService()
        assert service.is_s3_active() is True
        
        # Simulate a Malformed Access Key Id exception on put_object
        client_error = Exception("An error occurred (InvalidAccessKeyId) when calling the PutObject operation: Malformed Access Key Id")
        mock_s3_client.put_object.side_effect = client_error
        
        with patch.object(service, "_write_local_file") as mock_write_local:
            db_mock = MagicMock()
            db_mock.query.return_value.filter.return_value.first.return_value = None
            
            # Run upload_artifact
            artifact = service.upload_artifact(
                db=db_mock,
                file_data=b"test data",
                organization_id="org1",
                artifact_type="report_pdf",
                file_name="test.pdf"
            )
            
            assert artifact.storage_provider == "local"
            assert _global_state["r2_disabled"] is True
            assert service.is_s3_active() is False
            
            # Verify subsequent calls immediately bypass S3
            mock_s3_client.put_object.reset_mock()
            
            artifact2 = service.upload_artifact(
                db=db_mock,
                file_data=b"test data 2",
                organization_id="org1",
                artifact_type="report_pdf",
                file_name="test2.pdf"
            )
            
            assert artifact2.storage_provider == "local"
            mock_s3_client.put_object.assert_not_called()

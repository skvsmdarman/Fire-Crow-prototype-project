import pytest
import sys
from unittest.mock import patch, MagicMock

def test_import_storage_service_succeeds():
    """Test importing backend.app.services.storage succeeds."""
    import backend.app.services.storage as storage_module
    assert storage_module is not None

def test_storage_service_and_singleton_exist():
    """Test both StorageService and storage_service exist."""
    from backend.app.services.storage import StorageService, storage_service
    assert StorageService is not None
    assert storage_service is not None
    assert isinstance(storage_service, StorageService)

def test_import_routes_storage_succeeds():
    """Test importing backend.app.api.routes_storage succeeds."""
    import backend.app.api.routes_storage as routes_storage
    assert routes_storage is not None

def test_import_main_app_succeeds():
    """Test importing backend.app.main succeeds."""
    with patch("backend.app.config.settings.SECRET_KEY", "test-key-123"):
        from backend.app.main import app
        assert app is not None

def test_missing_optional_storage_env_does_not_crash_app_import():
    """Test missing optional storage env does not crash app import."""
    with patch("backend.app.config.settings.R2_ENDPOINT_URL", None), \
         patch("backend.app.config.settings.R2_ACCESS_KEY_ID", None), \
         patch("backend.app.config.settings.R2_SECRET_ACCESS_KEY", None), \
         patch("backend.app.config.settings.SECRET_KEY", "test-key-123"):

        # Import the storage module explicitly to trigger the init without the env variables
        from backend.app.services.storage import StorageService
        service = StorageService()

        # S3 should be deactivated due to missing variables
        assert service.is_s3_active() is False
        assert service.s3_client is None

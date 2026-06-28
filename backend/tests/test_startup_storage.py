from unittest.mock import patch

def test_import_storage_service_succeeds():
    """Test importing app.services.storage succeeds."""
    import app.services.storage as storage_module
    assert storage_module is not None

def test_storage_service_and_singleton_exist():
    """Test both StorageService and storage_service exist."""
    from app.services.storage import StorageService, storage_service
    assert StorageService is not None
    assert storage_service is not None
    assert isinstance(storage_service, StorageService)

def test_import_routes_storage_succeeds():
    """Test importing app.api.routes_storage succeeds."""
    import app.api.routes_storage as routes_storage
    assert routes_storage is not None

def test_import_main_app_succeeds():
    """Test importing app.main succeeds."""
    with patch("app.config.settings.SECRET_KEY", "test-key-123"):
        from app.main import app
        assert app is not None

def test_storage_service_is_local_only():
    """Storage service should stay importable without any cloud-storage configuration."""
    with patch("app.config.settings.SECRET_KEY", "test-key-123"):
        from app.services.storage import StorageService

        service = StorageService()

        assert service.is_s3_active() is False
        assert service.s3_client is None

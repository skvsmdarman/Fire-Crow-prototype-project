import pytest
from pydantic import ValidationError

def test_storage_config_validation():
    from backend.app.config import Settings

    # Should raise error if no cloud config and local fallback is False
    with pytest.raises(ValueError, match="Cloud storage configuration is missing"):
        Settings(
            DEBUG=False,
            SECRET_KEY="supersecretkeythatisatleast32charslong",
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            FIRE_CROW_SCANNER_IMAGE="image:1.0",
            REPORT_LOCAL_FALLBACK=False,
            R2_ACCESS_KEY_ID="",
        )

    # Should pass if local fallback is True
    Settings(
        DEBUG=False,
        SECRET_KEY="supersecretkeythatisatleast32charslong",
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        FIRE_CROW_SCANNER_IMAGE="image:1.0",
        REPORT_LOCAL_FALLBACK=True,
    )

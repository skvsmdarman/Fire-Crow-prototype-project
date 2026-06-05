import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Set environment variables at the very top to force in-memory or SQLite database for tests
# This must happen before any backend imports are triggered.
os.environ["DATABASE_URL"] = "sqlite:///test_firecrow.db"
os.environ["SECRET_KEY"] = "test_secret_key"
os.environ["DEBUG"] = "True"
os.environ["FIRE_CROW_MOCK_SANDBOX"] = "True"

from backend.app.models.database import Base, engine, SessionLocal


@pytest.fixture(autouse=True, scope="function")
def setup_test_db():
    """
    Ensure the test database schema is created before each test and dropped after.
    Since DATABASE_URL is set to a local SQLite file, all imports use this database.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # Drop tables to ensure clean slate for subsequent tests
    Base.metadata.drop_all(bind=engine)
    
    # Remove the temporary database file if it exists
    if os.path.exists("test_firecrow.db"):
        try:
            os.remove("test_firecrow.db")
        except Exception:
            pass

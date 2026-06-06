import logging
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.app.config import settings

from typing import Any, Generator

logger = logging.getLogger("firecrow.models.database")

db_url = settings.DATABASE_URL
engine: Any = None

if "postgresql" in db_url:
    try:
        connect_args: dict[str, Any] = {"connect_timeout": 5}
        if not settings.DEBUG:
            connect_args["sslmode"] = "require"
            
        # Create a test engine to verify connection
        test_engine = create_engine(
            db_url, 
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        with test_engine.connect() as conn:
            conn.execute(select(1))
        engine = test_engine
        logger.info("Successfully connected to PostgreSQL database.")
    except Exception as e:
        if not settings.DEBUG:
            # In production, PostgreSQL MUST be available — do not fall back to SQLite
            logger.critical(
                "FATAL: Cannot connect to PostgreSQL in production: %s. "
                "Set DATABASE_URL to a valid PostgreSQL connection string.",
                str(e),
            )
            raise RuntimeError(f"PostgreSQL connection required in production: {e}") from e

        logger.warning(
            "Failed to connect to PostgreSQL database: %s. "
            "Falling back to local SQLite database 'firecrow.db'.",
            str(e),
        )
        db_url = "sqlite:///firecrow.db"

if engine is None:
    # Initialize engine for SQLite or other URL
    engine = create_engine(db_url)
    logger.info("Initialized database engine using URL: %s", db_url)


def _ensure_audit_job_compatibility() -> None:
    if engine is None:
        return
    inspector = inspect(engine)
    if inspector is None:
        return
    if "audit_jobs" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("audit_jobs")}
    with engine.begin() as conn:
        if "cancel_requested" not in columns:
            conn.exec_driver_sql("ALTER TABLE audit_jobs ADD COLUMN cancel_requested BOOLEAN NOT NULL DEFAULT false")
        if "cancel_requested_at" not in columns:
            conn.exec_driver_sql("ALTER TABLE audit_jobs ADD COLUMN cancel_requested_at TIMESTAMP")


def _ensure_user_compatibility() -> None:
    if engine is None:
        return
    inspector = inspect(engine)
    if inspector is None:
        return
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as conn:
        if "github_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN github_id VARCHAR(255)")
        if "google_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN google_id VARCHAR(255)")
        if "privacy_policy_version" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN privacy_policy_version VARCHAR(64)")
        if "privacy_policy_accepted_at" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN privacy_policy_accepted_at TIMESTAMP")


_ensure_audit_job_compatibility()
_ensure_user_compatibility()

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for modern SQLAlchemy 2.0 models
class Base(DeclarativeBase):
    pass


# Dependency for FastAPI endpoints to yield a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import logging
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.app.config import settings
from backend.app.services.redaction import redact_text

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
                redact_text(str(e)),
            )
            raise RuntimeError("PostgreSQL connection required in production.") from e

        logger.warning(
            "Failed to connect to PostgreSQL database: %s. "
            "Falling back to local SQLite database 'firecrow.db'.",
            redact_text(str(e)),
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
        if "auto_email_reports" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN auto_email_reports BOOLEAN DEFAULT true")
        if "github_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN github_id VARCHAR(255)")
        if "github_access_token" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN github_access_token TEXT")
        if "github_token_scopes" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN github_token_scopes TEXT")
        if "github_token_updated_at" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN github_token_updated_at TIMESTAMP")
        if "google_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN google_id VARCHAR(255)")
        if "privacy_policy_version" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN privacy_policy_version VARCHAR(64)")
        if "privacy_policy_accepted_at" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN privacy_policy_accepted_at TIMESTAMP")
        if "terms_version" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN terms_version VARCHAR(64)")
        if "terms_accepted_at" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN terms_accepted_at TIMESTAMP")
        if "first_login_at" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN first_login_at TIMESTAMP")
        if "last_login_at" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP")
        if "last_logout_at" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN last_logout_at TIMESTAMP")
        if "activity_log" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN activity_log TEXT")
        try:
            if engine.dialect.name == "postgresql":
                conn.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lower_unique "
                    "ON users (lower(email)) WHERE email IS NOT NULL"
                )
            elif engine.dialect.name == "sqlite":
                conn.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lower_unique "
                    "ON users (lower(email)) WHERE email IS NOT NULL"
                )
        except Exception:
            logger.warning(
                "Could not create unique normalized users.email index. Existing duplicate emails may need manual review.",
                exc_info=True,
            )



def ensure_database_compatibility() -> None:
    _ensure_audit_job_compatibility()
    _ensure_user_compatibility()


def check_pending_migrations() -> bool:
    """Returns True if there are pending migrations, False otherwise.
    Safely handles cases where Alembic or the database is not configured.
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        import os

        # Root of backend
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
        script = ScriptDirectory.from_config(alembic_cfg)
        
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            
        heads = script.get_heads()
        if not heads:
            return False
            
        # If current_rev is None, check if any tables exist. If no tables exist, we can't check pending.
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if not tables:
            return False
            
        head_rev = heads[0]
        if current_rev != head_rev:
            return True
        return False
    except Exception as e:
        logger.warning("Failed to check pending migrations: %s", str(e))
        return False

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

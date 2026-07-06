import logging
import time
from collections import OrderedDict
from threading import Lock
from sqlalchemy import create_engine, inspect, select, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import WORKSPACE_DIR, settings
from app.services.redaction import redact_text

from typing import Any, Optional

logger = logging.getLogger("firecrow.models.database")
LOCAL_SQLITE_URL = f"sqlite:///{(WORKSPACE_DIR / 'firecrow.db').resolve().as_posix()}"


class _QueryCache:
    """Simple in-memory TTL cache for frequently accessed database queries."""
    
    def __init__(self, default_ttl: int = 30, max_size: int = 10000):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = Lock()
        self._default_ttl = default_ttl
        self._max_size = max(1, max_size)
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _prune_expired_locked(self) -> None:
        now = time.time()
        expired_keys = [key for key, (_, expires_at) in self._cache.items() if now >= expires_at]
        for key in expired_keys:
            del self._cache[key]

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, expires_at = self._cache.pop(key)
                if time.time() < expires_at:
                    self._cache[key] = (value, expires_at)
                    self._hits += 1
                    return value
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            self._prune_expired_locked()
            self._cache.pop(key, None)
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
                self._evictions += 1
            self._cache[key] = (value, time.time() + (ttl or self._default_ttl))

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._cache[k]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{(self._hits / total * 100):.1f}%" if total > 0 else "N/A",
                "entries": len(self._cache),
                "max_size": self._max_size,
                "evictions": self._evictions,
            }


# Global query cache instance
query_cache = _QueryCache(default_ttl=30, max_size=settings.QUERY_CACHE_MAX_SIZE)


def _refresh_pool_metrics() -> None:
    try:
        from app.middleware.telemetry import observe_db_pool_metrics

        observe_db_pool_metrics(engine)
    except Exception:
        logger.debug("Failed to refresh DB pool metrics", exc_info=True)


def _register_pool_metric_hooks(db_engine: Any) -> None:
    def _pool_metric_hook(*args: Any, **kwargs: Any) -> None:
        _refresh_pool_metrics()

    for event_name in ("connect", "checkout", "checkin", "close", "invalidate"):
        try:
            event.listen(db_engine, event_name, _pool_metric_hook)
        except Exception:
            logger.debug("Failed to attach DB pool hook for %s", event_name, exc_info=True)

    _refresh_pool_metrics()

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
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=getattr(settings, "DATABASE_MAX_OVERFLOW", 10),
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
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
        db_url = LOCAL_SQLITE_URL

if engine is None:
    # Initialize engine for SQLite or other URL
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=getattr(settings, "DATABASE_MAX_OVERFLOW", 10),
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
    ) if not db_url.startswith("sqlite") else create_engine(db_url)
    logger.info("Initialized database engine using URL: %s", redact_text(db_url))

_register_pool_metric_hooks(engine)


# Legacy auto-DDL is DEPRECATED. Use Alembic migrations instead.
# This function is kept for backward compatibility during development only.
def _ensure_audit_job_compatibility() -> None:
    """
    DEPRECATED: Auto-DDL is deprecated. Use Alembic migrations for schema changes.
    This function remains for backward compatibility in DEBUG mode only.
    """
    if not settings.DEBUG:
        logger.warning(
            "Auto-DDL is deprecated and disabled in production. "
            "Use 'alembic upgrade head' to apply schema migrations."
        )
        return
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
            logger.warning("DEPRECATED: Missing 'cancel_requested' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE audit_jobs ADD COLUMN cancel_requested BOOLEAN NOT NULL DEFAULT false")
        if "cancel_requested_at" not in columns:
            logger.warning("DEPRECATED: Missing 'cancel_requested_at' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE audit_jobs ADD COLUMN cancel_requested_at TIMESTAMP")
        if "report_id" not in columns:
            logger.warning("DEPRECATED: Missing 'report_id' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE audit_jobs ADD COLUMN report_id VARCHAR(36)")
        if "security_score" not in columns:
            logger.warning("DEPRECATED: Missing 'security_score' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE audit_jobs ADD COLUMN security_score FLOAT")


def _ensure_user_compatibility() -> None:
    """
    DEPRECATED: Auto-DDL is deprecated. Use Alembic migrations for schema changes.
    This function remains for backward compatibility in DEBUG mode only.
    """
    if not settings.DEBUG:
        logger.warning(
            "Auto-DDL is deprecated and disabled in production. "
            "Use 'alembic upgrade head' to apply schema migrations."
        )
        return
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
            logger.warning("DEPRECATED: Missing 'github_id' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN github_id VARCHAR(255)")
        if "github_access_token" not in columns:
            logger.warning("DEPRECATED: Missing 'github_access_token' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN github_access_token TEXT")
        if "github_token_scopes" not in columns:
            logger.warning("DEPRECATED: Missing 'github_token_scopes' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN github_token_scopes TEXT")
        if "github_token_updated_at" not in columns:
            logger.warning("DEPRECATED: Missing 'github_token_updated_at' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN github_token_updated_at TIMESTAMP")
        if "google_id" not in columns:
            logger.warning("DEPRECATED: Missing 'google_id' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN google_id VARCHAR(255)")
        if "privacy_policy_version" not in columns:
            logger.warning("DEPRECATED: Missing 'privacy_policy_version' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN privacy_policy_version VARCHAR(64)")
        if "privacy_policy_accepted_at" not in columns:
            logger.warning("DEPRECATED: Missing 'privacy_policy_accepted_at' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN privacy_policy_accepted_at TIMESTAMP")
        if "terms_version" not in columns:
            logger.warning("DEPRECATED: Missing 'terms_version' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN terms_version VARCHAR(64)")
        if "terms_accepted_at" not in columns:
            logger.warning("DEPRECATED: Missing 'terms_accepted_at' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN terms_accepted_at TIMESTAMP")
        if "first_login_at" not in columns:
            logger.warning("DEPRECATED: Missing 'first_login_at' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN first_login_at TIMESTAMP")
        if "last_login_at" not in columns:
            logger.warning("DEPRECATED: Missing 'last_login_at' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP")
        if "last_logout_at" not in columns:
            logger.warning("DEPRECATED: Missing 'last_logout_at' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN last_logout_at TIMESTAMP")
        if "region" not in columns:
            logger.warning("DEPRECATED: Missing 'region' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN region VARCHAR(100)")
        if "timezone" not in columns:
            logger.warning("DEPRECATED: Missing 'timezone' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN timezone VARCHAR(100)")
        if "credit_balance" not in columns:
            logger.warning("DEPRECATED: Missing 'credit_balance' column. Use Alembic migration instead.")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN credit_balance FLOAT NOT NULL DEFAULT 10.0")
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

def _ensure_finding_compatibility() -> None:
    if not settings.DEBUG:
        logger.warning(
            "Auto-DDL is deprecated and disabled in production. "
            "Use 'alembic upgrade head' to apply schema migrations."
        )
        return
    if engine is None:
        return
    inspector = inspect(engine)
    if inspector is None:
        return
    if "findings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("findings")}
    with engine.begin() as conn:
        if "confidence" not in columns:
            conn.exec_driver_sql("ALTER TABLE findings ADD COLUMN confidence VARCHAR(50)")
        if "scanner_name" not in columns:
            conn.exec_driver_sql("ALTER TABLE findings ADD COLUMN scanner_name VARCHAR(100)")
        if "scanner_mode" not in columns:
            conn.exec_driver_sql("ALTER TABLE findings ADD COLUMN scanner_mode VARCHAR(50)")
        if "file_path" not in columns:
            conn.exec_driver_sql("ALTER TABLE findings ADD COLUMN file_path VARCHAR(1024)")
        if "line_number" not in columns:
            conn.exec_driver_sql("ALTER TABLE findings ADD COLUMN line_number INTEGER")
        if "route" not in columns:
            conn.exec_driver_sql("ALTER TABLE findings ADD COLUMN route VARCHAR(1024)")
        if "metadata_json" not in columns:
            conn.exec_driver_sql("ALTER TABLE findings ADD COLUMN metadata_json TEXT")


def _ensure_artifact_compatibility() -> None:
    if engine is None:
        return
    inspector = inspect(engine)
    if inspector is None:
        return
    if "audit_artifacts" not in inspector.get_table_names():
        with engine.begin() as conn:
            conn.exec_driver_sql("""
                CREATE TABLE audit_artifacts (
                    id VARCHAR(36) PRIMARY KEY,
                    job_id VARCHAR(36) NOT NULL,
                    artifact_type VARCHAR(100) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    data_json TEXT,
                    data_text TEXT,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES audit_jobs(id)
                )
            """)
            try:
                conn.exec_driver_sql("CREATE INDEX ix_audit_artifacts_job_id ON audit_artifacts (job_id)")
            except Exception:
                logger.warning("Could not create index on audit_artifacts.job_id", exc_info=True)


def _ensure_audit_report_compatibility() -> None:
    if engine is None:
        return
    inspector = inspect(engine)
    if inspector is None:
        return
    if "audit_reports" not in inspector.get_table_names():
        with engine.begin() as conn:
            conn.exec_driver_sql("""
                CREATE TABLE audit_reports (
                    id VARCHAR(36) PRIMARY KEY,
                    job_id VARCHAR(36) NOT NULL,
                    html_content TEXT,
                    markdown_content TEXT,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES audit_jobs(id)
                )
            """)
            try:
                conn.exec_driver_sql("CREATE INDEX ix_audit_reports_job_id ON audit_reports (job_id)")
            except Exception:
                logger.warning("Could not create index on audit_reports.job_id", exc_info=True)


def _ensure_compliance_compatibility() -> None:
    if engine is None:
        return
    inspector = inspect(engine)
    if inspector is None:
        return

    # 1. Check/add audit_jobs.tenant_id
    if "audit_jobs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("audit_jobs")}
        if "tenant_id" not in columns:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE audit_jobs ADD COLUMN tenant_id VARCHAR(255)")

    # 2. Create missing compliance tables
    existing_tables = set(inspector.get_table_names())
    new_tables = [
        "organizations",
        "memberships",
        "data_processing_records",
        "retention_policies",
        "artifact_objects",
        "compliance_events",
        "privacy_requests",
        "authorization_attestations",
        "secret_redaction_events",
    ]

    # Import the compliance models here to make sure they are in metadata

    tables_to_create = []
    for table_name in new_tables:
        if table_name not in existing_tables:
            table_obj = Base.metadata.tables.get(table_name)
            if table_obj is not None:
                tables_to_create.append(table_obj)

    if tables_to_create:
        logger.info("Creating missing compliance tables: %s", [t.name for t in tables_to_create])
        Base.metadata.create_all(bind=engine, tables=tables_to_create)


def _ensure_session_and_failure_compatibility() -> None:
    if engine is None:
        return
    inspector = inspect(engine)
    if inspector is None:
        return
    existing_tables = set(inspector.get_table_names())
    tables_to_create = []

    # Import models here to make sure they are in Base.metadata

    for table_name in ["login_failures", "user_sessions", "auth_exchange_codes", "push_subscriptions"]:
        if table_name not in existing_tables:
            table_obj = Base.metadata.tables.get(table_name)
            if table_obj is not None:
                tables_to_create.append(table_obj)

    if tables_to_create:
        logger.info("Creating missing session/failure tables: %s", [t.name for t in tables_to_create])
        Base.metadata.create_all(bind=engine, tables=tables_to_create)


def _ensure_indexes() -> None:
    """Create performance indexes for frequently queried columns."""
    if engine is None:
        return
    
    indexes_to_create = [
        # Audit jobs - most queried table
        ("ix_audit_jobs_user_status", "audit_jobs", "user_id, status"),
        ("ix_audit_jobs_created_at", "audit_jobs", "created_at DESC"),
        ("ix_audit_jobs_user_created", "audit_jobs", "user_id, created_at DESC"),
        
        # Findings - join-heavy queries
        ("ix_findings_job_severity", "findings", "job_id, severity"),
        ("ix_findings_scanner", "findings", "scanner_name"),
        ("ix_findings_cwe", "findings", "cwe_id"),
        
        # Agent logs - time-series queries
        ("ix_agent_logs_job_timestamp", "agent_logs", "job_id, timestamp"),
        
        # Phase ledger - execution tracking
        ("ix_phase_ledger_job", "phase_ledger", "job_id"),
        
        # User sessions - auth lookups
        ("ix_user_sessions_user_id", "user_sessions", "user_id"),
        ("ix_user_sessions_token_family", "user_sessions", "token_family"),
        
        # Login failures - brute force detection
        ("ix_login_failures_user_window", "login_failures", "user_id, created_at"),
        
        # Compliance events - audit trail
        ("ix_compliance_events_user_timestamp", "compliance_events", "user_id, created_at DESC"),
    ]
    
    with engine.begin() as conn:
        for index_name, table_name, columns in indexes_to_create:
            try:
                if engine.dialect.name == "postgresql":
                    conn.exec_driver_sql(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns})"
                    )
                elif engine.dialect.name == "sqlite":
                    # SQLite doesn't support IF NOT EXISTS for indexes, so we catch and ignore
                    try:
                        conn.exec_driver_sql(
                            f"CREATE INDEX {index_name} ON {table_name} ({columns})"
                        )
                    except Exception:
                        pass  # Index already exists
            except Exception as e:
                logger.debug("Could not create index %s: %s", index_name, str(e))
    
    logger.info("Database indexes ensured for performance optimization.")


def ensure_database_compatibility() -> None:
    """
    DEPRECATED: This function provides backward compatibility for legacy auto-DDL.
    In production, all schema changes must be managed via Alembic migrations.
    This function is disabled in production and only runs in DEBUG mode.
    """
    if not settings.DEBUG:
        logger.warning(
            "ensure_database_compatibility() is deprecated in production. "
            "Use Alembic migrations for all schema changes."
        )
        return

    logger.warning(
        "ensure_database_compatibility() is deprecated. "
        "Use Alembic migrations for all schema changes: 'alembic revision --autogenerate -m <message>'"
    )
    _ensure_audit_job_compatibility()
    _ensure_user_compatibility()
    _ensure_finding_compatibility()
    _ensure_artifact_compatibility()
    _ensure_audit_report_compatibility()
    _ensure_compliance_compatibility()
    _ensure_session_and_failure_compatibility()
    _ensure_indexes()



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

import logging
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.app.config import settings
from backend.app.services.redaction import redact_text
from neo4j import GraphDatabase

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

neo4j_driver = None
if settings.NEO4J_URI:
    neo4j_driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )
    try:
        neo4j_driver.verify_connectivity()
        logger.info("Successfully connected to Neo4j database.")
    except Exception as e:
        logger.critical("Failed to connect to Neo4j database: %s", str(e))
        raise


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
        if "auto_push" not in columns:
            conn.exec_driver_sql("ALTER TABLE audit_jobs ADD COLUMN auto_push BOOLEAN NOT NULL DEFAULT false")


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
    if settings.NEO4J_URI:
        logger.info("Ensuring database compatibility in Neo4j (setting up unique constraints)...")
        with neo4j_driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT FOR (u:User) REQUIRE u.id IS UNIQUE",
                "CREATE CONSTRAINT FOR (u:User) REQUIRE u.username IS UNIQUE",
                "CREATE CONSTRAINT FOR (j:AuditJob) REQUIRE j.id IS UNIQUE",
                "CREATE CONSTRAINT FOR (f:FindingModel) REQUIRE f.id IS UNIQUE",
                "CREATE CONSTRAINT FOR (l:AgentLog) REQUIRE l.id IS UNIQUE",
                "CREATE CONSTRAINT FOR (s:SecurityLog) REQUIRE s.id IS UNIQUE"
            ]
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.debug("Failed to create constraint: %s", str(e))
        return

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
if settings.NEO4J_URI:
    import uuid
    from datetime import datetime
    from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList, UnaryExpression
    from sqlalchemy.sql.operators import eq, ne, or_ as or_op, and_ as and_op

    def evaluate_sqlalchemy_expr(expr):
        if expr is None:
            return "", {}
            
        if isinstance(expr, BooleanClauseList):
            clauses = expr.clauses
            op_name = " OR " if expr.operator == or_op else " AND "
            parts = []
            combined_params = {}
            for clause in clauses:
                clause_str, clause_params = evaluate_sqlalchemy_expr(clause)
                if clause_str:
                    parts.append(f"({clause_str})")
                    combined_params.update(clause_params)
            if parts:
                return op_name.join(parts), combined_params
            return "", {}
            
        elif isinstance(expr, BinaryExpression):
            left = expr.left
            right = expr.right
            op = expr.operator
            
            col_name = getattr(left, "name", None) or str(left)
            if "." in col_name:
                col_name = col_name.split(".")[-1]
                
            val = right.value if hasattr(right, "value") else right
            if hasattr(right, "effective_value"):
                val = right.effective_value
            elif hasattr(right, "element") and hasattr(right.element, "value"):
                val = right.element.value
                
            if hasattr(val, "value"):
                val = val.value
                
            param_name = f"param_{col_name}_{uuid.uuid4().hex[:6]}"
            
            if op == eq:
                if val is None:
                    return f"n.{col_name} IS NULL", {}
                return f"n.{col_name} = ${param_name}", {param_name: val}
            elif op == ne:
                if val is None:
                    return f"n.{col_name} IS NOT NULL", {}
                return f"n.{col_name} <> ${param_name}", {param_name: val}
            elif op.__name__ in ("in_op", "notin_op"):
                is_in = op.__name__ == "in_op"
                if not isinstance(val, (list, set, tuple)):
                    val = [val]
                val_list = [v.value if hasattr(v, "value") else v for v in val]
                op_str = "IN" if is_in else "NOT IN"
                return f"n.{col_name} {op_str} ${param_name}", {param_name: val_list}
            elif op.__name__ in ("like_op", "ilike_op"):
                val_str = str(val)
                import re
                escaped = re.escape(val_str).replace(r'\%', '.*')
                regex_val = f"(?i){escaped}" if op.__name__ == "ilike_op" else escaped
                return f"n.{col_name} =~ ${param_name}", {param_name: regex_val}
                
        return "", {}

    def get_object_properties(obj):
        props = {}
        for key, value in obj.__dict__.items():
            if key.startswith('_sa_') or key == '_sa_instance_state':
                continue
            if hasattr(value, "value"):
                props[key] = value.value
            elif isinstance(value, datetime):
                props[key] = value.isoformat()
            else:
                props[key] = value
        return props

    def node_to_model(node, model_class):
        from sqlalchemy.orm.instrumentation import manager_of_class

        # Use SQLAlchemy's own mechanism so that _sa_instance_state is a real
        # InstanceState object (not None). This is critical: any attribute
        # assignment through a SQLAlchemy descriptor (e.g. user.email = "x")
        # calls state._modified_event(...), which would crash if state is None.
        manager = manager_of_class(model_class)
        instance = manager.new_instance()

        properties = dict(node)
        datetime_fields = set()
        if hasattr(model_class, "__table__"):
            for col in model_class.__table__.columns:
                from sqlalchemy import DateTime
                if isinstance(col.type, DateTime):
                    datetime_fields.add(col.name)

        # Populate via __dict__ to bypass change-tracking on initial load —
        # the instance is transient/detached so there is no session to notify.
        for key, value in properties.items():
            if key in datetime_fields and isinstance(value, str):
                try:
                    instance.__dict__[key] = datetime.fromisoformat(value)
                except ValueError:
                    instance.__dict__[key] = value
            else:
                instance.__dict__[key] = value

        if hasattr(model_class, "__table__"):
            for col in model_class.__table__.columns:
                if col.name not in instance.__dict__:
                    instance.__dict__[col.name] = None

        return instance

    class Neo4jSession:
        def __init__(self, driver):
            self.driver = driver
            self.new_objects = []
            self.deleted_objects = []

        def add(self, obj):
            if obj not in self.new_objects:
                self.new_objects.append(obj)

        def add_all(self, objs):
            for obj in objs:
                self.add(obj)

        def delete(self, obj):
            if obj not in self.deleted_objects:
                self.deleted_objects.append(obj)

        def commit(self):
            with self.driver.session() as session:
                session.execute_write(self._commit_tx)

        def _resolve_pk_defaults(self, obj):
            """
            Invoke SQLAlchemy column default callables for any primary-key
            field that is still None.  This mirrors what SQLAlchemy would do
            during an INSERT but which our Neo4j path skips entirely.
            """
            model_class = type(obj)
            if not hasattr(model_class, "__table__"):
                return
            for col in model_class.__table__.columns:
                if not col.primary_key:
                    continue
                # Only fix when the attribute is missing or None
                current = obj.__dict__.get(col.name)
                if current is not None:
                    continue
                if col.default is not None and callable(col.default.arg):
                    obj.__dict__[col.name] = col.default.arg(None)

        def _commit_tx(self, tx):
            # 1. Resolve auto-increment AgentLog IDs (integer PK, not uuid)
            for obj in self.new_objects:
                label = type(obj).__name__
                if label == "AgentLog" and getattr(obj, "id", None) is None:
                    res = tx.run("MATCH (n:AgentLog) RETURN max(n.id) as max_id")
                    max_id = res.single()["max_id"]
                    obj.id = (max_id or 0) + 1

            # 2. Resolve callable SQLAlchemy column defaults for all other PKs
            #    (e.g. SecurityLog.id, FindingModel.id, AuditJob.id use uuid lambdas)
            for obj in self.new_objects:
                self._resolve_pk_defaults(obj)

            for obj in self.new_objects:
                label = type(obj).__name__
                props = get_object_properties(obj)
                pk = "id"
                if label == "User" and "id" not in props:
                    pk = "username"
                pk_val = props.get(pk)
                
                query = f"MERGE (n:{label} {{{pk}: $pk_val}}) SET n += $props"
                tx.run(query, pk_val=pk_val, props=props)
                
                if label == "FindingModel" and props.get("job_id"):
                    tx.run(
                        "MATCH (f:FindingModel {id: $f_id}), (j:AuditJob {id: $j_id}) "
                        "MERGE (f)-[:BELONGS_TO]->(j)",
                        f_id=props["id"], j_id=props["job_id"]
                    )
                elif label == "AgentLog" and props.get("job_id"):
                    tx.run(
                        "MATCH (l:AgentLog {id: $l_id}), (j:AuditJob {id: $j_id}) "
                        "MERGE (l)-[:LOGGED_FOR]->(j)",
                        l_id=props["id"], j_id=props["job_id"]
                    )
                elif label == "AuditJob" and props.get("user_id"):
                    tx.run(
                        "MATCH (j:AuditJob {id: $j_id}), (u:User {id: $u_id}) "
                        "MERGE (j)-[:OWNED_BY]->(u)",
                        j_id=props["id"], u_id=props["user_id"]
                    )

            for obj in self.deleted_objects:
                label = type(obj).__name__
                props = get_object_properties(obj)
                pk = "id"
                if label == "User" and "id" not in props:
                    pk = "username"
                pk_val = props.get(pk)
                if pk_val:
                    tx.run(f"MATCH (n:{label} {{{pk}: $pk_val}}) DETACH DELETE n", pk_val=pk_val)
                    
            self.new_objects.clear()
            self.deleted_objects.clear()

        def refresh(self, obj):
            label = type(obj).__name__
            props = get_object_properties(obj)
            pk = "id"
            if label == "User" and "id" not in props:
                pk = "username"
            pk_val = props.get(pk)
            if pk_val:
                with self.driver.session() as session:
                    res = session.run(f"MATCH (n:{label} {{{pk}: $pk_val}}) RETURN n", pk_val=pk_val)
                    record = res.single()
                    if record:
                        node = record["n"]
                        reloaded = node_to_model(node, type(obj))
                        obj.__dict__.update(reloaded.__dict__)

        def close(self):
            pass
            
        def expire_all(self):
            pass

        def query(self, model):
            return Neo4jQuery(self.driver, model)

    class Neo4jQuery:
        def __init__(self, driver, model):
            self.driver = driver
            self.model = model
            self.filters = []
            self.order_by_clause = ""
            self.limit_val = None
            self.offset_val = None

        def filter(self, *exprs):
            for expr in exprs:
                if expr is not None:
                    self.filters.append(expr)
            return self

        def order_by(self, *criteria):
            parts = []
            for crit in criteria:
                if isinstance(crit, UnaryExpression):
                    col = crit.element.name
                    direction = "DESC" if crit.modifier.__name__ == "desc_op" else "ASC"
                    parts.append(f"n.{col} {direction}")
                elif hasattr(crit, "name"):
                    parts.append(f"n.{crit.name} ASC")
                else:
                    crit_str = str(crit)
                    if crit_str.startswith("audit_jobs.") or crit_str.startswith("agent_logs.") or crit_str.startswith("findings."):
                        crit_str = crit_str.split(".")[-1]
                    parts.append(f"n.{crit_str}")
            if parts:
                self.order_by_clause = "ORDER BY " + ", ".join(parts)
            return self

        def limit(self, limit):
            self.limit_val = limit
            return self

        def offset(self, offset):
            self.offset_val = offset
            return self

        def all(self):
            return self._execute()

        def first(self):
            self.limit_val = 1
            results = self._execute()
            return results[0] if results else None

        def count(self):
            label = self.model.__name__
            where_clauses = []
            combined_params = {}
            for expr in self.filters:
                clause, params = evaluate_sqlalchemy_expr(expr)
                if clause:
                    where_clauses.append(clause)
                    combined_params.update(params)
                    
            where_str = " AND ".join(where_clauses)
            where_clause = f"WHERE {where_str}" if where_str else ""
            
            query = f"MATCH (n:{label}) {where_clause} RETURN count(n) as count"
            with self.driver.session() as session:
                res = session.run(query, **combined_params)
                record = res.single()
                return record["count"] if record else 0

        def _execute(self):
            label = self.model.__name__
            where_clauses = []
            combined_params = {}
            for expr in self.filters:
                clause, params = evaluate_sqlalchemy_expr(expr)
                if clause:
                    where_clauses.append(clause)
                    combined_params.update(params)
                    
            where_str = " AND ".join(where_clauses)
            where_clause = f"WHERE {where_str}" if where_str else ""
            
            order_clause = self.order_by_clause
            limit_clause = f"LIMIT {self.limit_val}" if self.limit_val is not None else ""
            offset_clause = f"SKIP {self.offset_val}" if self.offset_val is not None else ""
            
            query = f"MATCH (n:{label}) {where_clause} RETURN n {order_clause} {offset_clause} {limit_clause}"
            results = []
            with self.driver.session() as session:
                res = session.run(query, **combined_params)
                for record in res:
                    node = record["n"]
                    obj = node_to_model(node, self.model)
                    results.append(obj)
            return results

    class Neo4jSessionLocal:
        def __call__(self):
            return Neo4jSession(neo4j_driver)
        def close(self):
            pass

    SessionLocal = Neo4jSessionLocal()

    def get_db():
        db = Neo4jSession(neo4j_driver)
        try:
            yield db
        finally:
            db.close()
else:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


class Base(DeclarativeBase):
    pass

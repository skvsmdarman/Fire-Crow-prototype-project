# Fire Crow Database Models Package
from backend.app.models.database import Base, engine, SessionLocal, get_db
from backend.app.models.audit_job import AuditJob, FindingModel, AgentLog
from backend.app.models.user import User
from backend.app.models.security_log import SecurityLog
from backend.app.models.role import Role

import sqlalchemy.orm
try:
    sqlalchemy.orm.configure_mappers()
except Exception as e:
    import logging
    logging.getLogger("firecrow.models").warning("Failed to configure SQLAlchemy mappers on import: %s", str(e))


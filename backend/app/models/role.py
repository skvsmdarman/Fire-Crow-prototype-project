import uuid
from sqlalchemy import Column, String, Boolean
from app.models.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    
    # Permissions
    can_start_scans = Column(Boolean, default=False)
    can_view_reports = Column(Boolean, default=False)
    can_manage_users = Column(Boolean, default=False)
    can_manage_billing = Column(Boolean, default=False)

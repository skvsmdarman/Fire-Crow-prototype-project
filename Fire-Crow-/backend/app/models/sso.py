from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class SSOProvider(Base):
    __tablename__ = "sso_providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    issuer_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    client_secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authorization_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    token_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    userinfo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    jwks_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    certificate: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attribute_mapping: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    domains: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enforce_mfa: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_provision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_role_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class SSOSession(Base):
    __tablename__ = "sso_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    id_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

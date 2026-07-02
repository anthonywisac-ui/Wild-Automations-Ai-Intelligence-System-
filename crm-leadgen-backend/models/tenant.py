# Inspired By: TADD multi-tenant design
# Feature: Tenant ORM model
# Reason: Store tenant data and config
# ============================================================

from sqlalchemy import Column, String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDMixin, TimestampMixin

class Tenant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    leads = relationship("Lead", back_populates="tenant", lazy="selectin")
    conversations = relationship("Conversation", back_populates="tenant", lazy="selectin")

class TenantConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenant_configs"
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    config_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config_data: Mapped[dict] = mapped_column(JSON, nullable=False)

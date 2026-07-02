# Inspired By: TADD Unified Lead Schema
# Feature: Lead ORM model
# Reason: Persist lead data
# ============================================================

from sqlalchemy import Column, String, Float, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDMixin, TimestampMixin

class Lead(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "leads"
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    company: Mapped[str] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="new")
    enrichment_data: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    tenant = relationship("Tenant", back_populates="leads")
    conversations = relationship("Conversation", back_populates="lead", lazy="selectin")

    __table_args__ = (
        Index("ix_leads_tenant_email", "tenant_id", "email"),
        Index("ix_leads_tenant_company", "tenant_id", "company"),
        Index("ix_leads_tenant_status", "tenant_id", "status"),
    )

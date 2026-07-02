# Inspired By: enrichment job tracking
# Feature: Enrichment job model
# Reason: Track status and results of enrichment jobs
# ============================================================

from sqlalchemy import Column, String, JSON, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, UUIDMixin, TimestampMixin

class EnrichmentJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "enrichment_jobs"
    lead_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    enricher_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    error: Mapped[str] = mapped_column(String(500), nullable=True)

# Inspired By: Event-driven architecture
# Feature: Event schemas
# Reason: Standardize internal and external events
# ============================================================

from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class EventSchema(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    tenant_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class WebhookEvent(BaseModel):
    source: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    signature: Optional[str] = None

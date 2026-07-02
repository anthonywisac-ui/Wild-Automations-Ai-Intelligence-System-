# Inspired By: TADD Unified Lead Schema
# Feature: Lead schemas
# Reason: Validate and serialize lead data
# ============================================================

from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator
from ..utils.validators import validate_email, validate_phone, normalize_phone

class LeadCreate(BaseModel):
    tenant_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("phone")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not validate_phone(v):
            raise ValueError("Invalid phone number format")
        return normalize_phone(v) if v else v

class LeadUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, pattern="^(new|contacted|qualified|lost)$")
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("phone")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not validate_phone(v):
            raise ValueError("Invalid phone number format")
        return normalize_phone(v) if v else v

class LeadResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    source: str
    score: float = 0.0
    status: str = "new"
    enrichment_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class LeadScoreRequest(BaseModel):
    lead_id: UUID
    scoring_model: Optional[str] = "default"

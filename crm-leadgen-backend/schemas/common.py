# Inspired By: common pagination patterns
# Feature: Shared schemas for pagination, filtering
# Reason: Consistent API query parameters
# ============================================================

from typing import Optional, List, Any, Literal
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

class Pagination(BaseModel):
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)

    @field_validator("limit")
    @classmethod
    def clamp_limit(cls, v: int) -> int:
        return min(v, 1000)

class SortOrder(BaseModel):
    field: str
    direction: Literal["asc", "desc"] = "asc"

class Filter(BaseModel):
    field: str
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "contains", "in"]
    value: Any

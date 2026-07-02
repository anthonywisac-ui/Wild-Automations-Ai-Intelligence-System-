"""
Search Types — Wave 2 shared, framework-agnostic schema.

Pydantic models for the persona → pain → intent → source planning flow. Every
IntentQuery carries full Provenance (which persona + pain + tier produced it),
and every SearchPlan carries a trace_id so a run is traceable end-to-end.

No framework imports (FastAPI/test_ui) — reusable from any context.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CampaignType(str, Enum):
    LEAD_GENERATION = "lead_generation"
    RECRUITMENT = "recruitment"
    UNIVERSITY = "university"
    VISA = "visa"
    CARS = "cars"
    CUSTOM = "custom"


class BuyerPersona(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    name: str
    sector: str = ""
    size: str = ""
    region: str = ""
    attributes: Dict[str, Any] = Field(default_factory=dict)
    origin: str = ""   # blueprint:<niche> | llm:<provider> | config | heuristic


class PainPoint(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    persona_id: str = ""
    friction: str
    department: str = ""
    urgency: int = 3   # 1-5


class Provenance(BaseModel):
    """Why a query exists — full lineage for debugging + learning."""
    trace_id: str = ""
    campaign: str = ""
    persona_id: str = ""
    persona_name: str = ""
    pain_id: str = ""
    pain_friction: str = ""
    tier: str = ""
    origin: str = ""


class IntentQuery(BaseModel):
    text: str
    tier: str = ""
    platform: str = ""
    discovery_mode: str = ""                         # business|intent|opportunity|competitor
    lead_safe: bool = True                            # False for competitor queries
    score: Optional[Dict[str, Any]] = None           # QueryScore (buyer/seller prob, quality…)
    provenance: Provenance = Field(default_factory=Provenance)


class PlannedSource(BaseModel):
    name: str
    reliability: float = 0.65   # 0..1 blended (config + learned)
    reason: str = ""


class SearchPlan(BaseModel):
    trace_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    campaign: str = CampaignType.CUSTOM.value
    service: str = ""
    location: str = ""
    personas: List[BuyerPersona] = Field(default_factory=list)
    target_categories: List[str] = Field(default_factory=list)   # concrete buyer businesses
    pains: List[PainPoint] = Field(default_factory=list)
    modes: List[str] = Field(default_factory=list)               # discovery modes used
    queries: List[IntentQuery] = Field(default_factory=list)     # lead-safe queries
    competitor_queries: List[IntentQuery] = Field(default_factory=list)  # isolated
    sources: List[PlannedSource] = Field(default_factory=list)
    origin: str = ""

    def as_legacy_dict(self) -> Dict[str, Any]:
        """Backward-compatible shape consumed by the existing intent_planner API."""
        tiers: Dict[str, List[str]] = {}
        for q in self.queries:
            tiers.setdefault(q.tier or "hot", []).append(q.text)
        return {
            "buyer_personas": [p.name for p in self.personas],
            "pain_points": [p.friction for p in self.pains],
            "intent_queries": tiers,
            "priority_sources": [s.name for s in self.sources],
            "gmaps_keywords": [p.name for p in self.personas][:5],
            "_origin": self.origin,
            "_trace_id": self.trace_id,
        }

# Inspired By: Planner module design (from earlier)
# Feature: Planner input/output schemas
# Reason: Define structured planning data
# ============================================================

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class BusinessType(str, Enum):
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    B2B_SERVICES = "b2b_services"
    CONSULTING = "consulting"
    AGENCY = "agency"
    FINANCIAL = "financial"
    HEALTHCARE = "healthcare"
    REAL_ESTATE = "real_estate"
    OTHER = "other"

class Goal(str, Enum):
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    CONVERSION = "conversion"
    RETENTION = "retention"
    ENRICHMENT = "enrichment"

class PlannerInput(BaseModel):
    business_type: BusinessType
    country: str
    goal: Goal
    offer: str
    target_industry: Optional[str] = None
    target_audience: Optional[str] = None
    budget_constraint: Optional[float] = None
    time_constraint: Optional[int] = None

class SearchPlan(BaseModel):
    keywords: List[str]
    locations: List[str]
    platforms: List[str]
    search_depth: str
    filters: Dict[str, Any] = Field(default_factory=dict)

class SourcePriority(BaseModel):
    source_name: str
    priority: int = Field(ge=1, le=10)
    reason: str
    estimated_cost: float = 0.0

class PluginExecutionStep(BaseModel):
    plugin_name: str
    plugin_type: str
    dependencies: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    estimated_duration_seconds: int = 60
    priority: int = 1

class RiskAssessment(BaseModel):
    overall_risk: str = Field(..., description="low, medium, high")
    blockers: List[str] = Field(default_factory=list)
    mitigation_strategies: List[str] = Field(default_factory=list)

class BuyingIntentStrategy(BaseModel):
    signals: List[str]
    scoring_rules: Dict[str, Any]
    triggers: List[str] = Field(default_factory=list)

class PlannerOutput(BaseModel):
    search_plan: SearchPlan
    priority_sources: List[SourcePriority]
    plugin_execution_order: List[PluginExecutionStep]
    budget: float
    estimated_time_minutes: int
    risk: RiskAssessment
    buying_intent_strategy: BuyingIntentStrategy
    rationale: str
    alternative_plans: List[Dict[str, Any]] = Field(default_factory=list)

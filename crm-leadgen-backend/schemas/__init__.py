# Inspired By: TADD Unified Lead Schema
# Feature: Pydantic schemas for data transfer and validation
# Reason: Type-safe API contracts and internal data exchange
# ============================================================

from .common import Pagination, SortOrder, Filter
from .lead import LeadCreate, LeadUpdate, LeadResponse, LeadScoreRequest
from .config import TenantConfig, AgentConfig, ChannelConfig
from .event import EventSchema, WebhookEvent
from .planner import PlannerInput, PlannerOutput, SearchPlan, SourcePriority, PluginExecutionStep, RiskAssessment, BuyingIntentStrategy

__all__ = [
    "Pagination", "SortOrder", "Filter",
    "LeadCreate", "LeadUpdate", "LeadResponse", "LeadScoreRequest",
    "TenantConfig", "AgentConfig", "ChannelConfig",
    "EventSchema", "WebhookEvent",
    "PlannerInput", "PlannerOutput", "SearchPlan", "SourcePriority",
    "PluginExecutionStep", "RiskAssessment", "BuyingIntentStrategy",
]

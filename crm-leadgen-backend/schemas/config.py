# Inspired By: TADD configuration patterns
# Feature: Tenant, agent, channel configuration schemas
# Reason: Manage multi-tenant and agent settings
# ============================================================

from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class ChannelConfig(BaseModel):
    channel_type: str
    enabled: bool = True
    credentials: Dict[str, str] = Field(default_factory=dict)
    webhook_url: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)

class AgentConfig(BaseModel):
    agent_id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    script: Dict[str, Any] = Field(default_factory=dict)
    llm_model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000

class TenantConfig(BaseModel):
    tenant_id: UUID = Field(default_factory=uuid4)
    name: str
    active: bool = True
    agent_configs: List[AgentConfig] = Field(default_factory=list)
    channel_configs: List[ChannelConfig] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)

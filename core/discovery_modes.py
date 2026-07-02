"""
Discovery Modes — Search Planning layer.

Multi-stage lead discovery: each mode generates an INDEPENDENT query plan with
its own templates, sources and tiers. Competitor mode is isolated — its queries
are flagged and MUST NOT enter the Lead pipeline.

    BUSINESS     — find target businesses by concrete category + location
    INTENT       — find businesses/people expressing pain or buying intent
    OPPORTUNITY  — detect hiring / expansion / funding / poor-reviews / stale web
    COMPETITOR   — find competitors (market intel only; never a Lead)
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List


class DiscoveryMode(str, Enum):
    BUSINESS = "business"
    INTENT = "intent"
    OPPORTUNITY = "opportunity"
    COMPETITOR = "competitor"


# Modes that feed the Lead pipeline. COMPETITOR is deliberately excluded.
LEAD_SAFE_MODES = {DiscoveryMode.BUSINESS, DiscoveryMode.INTENT, DiscoveryMode.OPPORTUNITY}

# Per-mode config: which query-template group, sources, and tiers to use.
MODE_CONFIG: Dict[str, Dict] = {
    "business": {
        "template_group": "business_target",
        "sources": ["google_maps", "google", "marketplace"],
        "tiers": ["hot", "problem"],
        "uses": "target_category",     # {category} = concrete business type
    },
    "intent": {
        "template_group": "buyer_intent",
        "sources": ["reddit", "facebook", "instagram", "x", "google"],
        "tiers": ["problem", "hot", "hiring"],
        "uses": "pain",                # {q}/{pain} = buyer pain, never the service
    },
    "opportunity": {
        "template_group": "opportunity",
        "sources": ["news", "linkedin", "google_maps", "reddit"],
        "tiers": ["hiring", "problem"],
        "uses": "signal",              # hiring/funding/reviews signals
    },
    "competitor": {
        "template_group": "competitor",
        "sources": ["google", "google_maps", "linkedin"],
        "tiers": ["hot", "comparison"],
        "uses": "service",             # the service itself → providers (isolated)
    },
}


def config(mode: DiscoveryMode) -> Dict:
    return MODE_CONFIG.get(mode.value, MODE_CONFIG["intent"])


def is_lead_safe(mode: DiscoveryMode) -> bool:
    return mode in LEAD_SAFE_MODES

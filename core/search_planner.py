"""
Search Planner — Wave 2 orchestrator.

Coordinates the think-first flow for a campaign:

    service + campaign_type
        → Persona Engine       (who buys / who to target)
        → Pain Engine          (their operational friction)
        → Intent Query Gen     (platform-specific, provenance-tagged queries)
        → Source Reliability   (rank sources; config + learned)
        → SearchPlan (trace_id, full lineage)

Supports multiple campaign types (lead_generation, recruitment, university,
visa, cars, custom) via data/campaign_types.json. Every stage logs the trace_id
so a run is traceable end-to-end. Framework-agnostic.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import (discovery_modes, intent_query_generator, pain_engine, persona_engine,
                  source_reliability, target_business_engine)
from core.discovery_modes import DiscoveryMode
from core.search_types import (BuyerPersona, CampaignType, IntentQuery, PainPoint,
                               PlannedSource, SearchPlan)

logger = logging.getLogger(__name__)

_CAMPAIGNS = Path(__file__).resolve().parent.parent / "data" / "campaign_types.json"

_DEFAULT_CAMPAIGN = {
    "default_sources": ["google", "google_maps"],
    "tiers": ["hot", "warm", "problem"],
    "location_aware": True,
}


def _campaign_config(campaign_type: str) -> Dict[str, Any]:
    try:
        data = json.loads(_CAMPAIGNS.read_text(encoding="utf-8")).get("campaigns", {})
        return data.get(campaign_type) or _DEFAULT_CAMPAIGN
    except Exception as exc:
        logger.warning("search_planner: campaign config load failed: %s", exc)
        return _DEFAULT_CAMPAIGN


_DEFAULT_MODES = [DiscoveryMode.BUSINESS, DiscoveryMode.INTENT, DiscoveryMode.OPPORTUNITY]


async def plan_campaign(
    service: str,
    campaign_type: str = CampaignType.LEAD_GENERATION.value,
    *,
    location: str = "",
    max_personas: int = 3,
    modes: Optional[List[str]] = None,
) -> SearchPlan:
    """Buyer-first, multi-mode, scored & gated SearchPlan.

    Flow: Service → Persona → TARGET BUSINESSES → Buyer Intent/Pain → scored,
    validated queries per discovery mode → ranked sources. Competitor queries are
    isolated (never entered into the lead-safe query set).
    """
    plan = SearchPlan(campaign=campaign_type, service=service, location=location)
    # requested modes (default = the three lead-safe modes; competitor only if asked)
    req = [DiscoveryMode(m) if isinstance(m, str) else m for m in (modes or _DEFAULT_MODES)]
    plan.modes = [m.value for m in req]
    src_names: List[str] = _campaign_config(campaign_type).get(
        "default_sources", _DEFAULT_CAMPAIGN["default_sources"])
    logger.info("search_planner[%s]: campaign=%s service=%r modes=%s",
                plan.trace_id, campaign_type, service, plan.modes)

    # 1. Personas
    try:
        personas = await persona_engine.generate(service)
    except Exception as exc:
        logger.warning("search_planner[%s]: persona engine failed: %s", plan.trace_id, exc)
        personas = [BuyerPersona(name=service, origin="heuristic")]
    plan.personas = personas[:max_personas]
    plan.origin = personas[0].origin if personas else "heuristic"

    # 2. TARGET BUSINESSES — concrete searchable categories that BUY the service
    try:
        plan.target_categories = await target_business_engine.targets_for(service)
    except Exception as exc:
        logger.warning("search_planner[%s]: target-business engine failed: %s", plan.trace_id, exc)
        plan.target_categories = [service]
    logger.info("search_planner[%s]: personas=%d target_businesses=%d (%s)",
                plan.trace_id, len(plan.personas), len(plan.target_categories), plan.origin)

    # 3. Pains
    pains: List[PainPoint] = []
    for persona in plan.personas:
        try:
            pains.extend(await pain_engine.generate(persona, max_pains=6))
        except Exception as exc:
            logger.warning("search_planner[%s]: pain engine failed: %s", plan.trace_id, exc)
    plan.pains = pains

    # 4. Per-mode, buyer-first, VALIDATED query generation
    persona0 = plan.personas[0] if plan.personas else None
    for mode in req:
        try:
            qs = intent_query_generator.generate_for_mode(
                service, plan.target_categories, plan.pains, mode=mode.value,
                location=location, campaign=campaign_type, trace_id=plan.trace_id,
                persona=persona0)
        except Exception as exc:
            logger.warning("search_planner[%s]: mode %s failed: %s", plan.trace_id, mode.value, exc)
            qs = []
        if mode == DiscoveryMode.COMPETITOR:
            plan.competitor_queries.extend(qs)   # isolated — never a lead
        else:
            plan.queries.extend(qs)
        logger.info("search_planner[%s]: mode=%s -> %d validated queries",
                    plan.trace_id, mode.value, len(qs))

    # 5. Source ranking (config + learned)
    try:
        for name, sc, reason in source_reliability.ranked(src_names, category=campaign_type):
            plan.sources.append(PlannedSource(name=name, reliability=sc, reason=reason))
    except Exception as exc:
        logger.warning("search_planner[%s]: source ranking failed: %s", plan.trace_id, exc)
        plan.sources = [PlannedSource(name=n) for n in src_names]

    logger.info("search_planner[%s]: PLAN ready — %d target-businesses, %d lead queries, "
                "%d competitor queries (isolated), %d sources",
                plan.trace_id, len(plan.target_categories), len(plan.queries),
                len(plan.competitor_queries), len(plan.sources))
    return plan

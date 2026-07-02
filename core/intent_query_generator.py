"""
Intent Query Generator — Wave 2.

Turns personas + pains into PLATFORM-SPECIFIC search queries (Google, Maps,
LinkedIn, Facebook, Instagram, Reddit, X, GitHub, News, RSS, Government,
Marketplace) using data-driven templates (data/query_templates.json).

Every emitted IntentQuery carries full Provenance: the persona, pain point,
intent tier, platform, campaign and trace_id that produced it.

Framework-agnostic; no query text hardcoded in code (all from templates).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.search_types import BuyerPersona, IntentQuery, PainPoint, Provenance

logger = logging.getLogger(__name__)

_TEMPLATES = Path(__file__).resolve().parent.parent / "data" / "query_templates.json"
_BLUEPRINTS = Path(__file__).resolve().parent.parent / "data" / "niche_blueprints.json"

_MAX_PER_PLATFORM_TIER = 3
_MAX_TOTAL = 40


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _blueprint_intents(sector: str) -> Dict[str, List[str]]:
    bps = _load(_BLUEPRINTS, {}).get("blueprints", {})
    return (bps.get(sector) or {}).get("intent_queries", {}) or {}


def _fill(template: str, ctx: Dict[str, str]) -> str:
    out = template
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", v)
    # drop any unfilled placeholders cleanly
    while "{" in out and "}" in out:
        i, j = out.find("{"), out.find("}")
        if i < j:
            out = (out[:i] + out[j + 1:]).strip()
        else:
            break
    return " ".join(out.split()).strip()


def _template_group(group: str) -> Dict[str, Any]:
    return _load(_TEMPLATES, {}).get("template_groups", {}).get(group, {})


def generate_for_mode(
    service: str,
    target_categories: List[str],
    pains: List[PainPoint],
    *,
    mode: str = "intent",
    location: str = "",
    campaign: str = "",
    trace_id: str = "",
    persona: Optional[BuyerPersona] = None,
    max_total: int = 30,
) -> List[IntentQuery]:
    """BUYER-FIRST, mode-aware, VALIDATED query generation.

    Fills {business}=concrete target category, {pain}=buyer pain (never the
    service, except in competitor mode). Every query is scored + gated by the
    query_validator; only accepted queries are returned for lead-safe modes,
    while competitor-mode queries are returned flagged (lead_safe=False).
    """
    from core import discovery_modes, query_validator, negative_keywords
    cfg = discovery_modes.MODE_CONFIG.get(mode, discovery_modes.MODE_CONFIG["intent"])
    group = _template_group(cfg["template_group"])
    if not group:
        return []
    lead_safe = discovery_modes.is_lead_safe(discovery_modes.DiscoveryMode(mode))
    pain_texts = [p.friction for p in (pains or [])] or [""]
    cats = target_categories or [service]
    all_negs = negative_keywords.for_service(service) if mode != "competitor" else []

    def _neg_suffix_for(business: str) -> str:
        # exclude seller terms, but NEVER a token that is part of the target
        # business itself (e.g. don't `-agency` when targeting "real estate agency")
        biz_tokens = set(business.lower().split())
        singles = [n for n in all_negs if " " not in n and n not in biz_tokens][:8]
        return " ".join(f"-{t}" for t in singles)

    out: List[IntentQuery] = []
    seen: set = set()
    for platform, tiers_map in group.items():
        for tier, tmpls in tiers_map.items():
            for tmpl in tmpls:
                for business in cats[:6]:
                    for pain in pain_texts[:3]:
                        ctx = {"business": business, "category": business, "pain": pain,
                               "service": service, "location": location, "q": business}
                        core = _fill(tmpl, ctx)     # clean text (no exclusions)
                        if not core or core.lower() in seen:
                            continue
                        seen.add(core.lower())
                        # score the CLEAN core text (exclusions must not skew scoring)
                        qs = query_validator.score_query(
                            core, platform=platform, tier=tier, mode=mode,
                            service=service, target_categories=cats)
                        if not qs.accepted:
                            continue   # gate: rejected queries never reach the scraper
                        # append per-business negative exclusions for web/maps queries
                        text = core
                        if mode != "competitor" and platform in ("google", "google_maps") \
                                and "site:" not in core:
                            suffix = _neg_suffix_for(business)
                            if suffix:
                                text = f"{core} {suffix}"
                        prov = Provenance(
                            trace_id=trace_id, campaign=campaign,
                            persona_id=persona.id if persona else "",
                            persona_name=persona.name if persona else "",
                            pain_friction=pain, tier=tier,
                            origin=f"mode:{mode}")
                        out.append(IntentQuery(
                            text=text, tier=tier, platform=platform,
                            discovery_mode=mode, lead_safe=lead_safe,
                            score=qs.model_dump(), provenance=prov))
                        if len(out) >= max_total:
                            return out
                        break  # one pain variant per (template, business) is enough
    return out


def generate(
    service: str,
    personas: List[BuyerPersona],
    pains: List[PainPoint],
    platforms: List[str],
    tiers: List[str],
    *,
    location: str = "",
    campaign: str = "",
    trace_id: str = "",
) -> List[IntentQuery]:
    """Generate platform-specific, provenance-tagged intent queries."""
    templates = _load(_TEMPLATES, {}).get("platforms", {})
    if not templates:
        logger.warning("intent_query_generator: no templates loaded")
        return []

    queries: List[IntentQuery] = []
    seen: set = set()

    # Pull ready-made buyer phrases from the persona's blueprint (per tier) when present.
    sector = personas[0].sector if personas else ""
    bp_intents = _blueprint_intents(sector)

    def _phrases_for(tier: str) -> List[str]:
        pool = list(bp_intents.get(tier, []))
        if not pool:
            pool = [service]  # fall back to the service itself
        return pool[:3]

    for platform in platforms:
        ptempl = templates.get(platform)
        if not ptempl:
            continue
        for tier in tiers:
            tmpls = ptempl.get(tier)
            if not tmpls:
                continue
            emitted = 0
            persona = personas[0] if personas else None
            pain = pains[0] if pains else None
            for tmpl in tmpls:
                for phrase in _phrases_for(tier):
                    ctx = {
                        "q": phrase,
                        "service": service,
                        "role": persona.name if persona else service,
                        "category": persona.name if persona else service,
                        "location": location,
                        "pain": pain.friction if pain else "",
                        "tech": service,
                        "signal": "hiring OR funding OR expansion",
                    }
                    text = _fill(tmpl, ctx)
                    if not text or text.lower() in seen:
                        continue
                    seen.add(text.lower())
                    prov = Provenance(
                        trace_id=trace_id, campaign=campaign,
                        persona_id=persona.id if persona else "",
                        persona_name=persona.name if persona else "",
                        pain_id=pain.id if pain else "",
                        pain_friction=pain.friction if pain else "",
                        tier=tier, origin=(persona.origin if persona else ""),
                    )
                    queries.append(IntentQuery(text=text, tier=tier, platform=platform, provenance=prov))
                    emitted += 1
                    if emitted >= _MAX_PER_PLATFORM_TIER:
                        break
                if emitted >= _MAX_PER_PLATFORM_TIER:
                    break
            if len(queries) >= _MAX_TOTAL:
                return queries[:_MAX_TOTAL]
    return queries

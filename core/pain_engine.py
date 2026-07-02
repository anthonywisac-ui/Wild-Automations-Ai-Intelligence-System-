"""
Pain Point Engine — Wave 2. Data-driven (blueprint departments + LLM).

Given a persona, returns the operational pain points / friction that persona
suffers (department-mapped, urgency-scored). Pains carry the persona_id for
provenance. No pains hardcoded here — sourced from niche blueprints + LLM.
Framework-agnostic.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.search_types import BuyerPersona, PainPoint

logger = logging.getLogger(__name__)

_BLUEPRINTS = Path(__file__).resolve().parent.parent / "data" / "niche_blueprints.json"


def _blueprint_departments(sector: str) -> List[str]:
    try:
        bps = json.loads(_BLUEPRINTS.read_text(encoding="utf-8")).get("blueprints", {})
        bp = bps.get(sector) or {}
        return bp.get("core_departments", [])
    except Exception:
        return []


# Generic operational frictions mapped to a department (data, not persona-specific).
_DEPARTMENT_PAINS = {
    "Front Desk": ["missed calls", "slow response", "reception overload"],
    "Reception": ["missed calls", "no online booking", "reception overload"],
    "Patient Coordination": ["appointment no-shows", "manual follow-up"],
    "Sales": ["lost leads", "no follow-up", "slow lead response"],
    "Marketing": ["low conversion", "no lead tracking"],
    "Customer Support": ["support inbox overload", "slow response"],
    "Reservations": ["missed reservation calls", "no online booking"],
    "Intake Desk": ["intake bottleneck", "never called back"],
    "Case Management": ["no case follow-up", "client ghosted"],
    "Billing": ["billing disputes", "manual invoicing"],
    "Lead Management": ["leads going cold", "no callback"],
    "Aftercare Support": ["no post-service follow-up"],
    "Client Relations": ["poor communication", "no updates"],
}


async def _from_llm(persona: BuyerPersona) -> Optional[List[str]]:
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return None
        prompt = (
            f"List 6-10 operational pain points a '{persona.name}' business commonly has "
            "(missed calls, slow response, no follow-up, booking issues, etc.). "
            "Return ONLY a JSON array of short pain phrases."
        )
        raw = (await llm.complete(prompt, max_tokens=220, temperature=0.4)).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            raw = raw[4:] if raw.lower().startswith("json") else raw
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        return [str(x) for x in json.loads(m.group(0) if m else raw) if x]
    except Exception as exc:
        logger.warning("pain_engine: LLM generation failed: %s", exc)
        return None


async def generate(persona: BuyerPersona, *, max_pains: int = 10) -> List[PainPoint]:
    """Return department-mapped pain points for a persona (blueprint → LLM → generic)."""
    pains: List[PainPoint] = []

    # 1. blueprint departments → mapped frictions
    for dept in _blueprint_departments(persona.sector):
        for friction in _DEPARTMENT_PAINS.get(dept, []):
            pains.append(PainPoint(persona_id=persona.id, friction=friction,
                                   department=dept, urgency=3))

    # 2. LLM enrichment (unmapped / richer)
    if len(pains) < 4:
        llm_pains = await _from_llm(persona)
        for friction in (llm_pains or []):
            pains.append(PainPoint(persona_id=persona.id, friction=friction, urgency=3))

    # 3. generic fallback
    if not pains:
        for friction in ("missed calls", "slow response", "no follow-up", "lost leads"):
            pains.append(PainPoint(persona_id=persona.id, friction=friction, urgency=3))

    # de-dup by friction, cap
    seen, unique = set(), []
    for p in pains:
        k = p.friction.lower()
        if k not in seen:
            seen.add(k)
            unique.append(p)
        if len(unique) >= max_pains:
            break
    return unique

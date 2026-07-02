"""
Visa Intelligence — Low-friction pathway detection + friction scoring (Phase 3).

Implements the "Global Passport Ease & Frontier Visa Intelligence" docs: score
how EASY a visa actually is for structured passports — no job offer needed,
points-based/centralized processing (passport-neutral), fast turnaround, rolling
availability — so the engine surfaces the lowest-friction routes.

    flags(text, meta)  -> deterministic friction signals (fast, no LLM)
    mine(record)       -> GROQ friction auditor (simplicity_score, passport_neutral)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Signals that LOWER friction (easier visa)
EASE_TERMS = [
    "no job offer", "without a job offer", "exempt from labor market", "lmia exempt",
    "lmia-exempt", "no labour market test", "points-based", "opportunity card",
    "chancenkarte", "digital nomad", "scale-up", "global talent", "innovation stream",
    "trusted partner", "fast-track", "fast track", "accelerated", "priority processing",
    "expedited", "2-week", "two-week", "immediate work authorization", "open work permit",
    "rolling availability", "no cap", "self-certified", "no prior language test",
    "centralized", "streamlined", "relaxed", "reduced processing", "short notice",
]

# Signals that RAISE friction (harder visa)
FRICTION_TERMS = [
    "labor market test", "labour market test", "lmia required", "job offer required",
    "sponsorship required", "must have a job offer", "annual cap", "quota", "lottery",
    "wait time", "backlog", "in-person interview", "embassy interview", "long processing",
]

NEW_ROUTE_TERMS = ["new visa route", "newly launched", "launch", "new pathway",
                   "just introduced", "new subclass", "pilot program"]


def _hits(text: str, terms: List[str]) -> List[str]:
    t = (text or "").lower()
    return [term for term in terms if term in t]


def flags(text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deterministic visa-ease signals from a record's text + metadata."""
    m = meta or {}
    blob = f"{text} {json.dumps(m, default=str)}".lower()

    ease = _hits(blob, EASE_TERMS)
    friction = _hits(blob, FRICTION_TERMS)
    new_route = bool(_hits(blob, NEW_ROUTE_TERMS))

    # Negation-aware: "no job offer required" / "without a job offer" → NOT required
    no_offer = any(k in blob for k in ("no job offer", "without a job offer",
                                       "job offer not required", "exempt from labor",
                                       "exempt from labour", "lmia exempt", "lmia-exempt"))
    requires_job_offer = (not no_offer) and any(
        k in blob for k in ("job offer required", "sponsorship required",
                            "must have a job offer", "requires a job offer"))
    passport_neutral = any(k in blob for k in
                           ("points-based", "centralized", "global talent",
                            "opportunity card", "chancenkarte", "digital nomad"))

    # simplicity 0..10 (10 = no job offer + centralized + fast)
    raw = 4 + 1.2 * len(ease) - 1.5 * len(friction) + (2 if passport_neutral else 0) \
        + (1 if new_route else 0) - (3 if requires_job_offer else 0)
    simplicity = max(0, min(10, round(raw, 1)))

    level = "Low" if simplicity >= 7 else "Medium" if simplicity >= 4 else "High"
    return {
        "friction_level": level,
        "simplicity_score": simplicity,
        "ease_terms": ease[:4],
        "friction_terms": friction[:3],
        "is_new_route": new_route,
        "requires_job_offer": requires_job_offer,
        "passport_neutral": passport_neutral,
    }


async def mine(record: Dict[str, Any]) -> Dict[str, Any]:
    """GROQ friction auditor (best-effort): simplicity, passport neutrality, bypass value."""
    text = f"{record.get('title','')} {record.get('description','')}"
    m = record.get("metadata") or {}
    det = flags(text, m)
    if det["simplicity_score"] == 0 and not det["ease_terms"] and not det["is_new_route"]:
        return det
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return det
        prompt = (
            "You are a global immigration policy analyst. From the visa text, output ONLY "
            "JSON: {\"application_simplicity_score\": 1-10 (10 = no job offer/complex docs), "
            "\"requires_job_offer\": true/false, "
            "\"passport_neutral_design\": true/false (centralized processing that bypasses "
            "backlogged local embassies), "
            "\"strategic_bypass_value\": one short sentence}. "
            f"Text: {text[:600]}"
        )
        raw = (await llm.complete(prompt, max_tokens=180, temperature=0.3)).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            raw = raw[4:] if raw.lower().startswith("json") else raw
        mt = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(mt.group(0) if mt else raw)
        if data.get("application_simplicity_score") is not None:
            try:
                det["simplicity_score"] = float(data["application_simplicity_score"])
                det["friction_level"] = ("Low" if det["simplicity_score"] >= 7
                                         else "Medium" if det["simplicity_score"] >= 4 else "High")
            except (ValueError, TypeError):
                pass
        det["requires_job_offer"] = data.get("requires_job_offer", det["requires_job_offer"])
        det["passport_neutral"] = data.get("passport_neutral_design", det["passport_neutral"])
        det["bypass_value"] = data.get("strategic_bypass_value")
    except Exception as exc:
        logger.warning("visa_intel: mine LLM failed: %s", exc)
    return det

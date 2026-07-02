"""
Review Miner — Agent 2 from the multi-agent spec.

Reads a business's public signals (rating, review volume, category, and any
review text) and isolates OPERATIONAL PAIN — the friction that means the
business is bleeding leads and is therefore a hot prospect.

Two entry points:
    mine_business(place)  -> pain hypothesis from rating/volume/category (fast, GROQ)
    mine_reviews(texts)   -> structured pain records per review (full Agent-2 extraction)

Deterministic pain-likelihood (no LLM) is always computed; GROQ adds the
qualitative friction hypothesis + recommended offer when a provider is present.
The rule of thumb (from the niche blueprints): high review volume + a rating
BELOW ~4.2 = systemic back-office/front-desk failure = high-value lead.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Friction lexicon → bucket
_FRICTION_KEYWORDS = {
    "missed calls": ["missed call", "no answer", "never answers", "phone", "unreachable", "no one picks"],
    "slow response": ["slow", "late reply", "waited", "no response", "took days", "hours to respond"],
    "no follow up": ["no follow up", "never called back", "ghosted", "no callback", "forgot"],
    "booking issues": ["booking", "appointment", "reservation", "double booked", "cancelled"],
    "whatsapp ignored": ["whatsapp no reply", "dm", "sent a message", "no reply on whatsapp"],
    "staff behavior": ["rude", "unprofessional", "attitude", "unhelpful"],
    "billing issues": ["overcharged", "billing", "refund", "hidden charge"],
}


def _pain_likelihood(rating: Optional[float], reviews: Optional[int]) -> float:
    """0..1 — high review volume + sub-4.2 rating = high operational pain."""
    if not rating:
        return 0.35 if reviews else 0.2
    # rating 5.0 → ~0 pain, 3.0 → high pain
    rating_pain = max(0.0, min(1.0, (4.6 - rating) / 1.6))
    volume = 0.0
    if reviews:
        import math
        volume = min(1.0, math.log10(reviews + 1) / 3)  # 1000 reviews ≈ 1.0
    return round(min(1.0, 0.65 * rating_pain + 0.35 * volume), 3)


def _keyword_frictions(text: str) -> List[str]:
    t = (text or "").lower()
    return [bucket for bucket, kws in _FRICTION_KEYWORDS.items() if any(k in t for k in kws)]


async def mine_business(place: Dict[str, Any]) -> Dict[str, Any]:
    """Pain hypothesis for a Maps business from rating/volume/category (best-effort GROQ)."""
    rating = place.get("rating")
    reviews = place.get("review_count")
    category = place.get("category") or place.get("keyword") or "business"
    name = place.get("name") or "business"
    likelihood = _pain_likelihood(rating, reviews)

    result = {
        "pain_likelihood": likelihood,
        "rating": rating, "review_count": reviews,
        "likely_friction": [], "department": None,
        "recommended_offer": None,
    }

    # GROQ friction hypothesis for any business showing meaningful pain likelihood
    # (low rating alone qualifies — review count is a bonus, not a gate).
    if likelihood < 0.3:
        return result
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return result
        prompt = (
            "You are an elite review/pain analyst for a B2B automation vendor. "
            f"Business: '{name}' | category: {category} | rating: {rating} | reviews: {reviews}. "
            "Based on this category and rating, output ONLY JSON: "
            "{\"likely_friction\": [2-4 operational pains like 'missed calls','booking delays','slow whatsapp response'], "
            "\"department\": 'the team that fails (front desk/reception/sales/support)', "
            "\"recommended_offer\": 'one automation to pitch them (<=8 words)'}."
        )
        raw = (await llm.complete(prompt, max_tokens=180, temperature=0.3)).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            raw = raw[4:] if raw.lower().startswith("json") else raw
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0) if m else raw)
        result["likely_friction"] = data.get("likely_friction", [])[:4]
        result["department"] = data.get("department")
        result["recommended_offer"] = data.get("recommended_offer")
    except Exception as exc:
        logger.warning("review_miner: mine_business LLM failed: %s", exc)
    return result


async def mine_reviews(texts: List[str], business: str = "") -> List[Dict[str, Any]]:
    """Full Agent-2 extraction: structured pain record per (low-star) review."""
    records = []
    for t in (texts or []):
        buckets = _keyword_frictions(t)
        if not buckets:
            continue
        records.append({
            "business": business,
            "review_text": t[:220],
            "friction_categories": buckets,
            "urgency_level": min(5, 2 + len(buckets)),
            "sentiment": "negative" if buckets else "neutral",
        })
    return records

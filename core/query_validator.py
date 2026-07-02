"""
Query Validator + Search-Strategy Scorer — Search Planning layer.

Every generated query is scored BEFORE execution and gated:
    - buyer_probability      (targets a buyer expressing need / a target business)
    - seller_probability     (names the service / contains seller terms)
    - intent_strength        (buying-intent verbs / pain framing / tier)
    - source_suitability     (platform ↔ discovery-mode fit)
    - expected_lead_quality  (composite)
    - confidence             (how sure we are)

A query only passes when buyer_probability is high AND seller_probability is low
(except in Competitor Discovery mode, where seller queries are allowed but the
result is flagged competitor and MUST NOT enter the Lead pipeline).

Deterministic, framework-agnostic. This is the hard gate — no query reaches the
scraper unless `accepted` is True.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core import negative_keywords

logger = logging.getLogger(__name__)

# Buyer-intent / pain markers (a business/person expressing a NEED).
_BUYER_MARKERS = ("looking for", "need", "recommend", "anyone know", "help with",
                  "struggling", "not working", "poor", "no whatsapp", "missed",
                  "complaint", "reviews", "hiring", "our ")
# Source ↔ discovery-mode suitability.
_SOURCE_FIT = {
    "business":    {"google_maps": 1.0, "google": 0.6, "marketplace": 0.7,
                    "facebook": 0.3, "instagram": 0.3, "reddit": 0.2, "linkedin": 0.4},
    "intent":      {"reddit": 1.0, "facebook": 0.8, "instagram": 0.7, "x": 0.7,
                    "google": 0.6, "google_maps": 0.2, "linkedin": 0.6},
    "opportunity": {"google_maps": 0.8, "news": 1.0, "linkedin": 0.9, "reddit": 0.6,
                    "google": 0.7, "github": 0.7},
    "competitor":  {"google": 1.0, "google_maps": 1.0, "linkedin": 0.8},
}
_ACCEPT_BUYER_MIN = 0.55
_ACCEPT_SELLER_MAX = 0.5


class QueryScore(BaseModel):
    text: str
    platform: str = ""
    tier: str = ""
    mode: str = ""
    buyer_probability: float = 0.0
    seller_probability: float = 0.0
    intent_strength: float = 0.0
    source_suitability: float = 0.0
    expected_lead_quality: float = 0.0
    confidence: float = 0.0
    accepted: bool = False
    reason: str = ""


def _seller_probability(text: str, service: str, target_categories: List[str]) -> float:
    t = text.lower()
    negs = negative_keywords.for_service(service)
    hits = sum(1 for n in negs if n in t)
    # A query that names a concrete target business category is buyer-oriented,
    # which suppresses seller probability even if a service word appears.
    targets_business = any(cat.lower() in t for cat in (target_categories or []))
    base = min(1.0, 0.35 * hits)
    if targets_business:
        base *= 0.3
    # exact service-name-as-target (e.g. "marketing agency in dubai") = strong seller
    if re.search(r"\bagency\b|\bagencies\b|\bservices\b|\bconsultant\b", t) and not targets_business:
        base = max(base, 0.8)
    return round(min(1.0, base), 3)


def _buyer_probability(text: str, target_categories: List[str], seller_p: float) -> float:
    t = text.lower()
    targets_business = any(cat.lower() in t for cat in (target_categories or []))
    buyer_markers = sum(1 for m in _BUYER_MARKERS if m in t)
    score = 0.2 + (0.5 if targets_business else 0.0) + min(0.4, 0.12 * buyer_markers)
    score *= (1.0 - 0.7 * seller_p)   # sellerness drags buyer probability down
    return round(max(0.0, min(1.0, score)), 3)


def _intent_strength(text: str, tier: str) -> float:
    t = text.lower()
    tier_base = {"hot": 0.7, "problem": 0.75, "warm": 0.55, "hiring": 0.7,
                 "comparison": 0.5}.get(tier, 0.4)
    markers = sum(1 for m in _BUYER_MARKERS if m in t)
    return round(min(1.0, tier_base + 0.08 * markers), 3)


def score_query(text: str, *, platform: str = "", tier: str = "", mode: str = "intent",
                service: str = "", target_categories: Optional[List[str]] = None) -> QueryScore:
    """Score a single query and decide acceptance for the given discovery mode."""
    target_categories = target_categories or []
    seller_p = _seller_probability(text, service, target_categories)
    buyer_p = _buyer_probability(text, target_categories, seller_p)
    intent = _intent_strength(text, tier)
    suit = _SOURCE_FIT.get(mode, {}).get(platform, 0.5)
    quality = round(buyer_p * (0.5 + 0.5 * intent) * (0.6 + 0.4 * suit), 3)
    confidence = round(0.5 + 0.5 * (1.0 - abs(buyer_p - (1 - seller_p))), 3)

    if mode == "competitor":
        accepted, reason = True, "competitor-mode (isolated; never enters Lead pipeline)"
    elif buyer_p >= _ACCEPT_BUYER_MIN and seller_p <= _ACCEPT_SELLER_MAX:
        accepted, reason = True, "buyer-oriented"
    else:
        accepted = False
        reason = (f"rejected: buyer={buyer_p} < {_ACCEPT_BUYER_MIN}" if buyer_p < _ACCEPT_BUYER_MIN
                  else f"rejected: seller={seller_p} > {_ACCEPT_SELLER_MAX}")

    return QueryScore(
        text=text, platform=platform, tier=tier, mode=mode,
        buyer_probability=buyer_p, seller_probability=seller_p,
        intent_strength=intent, source_suitability=round(suit, 3),
        expected_lead_quality=quality, confidence=confidence,
        accepted=accepted, reason=reason,
    )

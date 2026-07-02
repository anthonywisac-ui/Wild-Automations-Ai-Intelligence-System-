"""
Ticket Segmentation Engine — deterministic High / Mid / Low classification.

Runs BEFORE scraping/enrichment so the planner, UI, AI explanation, and outreach
planner all share one estimate of deal size and how to sell into it.

Given a target business category (and optional signals: employees, revenue,
review_count), it returns a TicketProfile:

    ticket            High | Mid | Low
    expected_budget   monthly service budget band (USD)
    maturity          business maturity descriptor
    employees         estimated headcount band
    revenue_tier      estimated annual revenue band
    urgency           typical buying urgency
    sales_cycle       expected time-to-close
    decision_maker    who signs off
    outreach          recommended first-touch strategy

Deterministic keyword classification (fail-soft → Mid/unknown). No LLM.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TicketProfile:
    ticket: str
    expected_budget: str
    maturity: str
    employees: str
    revenue_tier: str
    urgency: str
    sales_cycle: str
    decision_maker: str
    outreach: str
    matched_category: str = ""
    confidence: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Segment templates (the sales playbook per tier) ───────────────────────────
_SEGMENTS: Dict[str, Dict[str, str]] = {
    "High": {
        "expected_budget": "$5,000–$50,000+/mo",
        "maturity": "Established / enterprise",
        "employees": "200+",
        "revenue_tier": "$10M+",
        "urgency": "Low–Medium (committee-driven)",
        "sales_cycle": "2–6 months",
        "decision_maker": "C-suite / Head of Marketing / Procurement",
        "outreach": "Warm intro or multi-touch ABM; LinkedIn + email; lead with ROI/case studies",
    },
    "Mid": {
        "expected_budget": "$800–$5,000/mo",
        "maturity": "Growing SMB",
        "employees": "10–200",
        "revenue_tier": "$1M–$10M",
        "urgency": "Medium (owner/manager driven)",
        "sales_cycle": "2–6 weeks",
        "decision_maker": "Owner / GM / Marketing Manager",
        "outreach": "Direct call + WhatsApp/email; lead with a specific gap you found",
    },
    "Low": {
        "expected_budget": "$100–$800/mo",
        "maturity": "Small / local",
        "employees": "1–10",
        "revenue_tier": "<$1M",
        "urgency": "High but price-sensitive",
        "sales_cycle": "Days–2 weeks",
        "decision_maker": "Owner",
        "outreach": "WhatsApp/DM or walk-in; lead with quick win + clear price",
    },
}

# ── Category → tier keyword maps (word-boundary matched, longest first) ────────
_HIGH = [
    "hospital", "real estate developer", "property developer", "law firm",
    "enterprise saas", "manufactur", "university", "college", "airline",
    "hotel", "resort", "luxury", "construction", "automotive group", "car dealership",
    "dealership", "insurance company", "bank", "developer", "oil", "logistics",
    "shipping", "pharmaceutical", "hospitality group", "franchise group",
]
_MID = [
    "dental clinic", "dental", "clinic", "medical center", "gym", "fitness",
    "restaurant", "accounting firm", "accountant", "travel agency", "furniture store",
    "education institute", "institute", "training center", "retail chain", "dealership",
    "veterinary", "spa", "physiotherapy", "optician", "pharmacy", "school",
    "car rental", "event", "catering", "interior design",
]
_LOW = [
    "salon", "barber", "cafe", "coffee shop", "local shop", "repair shop",
    "phone repair", "small ecommerce", "home service", "cleaning service",
    "plumber", "electrician", "handyman", "tailor", "laundry", "food truck",
    "kiosk", "boutique", "florist", "pet grooming", "nail",
]

# order matters: check High → Mid → Low so specific enterprise terms win
_TIER_ORDER: List[tuple] = [("High", _HIGH), ("Mid", _MID), ("Low", _LOW)]


def _match_tier(category: str) -> tuple:
    """Return (tier, matched_keyword, confidence). Fail-soft → ('Mid','',0.4)."""
    c = (category or "").lower().strip()
    if not c:
        return "Mid", "", 0.3
    for tier, keywords in _TIER_ORDER:
        # longest keywords first so 'dental clinic' beats 'clinic', 'real estate
        # developer' beats generic terms
        for kw in sorted(keywords, key=len, reverse=True):
            if re.search(r"\b" + re.escape(kw), c):
                return tier, kw, 0.9
    return "Mid", "", 0.4  # unknown category → conservative Mid, low confidence


def _signal_override(tier: str, employees: Optional[int], revenue: Optional[float],
                     review_count: Optional[int]) -> tuple:
    """Hard signals (headcount/revenue/reviews) refine the keyword tier."""
    bumped = tier
    conf = 0.0
    if employees is not None:
        conf = 0.95
        bumped = "High" if employees >= 200 else ("Mid" if employees >= 10 else "Low")
    elif revenue is not None:
        conf = 0.9
        bumped = "High" if revenue >= 10_000_000 else ("Mid" if revenue >= 1_000_000 else "Low")
    elif review_count is not None and review_count >= 1000:
        # very high review volume implies scale → nudge up one tier
        conf = 0.6
        bumped = {"Low": "Mid", "Mid": "High"}.get(tier, tier)
    return bumped, conf


def segment(category: str, *, employees: Optional[int] = None,
            revenue: Optional[float] = None, review_count: Optional[int] = None) -> TicketProfile:
    """Classify a target business category into a full ticket profile."""
    tier, matched, base_conf = _match_tier(category)
    override_tier, override_conf = _signal_override(tier, employees, revenue, review_count)
    if override_conf:
        tier = override_tier
        confidence = max(base_conf, override_conf)
    else:
        confidence = base_conf

    tpl = _SEGMENTS[tier]
    return TicketProfile(
        ticket=tier, matched_category=matched, confidence=round(confidence, 3),
        **tpl,
    )


def enrich_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Attach a ticket profile to a lead record's metadata (additive, fail-soft).
    Uses category + any enrichment/review signals already present."""
    try:
        md = record.setdefault("metadata", {})
        category = md.get("target_category") or md.get("category") or record.get("title", "")
        enr = md.get("enrichment") or {}
        rc = md.get("review_count") or enr.get("review_count")
        rc = int(rc) if str(rc).isdigit() else None
        emp = md.get("employees")
        emp = int(emp) if isinstance(emp, (int, float)) or str(emp).isdigit() else None
        profile = segment(category, employees=emp, review_count=rc)
        md["ticket_profile"] = profile.as_dict()
        md["ticket"] = profile.ticket
    except Exception as exc:
        logger.warning("ticket_segmentation: enrich failed: %s", exc)
    return record

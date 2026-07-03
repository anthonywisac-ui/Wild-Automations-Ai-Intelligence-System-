"""
Lead Explanation Composer — deterministic, evidence-backed sales narrative.

Turns the outputs of the existing frozen modules (Qualification Engine, Ticket
Segmentation, Evidence Graph, Enrichment) into the answer set every lead must
carry before it enters the CRM. No "Standard Lead" / "Website Found" filler —
every statement is backed by a concrete signal.

    explain(record) -> {
        who_are_they, why_buyer, evidence[], confidence,
        spend_crawl, spend_llm, what_to_sell, why_sell,
        who_to_contact, outreach_channel, expected_close_probability
    }

Deterministic; no LLM required (LLM only personalizes wording downstream).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# expected close probability by decision band × ticket (deterministic priors,
# later calibrated by the Learning Engine from real outcomes)
_CLOSE_PRIOR = {
    "FULL_ENRICHMENT":     {"High": 0.28, "Mid": 0.42, "Low": 0.55},
    "STANDARD_ENRICHMENT": {"High": 0.20, "Mid": 0.34, "Low": 0.46},
    "MINIMAL_ENRICHMENT":  {"High": 0.12, "Mid": 0.22, "Low": 0.30},
}


def _dims(record: Dict[str, Any]) -> Dict[str, Any]:
    return ((record.get("metadata") or {}).get("qualification") or {}).get("dimensions") or {}


def _why_buyer(record: Dict[str, Any]) -> List[str]:
    """Concrete reasons this is a buyer, pulled from qualification evidence."""
    dims = _dims(record)
    reasons: List[str] = []
    for key in ("service", "buyer", "geographic", "commercial"):
        d = dims.get(key) or {}
        for ev in (d.get("evidence") or [])[:2]:
            reasons.append(ev)
    return list(dict.fromkeys(reasons))[:6]


def _opportunity_evidence(record: Dict[str, Any]) -> List[str]:
    """What's wrong / missing that we can sell against (real signals only)."""
    md = record.get("metadata") or {}
    enr = md.get("enrichment") or {}
    ev: List[str] = []
    if md.get("rating") is not None and float(md.get("rating") or 5) < 4.0:
        ev.append(f"low rating {md.get('rating')}★")
    if not md.get("website") and not enr.get("website"):
        ev.append("no website detected")
    if enr:
        if not enr.get("socials", {}).get("instagram"):
            ev.append("no active Instagram")
        tech = enr.get("tech") or {}
        if not tech.get("meta_pixel"):
            ev.append("no Meta Pixel")
        if not enr.get("booking_system"):
            ev.append("no booking system")
        if not enr.get("chatbot"):
            ev.append("no chatbot")
        if enr.get("hiring"):
            ev.append("actively hiring")
    dims = _dims(record)
    for ev_item in ((dims.get("marketing") or {}).get("evidence") or []):
        if "indicator" in ev_item:
            ev.append(ev_item.replace("indicator: ", ""))
    return list(dict.fromkeys(ev))[:6]


def _what_to_sell(record: Dict[str, Any], opp: List[str]):
    """Deterministic offer suggestion from the strongest gap, WITH the basis
    (which detected gap triggered which rule) so the recommendation is auditable.
    Returns (offer, basis)."""
    joined = " ".join(opp).lower()
    if "no website" in joined:
        return ("Website build + local SEO foundation",
                "no website detected on the crawl → they have no owned funnel to convert traffic")
    if "meta pixel" in joined or "instagram" in joined:
        trig = [g for g in opp if "meta pixel" in g.lower() or "instagram" in g.lower()]
        return ("Paid social + tracking setup (Meta Pixel + retargeting)",
                f"gaps {trig} → can't run or measure paid social without a pixel / active social presence")
    if "booking" in joined or "chatbot" in joined:
        trig = [g for g in opp if "booking" in g.lower() or "chatbot" in g.lower()]
        return ("Lead-capture funnel (booking + WhatsApp automation)",
                f"gaps {trig} → enquiries are arriving but there's no capture/booking path, so leads leak")
    if "low rating" in joined or "reviews" in joined:
        return ("Reputation management + review-generation campaign",
                "low rating / weak review volume → trust is the bottleneck before demand-gen")
    if "hiring" in joined:
        return ("Recruitment marketing campaign",
                "active hiring signal → they're growing and have budget for growth marketing")
    return ("Social media management + lead-generation retainer",
            "no specific gap surfaced pre/at this enrichment depth → default growth retainer")


def explain(record: Dict[str, Any]) -> Dict[str, Any]:
    """Compose the full evidence-backed answer set for one lead."""
    md = record.get("metadata") or {}
    q = md.get("qualification") or {}
    decision = q.get("decision", "")
    ticket = md.get("ticket") or (md.get("ticket_profile") or {}).get("ticket") or "Mid"
    profile = md.get("ticket_profile") or {}

    name = record.get("title") or md.get("name") or "Unknown business"
    category = md.get("category") or ""
    location = md.get("location") or ""

    why_buyer = _why_buyer(record)
    opp = _opportunity_evidence(record)
    confidence = float(q.get("overall", 0)) / 100.0

    # spend gating mirrors the qualification decision (never spend on rejects)
    spend_crawl = decision in ("FULL_ENRICHMENT", "STANDARD_ENRICHMENT")
    spend_llm = decision == "FULL_ENRICHMENT"

    what, what_basis = _what_to_sell(record, opp)
    close = _CLOSE_PRIOR.get(decision, {}).get(ticket, 0.15)
    # confidence nudges the prior slightly
    close = round(min(0.9, close * (0.7 + 0.6 * confidence)), 2)

    who_to_contact = profile.get("decision_maker", "Owner / Manager")
    channel = "Phone" if md.get("phone") else ("WhatsApp" if md.get("whatsapp") else "Email")

    who = f"{name} — a {ticket.lower()}-ticket {category or 'business'}" + (f" in {location}" if location else "")
    why_sell = (f"Gaps found: {', '.join(opp)}." if opp
                else "Fits target profile; discovery-stage opportunity pending enrichment.")

    return {
        "who_are_they": who,
        "why_buyer": why_buyer or ["fits target industry profile"],
        "evidence": opp,
        "confidence": round(confidence, 3),
        "spend_crawl": spend_crawl,
        "spend_llm": spend_llm,
        "what_to_sell": what,
        "recommendation_basis": what_basis,
        "analysis_basis": (
            f"Qualified as a buyer because: {'; '.join(why_buyer) if why_buyer else 'fits target industry'}. "
            f"Offer chosen because: {what_basis}. "
            f"Confidence {round(confidence,2)} from qualification score {q.get('overall',0)}; "
            f"enrichment depth: {decision}."),
        "why_sell": why_sell,
        "who_to_contact": who_to_contact,
        "outreach_channel": channel,
        "expected_close_probability": close,
        "ticket": ticket,
        "decision": decision,
    }


def is_quality(explanation: Dict[str, Any]) -> bool:
    """A production-quality explanation: non-empty who, ≥1 buyer reason, a concrete
    offer, a real contact channel, and no filler placeholders."""
    if not explanation:
        return False
    banned = {"standard lead", "phone available", "website found", "n/a", ""}
    if (explanation.get("who_are_they") or "").strip().lower() in banned:
        return False
    if not explanation.get("why_buyer"):
        return False
    if (explanation.get("what_to_sell") or "").strip().lower() in banned:
        return False
    if not explanation.get("outreach_channel"):
        return False
    return True

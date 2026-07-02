"""
Recommendation Engine — Wave 4. The decision engine.

Consumes the Evidence Graph (never rebuilds it) plus the resolved entity, search
intent, persona and campaign, and decides — deterministically — the best service,
offer, outreach channel, contact order, follow-up strategy, next best action and
an estimated conversion probability. The LLM is used ONLY to personalize the
pitch wording, never to make the decision.

    recommend(record) -> Recommendation           (deterministic)
    async personalize(record, rec) -> None         (LLM pitch polish, optional)

Sub-capabilities (all rule-based): OfferMatcher, OutreachPlanner, ContactStrategy,
PitchGenerator, NextBestAction. Framework-agnostic.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from core.domain import EvidenceType, Recommendation

logger = logging.getLogger(__name__)

# ── OfferMatcher: evidence type → (service, offer). Ordered by decisiveness. ──
_OFFER_RULES: List[Tuple[EvidenceType, str, str]] = [
    (EvidenceType.INTENT, "Direct Service Match",
     "the exact service they are actively searching for"),
    (EvidenceType.RECOMMENDATION, "Direct Service Match",
     "the service they publicly asked for a recommendation on"),
    (EvidenceType.COMPLAINT, "AI Reception & Response Automation",
     "an AI receptionist to end missed calls and slow replies"),
    (EvidenceType.POOR_REVIEWS, "Reputation & Review Recovery",
     "automated review response + service-recovery workflows"),
    (EvidenceType.WEBSITE_MISSING_FEATURES, "Website + Online Booking",
     "a website with WhatsApp booking and lead capture"),
    (EvidenceType.HIRING, "Recruitment Automation",
     "AI candidate screening + onboarding automation"),
    (EvidenceType.EXPANSION, "Multi-Branch Operations Suite",
     "centralized automation for their new locations"),
    (EvidenceType.FUNDING, "Growth Automation Suite",
     "sales + marketing automation to deploy their new capital"),
    (EvidenceType.SOCIAL_ACTIVITY, "Social DM Automation",
     "an Instagram/Facebook DM auto-responder that captures leads"),
    (EvidenceType.TECHNOLOGY_STACK, "Integration & Workflow Automation",
     "automation that plugs into their existing stack"),
]
_RULE_INDEX = {t: (svc, off) for t, svc, off in _OFFER_RULES}

# ── Channel priority (ContactStrategy) ───────────────────────────────────────
_CHANNEL_PRIORITY = ["Call", "WhatsApp", "DM", "Email", "Web form"]


def _evidence_nodes(md: Dict[str, Any]) -> List[Dict[str, Any]]:
    return md.get("evidence") or []


def _offer_weight(service: str) -> float:
    """Adaptive offer ranking — learned conversion multiplier (neutral 1.0)."""
    try:
        from core import learning_engine
        return learning_engine.weight("offer", service)
    except Exception:
        return 1.0


def _offer_match(nodes: List[Dict[str, Any]], service_hint: str) -> Tuple[str, str, List[str], str]:
    """Pick the most decisive evidence node → (service, offer, driving_evidence, reason).
    Ranking is adaptive: evidence strength × learned offer conversion weight."""
    best = None
    best_score = -1.0
    for n in nodes:
        try:
            etype = EvidenceType(n.get("type"))
        except (ValueError, KeyError):
            continue
        if etype not in _RULE_INDEX:
            continue
        service, _ = _RULE_INDEX[etype]
        score = float(n.get("value", 0)) * float(n.get("weight", 0)) * _offer_weight(service)
        if score > best_score:
            best_score, best = score, (etype, n)
    if best is None:
        return ("General Automation Consultation",
                "an operational automation audit", [], "no decisive evidence — default audit")
    etype, node = best
    service, offer = _RULE_INDEX[etype]
    if etype in (EvidenceType.INTENT, EvidenceType.RECOMMENDATION) and service_hint:
        offer = f"{service_hint} — {offer}"
    return service, offer, [etype.value], f"driven by {etype.value} ({node.get('detail','')})"


def _contact_strategy(md: Dict[str, Any]) -> Tuple[List[str], str]:
    """Available channels in priority order + the primary channel."""
    text = f"{md.get('post_text','')} {md.get('company','')}".lower()
    platform = (md.get("platform") or "").lower()
    has_phone = bool(md.get("phone")) or bool(re.search(r"\+?\d[\d\s().\-]{7,}\d", text))
    has_web = bool(md.get("website")) or any(k in text for k in (".com", "www.", "http"))
    available = []
    if has_phone:
        available += ["Call", "WhatsApp"]
    if platform in ("instagram", "facebook") or md.get("followers"):
        available.append("DM")
    if md.get("email") or has_web:
        available.append("Email")
    if has_web:
        available.append("Web form")
    ordered = [c for c in _CHANNEL_PRIORITY if c in available] or ["Email"]
    return ordered, ordered[0]


def _priority_and_conversion(md: Dict[str, Any], nodes: List[Dict[str, Any]],
                             contactable: bool) -> Tuple[str, float]:
    intent = (md.get("intent") or "").lower() == "interested"
    ev_strength = float(md.get("evidence_strength") or 0.0)
    final_conf = float(md.get("final_confidence") or 0.5)
    has_phone = "Call" in _contact_strategy(md)[0]

    if intent and contactable:
        priority = "Hot"
    elif ev_strength >= 0.4 and contactable:
        priority = "High"
    elif ev_strength >= 0.3 or contactable:
        priority = "Medium"
    else:
        priority = "Low"

    # deterministic conversion estimate, scaled by confidence
    p = 0.10
    if intent:
        p += 0.30
    p += min(0.30, ev_strength * 0.4)
    p += 0.20 if has_phone else (0.10 if contactable else 0.0)
    p = min(1.0, p) * (0.5 + 0.5 * final_conf)
    return priority, round(min(1.0, p), 3)


def _pitch(name: str, offer: str, nodes: List[Dict[str, Any]]) -> str:
    pains = [n.get("detail", "") for n in nodes
             if n.get("type") in ("complaint", "poor_reviews", "website_missing_features")]
    hook = f" We noticed {pains[0]}." if pains and pains[0] else ""
    who = name or "your team"
    return f"Hi {who} — we help businesses like yours with {offer}.{hook}".strip()


def _followup(priority: str) -> str:
    return {
        "Hot": "Call same day; if no answer, WhatsApp within 2h, then follow up on day 2 and day 4.",
        "High": "Call within 24h; email a case study; follow up in 3 days.",
        "Medium": "WhatsApp/email intro; follow up in 5 days.",
        "Low": "Add to nurture list; light-touch email in 1-2 weeks.",
    }.get(priority, "Add to nurture list.")


def recommend(record: Dict[str, Any]) -> Recommendation:
    """Deterministic decision from the evidence graph + entity + intent."""
    md = record.get("metadata") or {}
    nodes = _evidence_nodes(md)
    name = md.get("company") or record.get("title") or ""
    service_hint = md.get("_query") or ""    # search intent → what they want

    service, offer, driving, reason = _offer_match(nodes, service_hint)
    contact_order, channel = _contact_strategy(md)
    contactable = channel != "Email" or bool(md.get("email"))
    priority, conversion = _priority_and_conversion(md, nodes, contactable)
    pitch = _pitch(name, offer, nodes)
    action = f"{contact_order[0]} {name or 'the lead'} — pitch: {service}"

    return Recommendation(
        canonical_id=md.get("canonical_id", ""),
        recommended_service=service,
        reason=reason,
        evidence=driving + [n.get("type") for n in nodes if n.get("type") not in driving][:4],
        priority=priority,
        confidence=float(md.get("final_confidence") or 0.0),
        recommended_offer=offer,
        recommended_pitch=pitch,
        outreach_channel=channel,
        contact_order=contact_order,
        followup_strategy=_followup(priority),
        next_best_action=action,
        conversion_probability=conversion,
    )


async def personalize(record: Dict[str, Any], rec: Recommendation) -> None:
    """LLM personalizes the PITCH wording only (decision stays deterministic)."""
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return
        md = record.get("metadata") or {}
        ev = ", ".join(n.get("type", "") for n in _evidence_nodes(md)[:4])
        prompt = (
            f"Rewrite this cold-outreach opener in ONE friendly, specific sentence (max 22 words) "
            f"for '{md.get('company') or record.get('title','')}'. Offer: {rec.recommended_offer}. "
            f"Signals: {ev}. Draft: {rec.recommended_pitch}. Return only the sentence."
        )
        text = (await llm.complete(prompt, max_tokens=60, temperature=0.5)).strip().strip('"')
        if text:
            rec.recommended_pitch = text
    except Exception as exc:
        logger.warning("recommendation_engine: personalize skipped: %s", exc)

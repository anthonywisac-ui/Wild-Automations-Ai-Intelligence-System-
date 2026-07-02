"""
Evidence Graph — Wave 3 first-class explainability.

Extracts structured, typed evidence nodes from a record (deterministic
detectors over existing scraped signals) so that every score is explainable
through evidence instead of hidden calculations.

    build(rec, resolved) -> List[EvidenceNode]
    strength(nodes)      -> float in [0,1]     (aggregate evidence strength)
    dynamic_confidence(entity_conf, source_rel, evidence_strength, completeness)

Framework-agnostic; no LLM required (uses signals already on the record).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from core.domain import EntityType, EvidenceNode, EvidenceType, ResolvedEntity

logger = logging.getLogger(__name__)

_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().\-]{7,}\d)")
_URL_RE = re.compile(r"(https?://|www\.|\.com|\.ae|\.io|\.co\b|\.net)", re.I)
_TECH_TERMS = ("react", "wordpress", "shopify", "hubspot", "salesforce", "python",
               "aws", "node", "kubernetes", "ai", "chatbot", "crm", "api")
_EXPANSION = ("new branch", "opening", "expansion", "expanding", "now open",
              "new location", "franchise")
_FUNDING = ("funding", "raised", "series a", "series b", "seed round", "investment",
            "backed by", "valuation")
_HIRING = ("hiring", "we're hiring", "we are hiring", "join our team", "now hiring",
           "vacancy", "recruiting")
_RECO = ("recommend", "looking for", "need a", "anyone know", "suggestions for")

# per-type base weight (contribution to opportunity score)
_WEIGHTS = {
    EvidenceType.INTENT: 0.30,
    EvidenceType.COMPLAINT: 0.25,
    EvidenceType.POOR_REVIEWS: 0.22,
    EvidenceType.HIRING: 0.20,
    EvidenceType.FUNDING: 0.20,
    EvidenceType.EXPANSION: 0.18,
    EvidenceType.RECOMMENDATION: 0.20,
    EvidenceType.CONTACTABILITY: 0.18,
    EvidenceType.WEBSITE_MISSING_FEATURES: 0.15,
    EvidenceType.SOCIAL_ACTIVITY: 0.12,
    EvidenceType.DEADLINE: 0.15,
    EvidenceType.HIGH_RATINGS: 0.08,
    EvidenceType.GOVERNMENT_DATA: 0.10,
    EvidenceType.NEWS: 0.10,
    EvidenceType.COMMUNITY_DISCUSSION: 0.12,
    EvidenceType.TECHNOLOGY_STACK: 0.10,
}


def _node(t: EvidenceType, value: float, detail: str, source: str,
          rel: float, polarity: int = 1, confidence: float = None) -> EvidenceNode:
    return EvidenceNode(type=t, value=round(max(0.0, min(1.0, value)), 3),
                        weight=_WEIGHTS.get(t, 0.1), polarity=polarity,
                        detail=detail, source=source, source_reliability=rel,
                        confidence=(rel if confidence is None else round(confidence, 3)))


def build(rec: Dict[str, Any], resolved: ResolvedEntity) -> List[EvidenceNode]:
    """Deterministically extract typed evidence nodes from a record."""
    md = rec.get("metadata") or {}
    text = f"{rec.get('title','')} {rec.get('description','')} {md.get('post_text','')}".lower()
    src = md.get("source", "")
    rel = resolved.source_reliability
    nodes: List[EvidenceNode] = []

    # Ratings / reviews
    rating = md.get("rating")
    reviews = md.get("review_count") or 0
    if rating is not None:
        try:
            rf = float(rating)
            if rf <= 3.8:
                nodes.append(_node(EvidenceType.POOR_REVIEWS, (4.2 - rf) / 1.4,
                                   f"{rf}★ with {reviews} reviews", src, rel))
            elif rf >= 4.5:
                nodes.append(_node(EvidenceType.HIGH_RATINGS, (rf - 4.5) / 0.5,
                                   f"{rf}★ trusted", src, rel))
        except (ValueError, TypeError):
            pass

    # Complaint / pain (from review miner)
    frictions = md.get("likely_friction") or []
    if frictions:
        nodes.append(_node(EvidenceType.COMPLAINT, min(1.0, 0.4 + 0.2 * len(frictions)),
                           f"friction: {', '.join(frictions[:3])}", src, rel))

    # Buying intent
    if (md.get("intent") or "").lower() == "interested":
        nodes.append(_node(EvidenceType.INTENT, 1.0, "GROQ: interested", src, rel))
    elif any(k in text for k in _RECO):
        nodes.append(_node(EvidenceType.RECOMMENDATION, 0.7, "asking for recommendation", src, rel))

    # Hiring / expansion / funding (growth signals)
    if any(k in text for k in _HIRING) or resolved.entity_type in (EntityType.SPONSOR, EntityType.JOB):
        nodes.append(_node(EvidenceType.HIRING, 0.8, "hiring signal", src, rel))
    if any(k in text for k in _EXPANSION):
        nodes.append(_node(EvidenceType.EXPANSION, 0.8, "expansion signal", src, rel))
    if any(k in text for k in _FUNDING):
        nodes.append(_node(EvidenceType.FUNDING, 0.85, "funding signal", src, rel))

    # Contactability
    has_phone = bool(md.get("phone")) or bool(_PHONE_RE.search(text))
    has_web = bool(_URL_RE.search(text)) or bool(md.get("website"))
    if has_phone or has_web:
        nodes.append(_node(EvidenceType.CONTACTABILITY, 0.5 * has_phone + 0.5 * has_web,
                           f"{'phone ' if has_phone else ''}{'website' if has_web else ''}".strip(),
                           src, rel))
    elif resolved.entity_type == EntityType.BUSINESS:
        nodes.append(_node(EvidenceType.WEBSITE_MISSING_FEATURES, 0.6,
                           "no website/contact detected → automation opportunity", src, rel))

    # Social activity
    followers = md.get("followers")
    if md.get("platform") in ("instagram", "facebook") or followers:
        nodes.append(_node(EvidenceType.SOCIAL_ACTIVITY, 0.5,
                           f"active on {md.get('platform','social')}", src, rel))

    # Source-class evidence
    if any(k in src.lower() for k in ("gov", "nhtsa", "data.gov", "ircc", "state.gov")):
        nodes.append(_node(EvidenceType.GOVERNMENT_DATA, 0.6, "official government source", src, rel))
    if any(k in src.lower() for k in ("news", "rss", "pie", "icef")):
        nodes.append(_node(EvidenceType.NEWS, 0.5, "news/RSS source", src, rel))
    if any(k in src.lower() for k in ("reddit", "quora")):
        nodes.append(_node(EvidenceType.COMMUNITY_DISCUSSION, 0.6, "community discussion", src, rel))

    # Technology stack
    techs = [t for t in _TECH_TERMS if t in text]
    if techs:
        nodes.append(_node(EvidenceType.TECHNOLOGY_STACK, min(1.0, 0.3 + 0.15 * len(techs)),
                           f"tech: {', '.join(techs[:4])}", src, rel))

    # Deadline / time-sensitivity
    if md.get("academic_flags", {}).get("is_late_intake") or md.get("deadline_days_left") is not None:
        nodes.append(_node(EvidenceType.DEADLINE, 0.7, "time-sensitive window", src, rel))

    # ── Enrichment-derived evidence (real data + per-signal provenance) ──
    enr = md.get("enrichment")
    if isinstance(enr, dict):
        prov = enr.get("provenance") or {}

        def _pv(sig, default_src=src, default_conf=None):
            p = prov.get(sig) or {}
            return p.get("source") or default_src, p.get("confidence", default_conf)

        has_phone_e = bool(enr.get("phone"))
        has_wa = bool(enr.get("whatsapp"))
        has_email = bool(enr.get("email"))
        contact = 0.5 * has_phone_e + 0.3 * has_wa + 0.2 * has_email
        if contact > 0:
            channels = [c for c, ok in (("phone", has_phone_e), ("whatsapp", has_wa),
                                        ("email", has_email)) if ok]
            csrc, cconf = _pv("phone" if has_phone_e else ("whatsapp" if has_wa else "email"))
            nodes.append(_node(EvidenceType.CONTACTABILITY, contact,
                               "reachable via " + ", ".join(channels), csrc, rel, confidence=cconf))
        pains = enr.get("pain_signals") or []
        if pains:
            nodes.append(_node(EvidenceType.WEBSITE_MISSING_FEATURES,
                               min(1.0, 0.3 + 0.15 * len(pains)),
                               "gaps: " + ", ".join(pains[:4]), "website_html", rel, confidence=0.9))
        tech = enr.get("tech") or {}
        detected = [k for k in ("cms",) if tech.get(k)] + \
                   [k for k in ("meta_pixel", "google_analytics", "gtm") if tech.get(k)]
        if detected:
            nodes.append(_node(EvidenceType.TECHNOLOGY_STACK, min(1.0, 0.3 + 0.15 * len(detected)),
                               "detected: " + ", ".join(str(tech.get('cms') or d) for d in detected[:4]),
                               "html", rel, confidence=1.0))
        socials = enr.get("socials") or {}
        if socials:
            ssrc, sconf = _pv(f"social_{next(iter(socials))}")
            nodes.append(_node(EvidenceType.SOCIAL_ACTIVITY, min(1.0, 0.4 + 0.15 * len(socials)),
                               "profiles: " + ", ".join(socials.keys()), ssrc, rel, confidence=sconf))
        if enr.get("hiring"):
            hsrc, hconf = _pv("hiring")
            nodes.append(_node(EvidenceType.HIRING, 0.75, "careers/hiring on website",
                               hsrc, rel, confidence=hconf))

    # de-duplicate by type, keeping the strongest node of each kind
    best: Dict[Any, EvidenceNode] = {}
    for n in nodes:
        cur = best.get(n.type)
        if cur is None or n.value > cur.value:
            best[n.type] = n
    return list(best.values())


def strength(nodes: List[EvidenceNode]) -> float:
    """Aggregate evidence strength in [0,1] — weighted, reliability-scaled."""
    if not nodes:
        return 0.0
    total = sum(n.value * n.weight * n.source_reliability for n in nodes)
    # normalize against a saturating scale (≈3 strong nodes → ~1.0)
    return round(min(1.0, total / 0.6), 3)


# Confidence component weights — evidence weighted highest so weak evidence
# meaningfully penalizes the result (per architecture review).
_CONF_WEIGHTS = {"entity_confidence": 1.0, "source_reliability": 1.0,
                 "evidence_strength": 1.5, "data_completeness": 1.0}
_CONF_FLOOR = 0.05


def confidence_components(entity_conf: float, source_rel: float,
                         evidence_strength: float, completeness: float) -> Dict[str, float]:
    """The four confidence inputs, kept visible (never hidden)."""
    def c(x: float) -> float:
        return round(max(0.0, min(1.0, float(x))), 3)
    return {
        "entity_confidence": c(entity_conf),
        "source_reliability": c(source_rel),
        "evidence_strength": c(evidence_strength),
        "data_completeness": c(completeness),
    }


def dynamic_confidence(entity_conf: float, source_rel: float,
                       evidence_strength: float, completeness: float) -> float:
    """Weighted GEOMETRIC MEAN of the four components — interpretable on 0-1 while
    still penalizing weak evidence (a single low component drags the result down,
    but not to near-zero like a raw product)."""
    import math
    comps = confidence_components(entity_conf, source_rel, evidence_strength, completeness)
    num = 0.0
    den = 0.0
    for key, weight in _CONF_WEIGHTS.items():
        x = max(_CONF_FLOOR, comps[key])
        num += weight * math.log(x)
        den += weight
    return round(math.exp(num / den), 3) if den else 0.0

"""
Qualification Engine — the system gatekeeper (deterministic, pre-crawl).

Decides whether a discovered business is worth spending expensive enrichment on,
BEFORE any website/social crawl runs. It is not the Search Planner (what to
search) and not the Recommendation Engine (what to pitch) — it answers: is this
worth enriching, and how deeply.

Hierarchical, never a single blended number. Nine independent dimensions are
computed first, each producing {score, confidence, evidence, explanation}. Only
then is the Overall Qualification Score derived — so one weak area cannot hide
another.

    Dimensions: buyer · service · business · digital(est) · marketing(est) ·
                commercial · geographic · contact · risk

Service-specific rules come from config (data/qualification_profiles.json), so
the same engine works for any niche without code changes.

Decision bands (per profile thresholds):
    >= full      -> FULL_ENRICHMENT
    >= standard  -> STANDARD_ENRICHMENT
    >= minimal   -> MINIMAL_ENRICHMENT
    <  reject    -> REJECT   (persisted with structured reasons)
    <  blacklist -> BLACKLIST

Uses only pre-crawl signals (category, location, rating, review_count, website/
phone presence flags, post text). No network, no LLM.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core import ticket_segmentation

logger = logging.getLogger(__name__)

_PROFILES_PATH = Path(__file__).resolve().parent.parent / "data" / "qualification_profiles.json"

# Structured rejection reason codes (surfaced in the CRM).
REJECT_COMPETITOR = "COMPETITOR"
REJECT_OUT_OF_AREA = "OUT_OF_AREA"
REJECT_WRONG_INDUSTRY = "WRONG_INDUSTRY"
REJECT_TOO_SMALL = "TOO_SMALL"
REJECT_NO_BUYING_SIGNALS = "NO_BUYING_SIGNALS"
REJECT_DUPLICATE = "DUPLICATE"
REJECT_MARKETPLACE = "MARKETPLACE"
REJECT_GOVERNMENT = "GOVERNMENT"
REJECT_DIRECTORY = "DIRECTORY"
REJECT_SOFTWARE_VENDOR = "SOFTWARE_VENDOR"

# Non-buyer entity detectors (deterministic keyword sets).
_MARKETPLACE = ("marketplace", "classifieds", "olx", "dubizzle", "amazon", "ebay",
                "etsy", "aggregator", "listing platform")
_DIRECTORY = ("directory", "yellow pages", "yellowpages", "yelp", "tripadvisor",
              "justdial", "listing site", "review site", "wikipedia")
_GOVERNMENT = ("ministry", "gov.", ".gov", "municipality", "authority", "council",
               "department of", "embassy", "consulate")
_SOFTWARE = ("software", "saas", "app development", "crm software", "platform inc",
             "technologies", "systems inc", "it solutions")
_COMPETITOR_TERMS = ("marketing agency", "seo agency", "digital agency",
                     "advertising agency", "social media agency", "branding agency",
                     "web design agency", "pr agency", "ad agency", "smma",
                     "consultant", "consultancy", "freelancer")

DECISION_FULL = "FULL_ENRICHMENT"
DECISION_STANDARD = "STANDARD_ENRICHMENT"
DECISION_MINIMAL = "MINIMAL_ENRICHMENT"
DECISION_REJECT = "REJECT"
DECISION_BLACKLIST = "BLACKLIST"

# decision -> enrichment depth the pipeline honors
DECISION_DEPTH = {
    DECISION_FULL: "full",
    DECISION_STANDARD: "standard",
    DECISION_MINIMAL: "minimal",
    DECISION_REJECT: "none",
    DECISION_BLACKLIST: "none",
}


@dataclass
class Dimension:
    """One qualification dimension — independent, evidence-backed."""
    name: str
    score: float = 0.0            # 0..100
    confidence: float = 0.0       # 0..1
    evidence: List[str] = field(default_factory=list)
    explanation: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualificationResult:
    qualified: bool
    overall: float                       # 0..100
    decision: str                        # DECISION_*
    depth: str                           # full|standard|minimal|none
    dimensions: Dict[str, Dict[str, Any]]
    rejection_reasons: List[str] = field(default_factory=list)
    service: str = ""
    profile_used: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Config loading (cached, fail-soft) ────────────────────────────────────────
_PROFILES_CACHE: Optional[Dict[str, Any]] = None


def _load_profiles() -> Dict[str, Any]:
    global _PROFILES_CACHE
    if _PROFILES_CACHE is None:
        try:
            _PROFILES_CACHE = json.loads(_PROFILES_PATH.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            logger.warning("qualification: profiles load failed: %s", exc)
            _PROFILES_CACHE = {}
    return _PROFILES_CACHE


def reload_profiles() -> None:
    """Drop the cache so config edits take effect without a restart."""
    global _PROFILES_CACHE
    _PROFILES_CACHE = None


def resolve_profile(service: str) -> Tuple[str, Dict[str, Any]]:
    """Pick the profile for a service (substring match), fall back to 'default'."""
    profiles = _load_profiles()
    s = (service or "").lower().strip()
    if s:
        for name, prof in profiles.items():
            if name.startswith("_"):
                continue
            if name.replace("_", " ") in s or s in name.replace("_", " "):
                return name, prof
    return "default", profiles.get("default", {})


# ── Pre-crawl feature extraction ──────────────────────────────────────────────
def _features(record: Dict[str, Any]) -> Dict[str, Any]:
    md = record.get("metadata") or {}
    text = " ".join(str(x) for x in (
        record.get("title", ""), record.get("description", ""),
        md.get("category", ""), md.get("post_text", ""))).lower()
    rating = md.get("rating")
    try:
        rating = float(rating) if rating is not None else None
    except (ValueError, TypeError):
        rating = None
    rc = md.get("review_count")
    try:
        rc = int(rc) if rc is not None else None
    except (ValueError, TypeError):
        rc = None
    return {
        "text": text,
        "category": (md.get("category") or record.get("title", "") or "").lower(),
        "location": (md.get("location") or "").lower(),
        "rating": rating,
        "review_count": rc,
        "has_website": bool(md.get("website")),
        "has_phone": bool(md.get("phone")),
        "has_email": bool(md.get("email")),
        "is_duplicate": bool(md.get("_duplicate")),
        "employees": md.get("employees"),
    }


def _clamp100(x: float) -> float:
    return max(0.0, min(100.0, x))


# ── The nine dimensions (each independent, evidence-backed) ────────────────────
def _dim_service(f, prof) -> Dimension:
    """Does this business's industry match what the service sells INTO?"""
    cat = f["category"] or f["text"]
    targets = [t.lower() for t in prof.get("target_industries", [])]
    excluded = [e.lower() for e in prof.get("excluded_industries", [])]
    ev: List[str] = []
    hit = next((t for t in sorted(targets, key=len, reverse=True) if t in cat), None)
    bad = next((e for e in sorted(excluded, key=len, reverse=True) if e in cat), None)
    if bad:
        ev.append(f"matches excluded industry '{bad}'")
        return Dimension("service", 5, 0.9, ev, f"Excluded industry: {bad}")
    if hit:
        ev.append(f"target industry '{hit}'")
        return Dimension("service", 95, 0.9, ev, f"Perfect service fit: {hit}")
    if not targets:
        return Dimension("service", 55, 0.4, ["no target list (default profile)"],
                         "Neutral: no target industries configured")
    return Dimension("service", 35, 0.5, ["industry not in target list"],
                     "Industry not in target list")


def _dim_buyer(f, prof, service_dim) -> Dimension:
    """Buyer probability: is this a buyer, not a competitor/seller?"""
    text = f["text"]
    ev: List[str] = []
    comp = next((c for c in _COMPETITOR_TERMS if c in text), None)
    if comp:
        ev.append(f"competitor/seller term '{comp}'")
        return Dimension("buyer", 5, 0.95, ev, f"Competitor signal: {comp}")
    score = 40.0 + 0.5 * service_dim.score * 0.5   # inherits service fit
    if service_dim.score >= 90:
        score = 92
        ev.append("industry matches, no competitor signals")
    elif service_dim.score >= 50:
        score = 70
        ev.append("plausible buyer industry")
    else:
        score = 45
        ev.append("weak buyer fit")
    return Dimension("buyer", _clamp100(score), 0.8, ev,
                     "Industry matches; no competitor signals" if score >= 90
                     else "Buyer-plausible" if score >= 60 else "Weak buyer fit")


def _dim_business(f, prof) -> Dimension:
    """Business maturity from review volume + rating presence + ticket."""
    ev: List[str] = []
    profile = ticket_segmentation.segment(f["category"], review_count=f["review_count"])
    rc = f["review_count"] or 0
    base = 40.0
    if rc >= 500:
        base = 85; ev.append(f"{rc} reviews (established)")
    elif rc >= 100:
        base = 70; ev.append(f"{rc} reviews (active)")
    elif rc >= 20:
        base = 55; ev.append(f"{rc} reviews")
    elif rc > 0:
        base = 45; ev.append(f"{rc} reviews (small footprint)")
    else:
        ev.append("no review signal")
    ev.append(f"ticket {profile.ticket}")
    return Dimension("business", _clamp100(base), 0.6 if rc else 0.3, ev,
                     f"{profile.ticket}-ticket, {profile.maturity.lower()}")


def _dim_digital(f, prof) -> Dimension:
    """ESTIMATED digital maturity (pre-crawl proxy: website presence + rating)."""
    ev: List[str] = []
    if not f["has_website"]:
        ev.append("no website detected in discovery")
        return Dimension("digital", 25, 0.5, ev,
                         "Low digital maturity (no website) — strong opportunity")
    ev.append("website present")
    score = 60.0
    if f["rating"] is not None and f["rating"] < 4.0:
        score = 45; ev.append(f"low rating {f['rating']}")
    return Dimension("digital", _clamp100(score), 0.4, ev,
                     "Has website (depth unknown until crawl)")


def _dim_marketing(f, prof) -> Dimension:
    """ESTIMATED marketing maturity from buying/pain indicators in text."""
    text = f["text"]
    inds = [b for b in prof.get("buying_indicators", []) if b in text]
    ev = [f"indicator: {b}" for b in inds[:5]]
    if inds:
        # more pain indicators => lower current marketing maturity => more opportunity
        score = max(20.0, 60.0 - 8.0 * len(inds))
        return Dimension("marketing", _clamp100(score), 0.5, ev,
                         f"Marketing gaps found ({len(inds)}) — opportunity")
    return Dimension("marketing", 50, 0.25, ["no explicit marketing signals"],
                     "Marketing maturity unknown (no pre-crawl signals)")


def _dim_commercial(f, prof) -> Dimension:
    """Commercial fit: ticket size vs preferred + estimated budget."""
    ev: List[str] = []
    profile = ticket_segmentation.segment(f["category"], review_count=f["review_count"])
    preferred = prof.get("preferred_ticket_size", ["Low", "Mid", "High"])
    if profile.ticket in preferred:
        score = 85 if profile.ticket in ("Mid", "High") else 65
        ev.append(f"{profile.ticket} ticket in preferred range")
        ev.append(f"est. budget {profile.expected_budget}")
    else:
        score = 30
        ev.append(f"{profile.ticket} ticket outside preferred {preferred}")
    return Dimension("commercial", _clamp100(score), 0.6, ev,
                     f"Estimated budget {profile.expected_budget}")


def _dim_geographic(f, prof) -> Dimension:
    """Service-area fit. If no area configured, neutral-positive."""
    area = prof.get("service_area", {}) or {}
    countries = [c.lower() for c in area.get("countries", [])]
    cities = [c.lower() for c in area.get("cities", [])]
    loc = f["location"]
    if not countries and not cities:
        return Dimension("geographic", 70, 0.3, ["no service-area restriction"],
                         "No geographic restriction configured")
    if not loc:
        return Dimension("geographic", 45, 0.2, ["location unknown"], "Location unknown")
    hit = any(c in loc for c in countries + cities)
    if hit:
        return Dimension("geographic", 95, 0.8, [f"in service area: {loc}"], "In service area")
    return Dimension("geographic", 10, 0.8, [f"outside service area: {loc}"], "Outside service area")


def _dim_contact(f, prof) -> Dimension:
    """Reachability from pre-crawl presence flags."""
    ev, pts = [], 0.0
    if f["has_phone"]:
        pts += 50; ev.append("phone present")
    if f["has_website"]:
        pts += 30; ev.append("website present")
    if f["has_email"]:
        pts += 20; ev.append("email present")
    if not ev:
        ev.append("no contact channel yet (may resolve after crawl)")
    return Dimension("contact", _clamp100(pts or 30), 0.5 if pts else 0.2, ev,
                     "Reachable" if pts >= 50 else "Limited contact info pre-crawl")


def _dim_risk(f, prof) -> Tuple[Dimension, List[str]]:
    """Risk (higher = worse). Also returns hard rejection reason codes."""
    text = f["text"]
    cat = f["category"]
    reasons: List[str] = []
    ev: List[str] = []
    risk = 5.0

    def _any(terms):
        return next((t for t in terms if t in text or t in cat), None)

    if _any(_COMPETITOR_TERMS):
        risk = 95; reasons.append(REJECT_COMPETITOR); ev.append(f"competitor: {_any(_COMPETITOR_TERMS)}")
    if _any(_MARKETPLACE):
        risk = max(risk, 90); reasons.append(REJECT_MARKETPLACE); ev.append("marketplace")
    if _any(_DIRECTORY):
        risk = max(risk, 90); reasons.append(REJECT_DIRECTORY); ev.append("directory/review site")
    if _any(_GOVERNMENT):
        risk = max(risk, 85); reasons.append(REJECT_GOVERNMENT); ev.append("government entity")
    if _any(_SOFTWARE):
        risk = max(risk, 80); reasons.append(REJECT_SOFTWARE_VENDOR); ev.append("software vendor")
    # config-driven rejection indicators
    for ind in prof.get("rejection_indicators", []):
        if ind.lower() in text or ind.lower() in cat:
            risk = max(risk, 70)
            ev.append(f"rejection indicator: {ind}")
    if f["is_duplicate"]:
        risk = max(risk, 100); reasons.append(REJECT_DUPLICATE); ev.append("duplicate")
    if not ev:
        ev.append("no competitor/marketplace/gov signals")
    expl = "No risk signals" if risk <= 10 else f"Risk signals: {', '.join(sorted(set(reasons))) or 'soft'}"
    return Dimension("risk", _clamp100(risk), 0.9 if reasons else 0.5, ev, expl), reasons


# ── Orchestration ─────────────────────────────────────────────────────────────
def qualify(record: Dict[str, Any], service: str = "") -> QualificationResult:
    """Compute all dimensions, then the overall score + gatekeeper decision."""
    md = record.get("metadata") or {}
    service = service or md.get("_service") or md.get("service") or ""
    profile_name, prof = resolve_profile(service)
    f = _features(record)

    d_service = _dim_service(f, prof)
    d_buyer = _dim_buyer(f, prof, d_service)
    d_business = _dim_business(f, prof)
    d_digital = _dim_digital(f, prof)
    d_marketing = _dim_marketing(f, prof)
    d_commercial = _dim_commercial(f, prof)
    d_geographic = _dim_geographic(f, prof)
    d_contact = _dim_contact(f, prof)
    d_risk, hard_reasons = _dim_risk(f, prof)

    positives = {
        "buyer": d_buyer, "service": d_service, "business": d_business,
        "digital": d_digital, "marketing": d_marketing, "commercial": d_commercial,
        "geographic": d_geographic, "contact": d_contact,
    }
    weights = prof.get("weights", {})
    wsum = sum(weights.get(k, 0.1) for k in positives)
    base = sum(dim.score * weights.get(k, 0.1) for k, dim in positives.items()) / (wsum or 1)

    # risk applies a penalty on top of the positive blend
    risk_penalty = float(prof.get("risk_penalty", 0.6))
    overall = base * (1.0 - (d_risk.score / 100.0) * risk_penalty)

    # soft rejection reasons (not hard-coded gates but recorded)
    thresholds = prof.get("thresholds", {"full": 80, "standard": 60, "minimal": 40,
                                         "reject": 40, "blacklist": 20})
    reasons = list(dict.fromkeys(hard_reasons))  # de-dup, keep order
    if d_service.score < 40 and REJECT_WRONG_INDUSTRY not in reasons and not hard_reasons:
        reasons.append(REJECT_WRONG_INDUSTRY)
    if d_geographic.score < 20:
        reasons.append(REJECT_OUT_OF_AREA)
    if (not hard_reasons and d_business.score < 45 and (f["review_count"] or 0) == 0
            and d_marketing.score >= 50):
        # weak footprint AND no pain signal → no buying signal (only when no
        # stronger hard reason already explains the rejection)
        reasons.append(REJECT_NO_BUYING_SIGNALS)

    # hard reasons force rejection regardless of blend
    if hard_reasons:
        overall = min(overall, thresholds["reject"] - 1)

    overall = round(_clamp100(overall), 1)

    if overall < thresholds["blacklist"]:
        decision = DECISION_BLACKLIST
    elif overall < thresholds["reject"]:
        decision = DECISION_REJECT
    elif overall < thresholds["standard"]:
        decision = DECISION_MINIMAL
    elif overall < thresholds["full"]:
        decision = DECISION_STANDARD
    else:
        decision = DECISION_FULL

    qualified = decision in (DECISION_FULL, DECISION_STANDARD, DECISION_MINIMAL)
    if not qualified and not reasons:
        reasons.append(REJECT_NO_BUYING_SIGNALS)

    return QualificationResult(
        qualified=qualified, overall=overall, decision=decision,
        depth=DECISION_DEPTH[decision],
        dimensions={k: v.as_dict() for k, v in
                    {**positives, "risk": d_risk}.items()},
        rejection_reasons=reasons if not qualified else [],
        service=service, profile_used=profile_name,
    )

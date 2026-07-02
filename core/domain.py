"""
Domain Models — Wave 1 foundation.

Canonical typed schema for every scraped record plus the entity taxonomy the
resolver (Wave 3) will populate. Wave 1 only *tags* entity_type directly from
the existing metadata.type (additive) and attaches source_reliability +
confidence; full buyer/seller/sponsor role resolution is Wave 3.

The `confidence`, `source_reliability`, and `evidence` fields are present from
day one so later waves slot in without schema churn.

This module has no side effects and no external dependencies beyond pydantic.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Full taxonomy. Wave 1 assigns from metadata.type; Wave 3 resolves roles."""
    # Organizations
    BUSINESS = "business"        # buyer — has reviews/pain/contact
    EMPLOYER = "employer"        # seller of jobs
    SPONSOR = "sponsor"          # can sponsor a visa → potential employer (NOT a job)
    COMPANY = "company"          # parent org
    BRANCH = "branch"            # child location of a company
    # People
    PERSON = "person"
    LEAD = "lead"               # buyer-intent person
    CANDIDATE = "candidate"      # job seeker
    # Opportunities
    JOB = "job"                 # real posting
    ADMISSION = "admission"      # program + deadline + funding
    UNIVERSITY = "university"
    VISA = "visa"               # process/route (friction-scored)
    IMMIGRATION_PROGRAM = "immigration_program"  # policy vehicle (Chancenkarte, GTS)
    # References / signals
    PASSPORT = "passport"        # document / mobility index (NOT a visa)
    VEHICLE = "vehicle"
    REVIEW = "review"
    COMPLAINT = "complaint"      # 1-3★ operational pain (buying signal)
    OPPORTUNITY = "opportunity"  # actionable state change
    UNKNOWN = "unknown"


# Existing metadata.type strings → canonical EntityType (additive typing only).
_TYPE_MAP: Dict[str, EntityType] = {
    "job": EntityType.JOB,
    "uk_sponsor": EntityType.SPONSOR,
    "lead": EntityType.LEAD,
    "vehicle": EntityType.VEHICLE,
    "admission": EntityType.ADMISSION,
    "admissions_data": EntityType.ADMISSION,
    "admissions_guide": EntityType.ADMISSION,
    "university": EntityType.UNIVERSITY,
}

_CATEGORY_MAP: Dict[str, EntityType] = {
    "jobs": EntityType.JOB,
    "university": EntityType.ADMISSION,
    "visa": EntityType.VISA,
    "automobiles": EntityType.VEHICLE,
    "leads": EntityType.LEAD,
}


def entity_type_from_meta(meta: Dict[str, Any], category: str = "") -> EntityType:
    """Map an existing record's metadata.type (+category fallback) to EntityType.

    This is *typing*, not resolution — e.g. a UK sponsor register row is tagged
    SPONSOR (correctly not JOB), but re-routing it as a job source is Wave 3.
    """
    t = str((meta or {}).get("type", "")).lower()
    if t in _TYPE_MAP:
        return _TYPE_MAP[t]
    if "passport" in t:
        return EntityType.PASSPORT
    if "visa" in t:
        return EntityType.VISA
    if t.startswith("admission"):
        return EntityType.ADMISSION
    return _CATEGORY_MAP.get((category or "").lower(), EntityType.UNKNOWN)


# ── Source Reliability registry (0-100) — feeds confidence ────────────────────
# Substring-matched against a record's source. Higher = more trustworthy.
SOURCE_RELIABILITY: Dict[str, int] = {
    # official / government
    "travel.state.gov": 98, "ircc": 96, "nhtsa": 95, "data.gov": 95,
    "college_scorecard": 90, "gov": 95, "government": 95,
    # professional APIs / ATS
    "linkedin": 95, "proxycurl": 88, "brightdata": 85, "greenhouse": 88,
    "themuse": 85, "remotive": 85, "hipo": 85, "arbeitnow": 82,
    # csv / reference
    "henley": 85, "passport_index": 85, "wikipedia": 75,
    # maps / social
    "google_maps": 80, "maps": 80, "facebook": 70, "instagram": 60,
    # rss / news
    "pie": 75, "icef": 75, "study": 72, "rss": 72,
    # weak (not live / cached)
    "classified_listing": 55, "static": 45, "fallback": 40, "demo": 20,
}

_UNKNOWN_SOURCE_RELIABILITY = 65


def reliability_for(source: str, category: str = "") -> int:
    """Reliability weight for a source string (substring match; default 65)."""
    s = (source or "").lower()
    for key, val in SOURCE_RELIABILITY.items():
        if key in s:
            return val
    return _UNKNOWN_SOURCE_RELIABILITY


class Evidence(BaseModel):
    """A single explainability node for the Evidence Graph (populated in W3)."""
    signal: str
    weight: float = 0.0
    detail: str = ""


class ScrapedRecord(BaseModel):
    """Canonical validated record — a backward-compatible superset of the scraper
    dict. Used by the Validator to type-check ingestion; the pipeline continues to
    consume plain dicts, so this never breaks the existing contract."""
    title: str = ""
    source_url: str = ""
    description: str = ""
    location: str = ""
    price: str = ""
    category: str = ""
    entity_type: EntityType = EntityType.UNKNOWN
    source: str = ""
    source_reliability: int = _UNKNOWN_SOURCE_RELIABILITY
    confidence: float = 0.0
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


# ── Wave 3: Evidence Graph + Resolved Entity + Relationships ──────────────────

class EvidenceType(str, Enum):
    """Structured evidence node types — the vocabulary of explainable scoring."""
    HIRING = "hiring"
    EXPANSION = "expansion"
    FUNDING = "funding"
    POOR_REVIEWS = "poor_reviews"
    HIGH_RATINGS = "high_ratings"
    WEBSITE_MISSING_FEATURES = "website_missing_features"
    TECHNOLOGY_STACK = "technology_stack"
    SOCIAL_ACTIVITY = "social_activity"
    COMPLAINT = "complaint"
    RECOMMENDATION = "recommendation"
    GOVERNMENT_DATA = "government_data"
    NEWS = "news"
    COMMUNITY_DISCUSSION = "community_discussion"
    CONTACTABILITY = "contactability"       # phone/website/email present
    INTENT = "intent"                        # explicit buying intent
    DEADLINE = "deadline"                    # time-sensitive opportunity


class EvidenceNode(BaseModel):
    """A first-class, explainable evidence node backing a score."""
    type: EvidenceType
    value: float = 0.0                       # normalized 0..1 signal strength
    weight: float = 0.0                      # contribution weight to the score
    polarity: int = 1                        # +1 positive signal, -1 negative
    detail: str = ""
    source: str = ""
    source_reliability: float = 0.65
    confidence: float = 0.0                   # per-signal provenance confidence 0..1


class RelationType(str, Enum):
    PARENT = "parent"          # Branch → Company
    BRANCH = "branch"
    REVIEW = "review"
    EMPLOYEE = "employee"
    JOB = "job"
    COMPLAINT = "complaint"
    OPPORTUNITY = "opportunity"
    TECHNOLOGY = "technology"
    CONTACT = "contact"


class Relationship(BaseModel):
    rel_type: RelationType
    target_id: str
    detail: str = ""


class ResolvedEntity(BaseModel):
    """The output of the Entity Resolver — a canonical, explainable entity."""
    canonical_id: str
    entity_type: EntityType = EntityType.UNKNOWN
    name: str = ""
    location: str = ""
    confidence: float = 0.0                  # entity-resolution confidence 0..1
    source_reliability: float = 0.65         # blended reliability 0..1
    evidence: List[EvidenceNode] = Field(default_factory=list)
    reasoning: str = ""                      # human-readable resolution rationale
    parent_id: Optional[str] = None
    relationships: List[Relationship] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)   # every source it appeared in

    class Config:
        arbitrary_types_allowed = True


# ── Wave 4: Recommendation (decision engine output) ───────────────────────────

class Recommendation(BaseModel):
    """The Recommendation Engine's decision for one entity."""
    canonical_id: str = ""
    recommended_service: str = ""
    reason: str = ""
    evidence: List[str] = Field(default_factory=list)     # evidence types that drove it
    priority: str = "Low"                                 # Hot | High | Medium | Low
    confidence: float = 0.0
    recommended_offer: str = ""
    recommended_pitch: str = ""
    outreach_channel: str = ""                            # primary channel
    contact_order: List[str] = Field(default_factory=list)
    followup_strategy: str = ""
    next_best_action: str = ""
    conversion_probability: float = 0.0

    class Config:
        arbitrary_types_allowed = True

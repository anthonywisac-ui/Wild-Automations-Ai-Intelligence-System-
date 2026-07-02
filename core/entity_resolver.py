"""
Entity Resolver — Wave 3. Deterministic-first, LLM-second.

Resolves a normalized+validated record (from the Wave 1 boundary) into a
canonical ResolvedEntity: canonical_id, entity_type, confidence,
source_reliability, evidence (filled by evidence_graph), reasoning, parent_id.

Resolution order:
    1. Rules + patterns + schema  (entity_type already tagged in Wave 1;
       role refinement, canonical-key derivation, parent detection)
    2. LLM  — ONLY when the type is UNKNOWN / ambiguous (rare)

Framework-agnostic. No scrapers touched.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, Optional, Tuple

from core import domain, source_reliability
from core.domain import EntityType, ResolvedEntity

logger = logging.getLogger(__name__)

# Legal / branch tokens stripped when deriving a company's canonical name.
_LEGAL_SUFFIX = re.compile(
    r"\b(ltd|limited|llc|inc|incorporated|co|company|corp|corporation|plc|gmbh|"
    r"pvt|private|fzco|fze|fz-llc|est|establishment|trading|group|holdings?)\b\.?",
    re.I,
)
_BRANCH_HINT = re.compile(r"\b(branch|hq|head\s*office|main\s*branch)\b", re.I)
_BRANCH_WORDS = re.compile(r"\b(branch|hq|head\s*office|main)\b", re.I)
_UAE_CITIES = ("dubai", "abu dhabi", "sharjah", "ajman", "business bay",
               "deira", "bur dubai", "jlt", "marina")


def _canon_name(name: str) -> str:
    n = (name or "").lower()
    n = _LEGAL_SUFFIX.sub("", n)
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    n = " ".join(n.split())
    return n.strip()


def _canon_company(name: str) -> str:
    """Core company name — legal suffixes, branch words and city tokens stripped,
    so the same company merges across sources regardless of branch/location text."""
    n = _canon_name(name)
    n = _BRANCH_WORDS.sub("", n)
    for city in _UAE_CITIES:
        n = n.replace(city, "")
    return " ".join(n.split()).strip()


def _primary_location(location: str, description: str = "") -> str:
    blob = f"{location} {description}".lower()
    for city in _UAE_CITIES:
        if city in blob:
            return city
    return (location or "").split(",")[0].strip().lower()


def _cid(*parts: str) -> str:
    basis = "|".join(p for p in parts if p)
    return "ent_" + hashlib.md5(basis.encode("utf-8")).hexdigest()[:16]


def _canonical_key(rec: Dict[str, Any], etype: EntityType) -> Tuple[str, str, Optional[str], str]:
    """Return (canonical_id, canonical_name, parent_id, reasoning) — deterministic."""
    md = rec.get("metadata") or {}
    title = (rec.get("title") or "").strip()
    url = (rec.get("source_url") or "").strip()

    company_name = md.get("company") or title

    # Businesses (incl. business-style LEADs with a company name) merge by
    # company-core + location — the SAME company across Google/Maps/FB/IG/LinkedIn
    # resolves to one canonical_id (Requirement 3).
    is_business_like = etype in (
        EntityType.BUSINESS, EntityType.SPONSOR, EntityType.EMPLOYER,
        EntityType.COMPANY, EntityType.BRANCH) or (
        etype == EntityType.LEAD and md.get("company") and md.get("platform") in
        ("google_maps", "facebook", "linkedin"))
    if is_business_like:
        core = _canon_company(company_name)
        loc = _primary_location(rec.get("location", ""), rec.get("description", ""))
        cid = _cid(core, loc)
        parent_id = None
        reason = f"company keyed on core+location ({core!r}, {loc!r})"
        if _BRANCH_HINT.search(company_name) or etype == EntityType.BRANCH:
            parent_id = _cid(core)   # company across all branches/locations
            reason = f"branch of {core!r} → parent company {core!r}"
        return cid, core or title.lower(), parent_id, reason

    if etype in (EntityType.JOB, EntityType.ADMISSION, EntityType.VISA,
                 EntityType.OPPORTUNITY):
        if url:
            return _cid(url), title.lower(), None, f"{etype.value} keyed on source_url"
        return _cid(title.lower(), etype.value), title.lower(), None, f"{etype.value} keyed on title"

    if etype in (EntityType.LEAD, EntityType.PERSON, EntityType.CANDIDATE):
        key = url or f"{title.lower()}|{md.get('company','')}"
        return _cid(key), title.lower(), None, "person keyed on profile url/name"

    if etype == EntityType.VEHICLE:
        vk = f"{md.get('make','')}|{md.get('model','')}|{md.get('year','')}".lower()
        return _cid(vk), vk, None, "vehicle keyed on make+model+year"

    if etype == EntityType.PASSPORT:
        return _cid("passport", title.lower()), title.lower(), None, "passport keyed on title"

    if etype == EntityType.UNIVERSITY:
        return _cid("university", _canon_name(title)), _canon_name(title), None, "university keyed on name"

    return _cid(url or title.lower(), etype.value), title.lower(), None, "keyed on url/title"


def _refine_role(etype: EntityType, rec: Dict[str, Any]) -> Tuple[EntityType, str]:
    """Deterministic role refinement (buyer/seller, sponsor→potential employer)."""
    blob = f"{rec.get('title','')} {rec.get('description','')}".lower()
    if etype == EntityType.SPONSOR:
        return etype, "UK licensed sponsor → can sponsor visa → potential employer (job source)"
    if etype == EntityType.LEAD:
        if any(k in blob for k in ("we offer", "our services", "we provide", "hire us")):
            return EntityType.BUSINESS, "seller signal → reclassified as business (not buyer lead)"
        return etype, "buyer-intent person"
    if etype == EntityType.BUSINESS:
        return etype, "business (buyer candidate)"
    return etype, f"typed as {etype.value}"


async def resolve(rec: Dict[str, Any], category: str = "") -> ResolvedEntity:
    """Resolve a record → ResolvedEntity (deterministic; LLM only if UNKNOWN)."""
    md = rec.get("metadata") or {}
    cat = category or rec.get("_category", "")

    # entity_type: prefer the Wave 1 tag, else derive
    et_str = md.get("entity_type")
    etype = None
    if et_str:
        try:
            etype = EntityType(et_str)
        except ValueError:
            etype = None
    if etype is None:
        etype = domain.entity_type_from_meta(md, cat)

    etype, role_reason = _refine_role(etype, rec)

    # LLM fallback only when genuinely unknown (rare, deterministic-first)
    if etype == EntityType.UNKNOWN:
        etype, role_reason = await _resolve_llm(rec, cat)

    cid, cname, parent_id, key_reason = _canonical_key(rec, etype)
    reliability = source_reliability.score(md.get("source", ""), cat)
    base_conf = float(md.get("confidence") or 0.5)

    return ResolvedEntity(
        canonical_id=cid,
        entity_type=etype,
        name=(md.get("company") or rec.get("title") or cname)[:200],
        location=rec.get("location", ""),
        confidence=round(base_conf, 3),
        source_reliability=reliability,
        reasoning=f"{role_reason}; {key_reason}",
        parent_id=parent_id,
        sources=[md.get("source", "")] if md.get("source") else [],
    )


async def _resolve_llm(rec: Dict[str, Any], category: str) -> Tuple[EntityType, str]:
    """LLM classification — invoked only for UNKNOWN entities."""
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return EntityType.UNKNOWN, "no LLM; left UNKNOWN"
        types = ", ".join(e.value for e in EntityType)
        prompt = (
            f"Classify this record into ONE entity type from [{types}]. "
            f"Title: {rec.get('title','')[:120]}. Desc: {rec.get('description','')[:180]}. "
            "Return ONLY the single type string."
        )
        raw = (await llm.complete(prompt, max_tokens=20, temperature=0)).strip().lower()
        for e in EntityType:
            if e.value in raw:
                return e, f"LLM classified as {e.value}"
    except Exception as exc:
        logger.warning("entity_resolver: LLM classify failed: %s", exc)
    return EntityType.UNKNOWN, "LLM inconclusive; left UNKNOWN"

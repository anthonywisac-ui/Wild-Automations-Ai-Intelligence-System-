"""
Validator — Wave 1.

Enforces the record contract at the ingestion boundary: rejects junk (empty
titles, bare platform names, records with no supporting data), type-checks via
the domain schema, and attaches additive intelligence fields
(`entity_type`, `source_reliability`, `confidence`).

`confidence = feature_completeness × (source_reliability / 100)` — so sparse
records from weak sources cannot rank highly downstream. Scoring still runs on
the existing dict contract; these fields are additive and consumed in Wave 3.

Never raises on a single bad record — on internal error it keeps the record
(fail-open) so a validation bug can never silently empty a working scraper.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from core import domain, normalize

logger = logging.getLogger(__name__)

_MIN_TITLE_LEN = 2
_BARE_PLATFORM = {"instagram", "facebook", "linkedin", "twitter", "x",
                  "tiktok", "google", "youtube", "reddit", "maps"}
_MD_RICH_FIELDS = ("price_usd", "rating", "review_count", "followers", "company",
                   "deadlines", "application_deadline", "make", "model", "salary",
                   "processing_time", "gpa_minimum")


class ValidationResult:
    __slots__ = ("ok", "record", "reason")

    def __init__(self, ok: bool, record: Optional[Dict[str, Any]], reason: str = ""):
        self.ok = ok
        self.record = record
        self.reason = reason


def _has_body(rec: Dict[str, Any], md: Dict[str, Any]) -> bool:
    """A record must carry *some* substance: a URL, a real description, or rich metadata."""
    if rec.get("source_url"):
        return True
    if len((rec.get("description") or "").strip()) >= 10:
        return True
    return any(md.get(f) not in (None, "", [], {}) for f in _MD_RICH_FIELDS)


def _feature_completeness(rec: Dict[str, Any], md: Dict[str, Any]) -> float:
    present = [
        bool((rec.get("title") or "").strip()),
        bool(rec.get("source_url")),
        len((rec.get("description") or "").strip()) >= 10,
        bool((rec.get("location") or "").strip()),
        bool(rec.get("price") or any(md.get(f) for f in _MD_RICH_FIELDS)),
    ]
    return sum(1 for p in present if p) / len(present)


def validate_record(rec: Dict[str, Any], category: str = "") -> ValidationResult:
    """Validate + enrich a single (already-normalized) record."""
    if not isinstance(rec, dict):
        return ValidationResult(False, None, "not a dict")
    try:
        title = (rec.get("title") or "").strip()
        md: Dict[str, Any] = dict(rec.get("metadata") or {})
        cat = category or rec.get("_category", "") or ""

        # ── junk rules (conservative) ──
        if len(title) < _MIN_TITLE_LEN:
            return ValidationResult(False, None, f"empty/short title: {title!r}")
        if title.lower() in _BARE_PLATFORM:
            return ValidationResult(False, None, f"bare platform name: {title!r}")
        if not _has_body(rec, md):
            return ValidationResult(False, None, "no supporting data (url/description/metadata)")

        # ── schema type-check (coerce to str where needed) ──
        try:
            domain.ScrapedRecord(
                title=title,
                source_url=str(rec.get("source_url", "")),
                description=str(rec.get("description", "")),
                location=str(rec.get("location", "")),
                price=str(rec.get("price", "")),
                category=str(cat),
                source=str(md.get("source", "")),
                metadata=md,
            )
        except ValidationError as exc:
            logger.warning("validate_record: schema reject: %s", exc)
            return ValidationResult(False, None, "schema validation failed")

        # ── additive enrichment (entity type + reliability + confidence) ──
        etype = domain.entity_type_from_meta(md, cat)
        reliability = md.get("source_reliability")
        if not isinstance(reliability, int):
            reliability = domain.reliability_for(md.get("source", ""), cat)
        completeness = _feature_completeness(rec, md)
        confidence = round(completeness * (reliability / 100.0), 3)

        out = dict(rec)
        md["entity_type"] = etype.value
        md["source_reliability"] = reliability
        md["confidence"] = confidence
        md.setdefault("evidence", [])
        out["metadata"] = md
        return ValidationResult(True, out, "")
    except Exception as exc:  # fail-open: never drop a record to a validator bug
        logger.warning("validate_record: unexpected error, keeping record: %s", exc)
        return ValidationResult(True, rec, "validator-error-passthrough")


def clean_and_validate(records: Optional[List[Dict[str, Any]]],
                       source: str = "", category: str = "") -> Tuple[List[Dict[str, Any]], int]:
    """Normalize + validate a scraper's result list. Returns (kept, dropped_count)."""
    kept: List[Dict[str, Any]] = []
    dropped = 0
    for rec in (records or []):
        try:
            normalized = normalize.normalize_record(rec, source=source, category=category)
            result = validate_record(normalized, category=category)
            if result.ok and result.record is not None:
                kept.append(result.record)
            else:
                dropped += 1
                logger.debug("clean_and_validate: dropped (%s)", result.reason)
        except Exception as exc:  # never lose a record to an unexpected error
            logger.warning("clean_and_validate: passthrough on error: %s", exc)
            kept.append(rec)
    return kept, dropped

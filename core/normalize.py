"""
Normalizer — Wave 1.

Cleans a raw scraper record in place-safe fashion (returns a new dict): repairs
mojibake (â— → —), strips control chars, collapses whitespace, canonicalizes
names, and attaches the source-reliability weight from the registry.

Pure, deterministic, dependency-light (runs in the ingestion hot path). It only
cleans strings and adds additive metadata — it never changes business fields or
drops records (dropping is the Validator's job).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from core import domain

logger = logging.getLogger(__name__)

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_WS = re.compile(r"\s+")
_TRAILING_SEP = re.compile(r"[\s·|—–\-]+$")
_LEADING_SEP = re.compile(r"^[\s·|—–\-]+")
# markers that indicate UTF-8 bytes were mis-decoded as Latin-1/cp1252
# Mojibake pattern: UTF-8 lead byte (Ã/â/Â) + continuation (U+0080-U+00BF).
_MOJIBAKE_RE = re.compile("[ÂÃâÃ¬][-¿]")


def _mojibake_marks(s: str) -> int:
    return len(_MOJIBAKE_RE.findall(s))


def fix_encoding(s: str) -> str:
    """Reverse 'UTF-8 bytes decoded as Latin-1/cp1252' mojibake, safely.

    The round-trip only succeeds on genuine mojibake byte sequences, and we
    accept the repair *only* if it reduces mojibake markers — so legitimate
    accented text (e.g. 'château') is left untouched.
    """
    if not s or not _MOJIBAKE_RE.search(s):
        return s
    repaired = s
    try:
        repaired = s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        try:
            repaired = s.encode("cp1252").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError, LookupError):
            return s
    return repaired if _mojibake_marks(repaired) < _mojibake_marks(s) else s


def clean_text(value: Any) -> str:
    """Repair encoding, drop control chars, collapse whitespace, trim."""
    if value is None:
        return ""
    s = value if isinstance(value, str) else str(value)
    s = fix_encoding(s)
    s = _CTRL.sub("", s)
    s = _WS.sub(" ", s).strip()
    return s


def canonical_name(value: Any) -> str:
    """Clean a business/person/title name and strip dangling separators."""
    s = clean_text(value)
    s = _TRAILING_SEP.sub("", s)
    s = _LEADING_SEP.sub("", s)
    return s.strip()


def normalize_record(rec: Dict[str, Any], source: str = "", category: str = "") -> Dict[str, Any]:
    """Return a cleaned copy of a scraper record.

    Cleans the standard text fields + common metadata strings and attaches
    `metadata.source_reliability`. Non-dict input is returned unchanged.
    """
    if not isinstance(rec, dict):
        return rec
    try:
        out: Dict[str, Any] = dict(rec)
        md: Dict[str, Any] = dict(out.get("metadata") or {})

        if "title" in out:
            out["title"] = canonical_name(out.get("title"))
        for field in ("description", "location", "price"):
            if field in out:
                out[field] = clean_text(out.get(field))

        for field in ("company", "role", "category", "name", "post_text"):
            if isinstance(md.get(field), str):
                md[field] = clean_text(md[field])

        src = md.get("source") or source or ""
        md["source_reliability"] = domain.reliability_for(src, category)
        md["_normalized"] = True
        out["metadata"] = md
        return out
    except Exception as exc:  # never let cleaning break a working scraper
        logger.warning("normalize_record: skipped due to error: %s", exc)
        return rec

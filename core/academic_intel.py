"""
Academic Intelligence — Admissions taxonomy + stipend detection (Phase 3).

Implements the "Pan-European & Global Academic Intelligence" docs: detect
short-notice / late-intake admission windows and cash-stipend / free-tuition
triggers across countries, so the engine surfaces HIGH-VALUE opportunities
(open-now admissions with funding) instead of generic university listings.

    flags(text, meta)  -> deterministic taxonomy/stipend flags (fast, no LLM)
    mine(record)       -> GROQ enrichment (admission_status, deadline, funding)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Late-intake / short-notice admission keywords per region (from the taxonomy matrix)
LATE_INTAKE_TERMS = [
    # Germany
    "nc-frei", "zulassungsfrei", "losverfahren", "nachrückverfahren", "nachrueckverfahren",
    # Italy
    "immatricolazione tardiva", "posti residui", "terzo bando",
    # France
    "phase complémentaire", "phase complementaire", "rentrée décalée", "monmaster late",
    # Spain
    "convocatoria extraordinaria", "plazas vacantes", "fase extraordinaria",
    # Nordics / Poland / Hungary
    "restplatser", "rekrutacja uzupełniająca", "wolne miejsca", "last-call",
    # UK / US / Canada / AU / Ireland
    "clearing", "adjustment vacancies", "rolling admission", "rolling admissions",
    "spring intake", "late fall", "post-deadline", "january rollover", "january intake",
    "trimester", "mid-year intake", "cao available places", "available places",
    # Turkey / borders
    "ek kontenjan", "supplementary intake", "sesiune de toamnă", "extra quota",
    # generic
    "late application", "open for application", "still open", "applications open",
    "extended deadline", "continuous enrollment", "continuous selection",
]

# Cash-stipend / free-tuition triggers
STIPEND_TERMS = [
    "türkiye bursları", "turkiye burslari", "daad", "deutschlandstipendium",
    "stipendium hungaricum", "eiffel scholarship", "crous", "dsu", "edisu",
    "swedish institute", "government of ireland", "romanian government scholarship",
    "rtps", "research training program", "graduate assistantship", "ta/ra",
    "full tuition waiver", "tuition waiver", "fee waiver", "fee remission",
    "monthly stipend", "cash stipend", "living allowance", "pocket money",
    "fully funded", "fully-funded", "free tuition", "free accommodation",
    "msca", "marie skłodowska", "tv-l e13", "automatic bursary", "bursary",
    "scholarship", "stipend", "grant", "assistantship",
]

FREE_TUITION_TERMS = ["free tuition", "100% tuition", "tuition waiver", "fee waiver",
                      "no tuition", "fee remission", "full waiver"]
CASH_TERMS = ["stipend", "monthly allowance", "cash stipend", "living allowance",
              "pocket money", "€", "$", "monthly"]


def _hits(text: str, terms: List[str]) -> List[str]:
    t = (text or "").lower()
    return [term for term in terms if term in t]


def flags(text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deterministic admissions signals from a record's text + metadata."""
    m = meta or {}
    blob = f"{text} {json.dumps(m, default=str)}".lower()

    late_hits = _hits(blob, LATE_INTAKE_TERMS)
    stipend_hits = _hits(blob, STIPEND_TERMS)
    free_tuition = bool(_hits(blob, FREE_TUITION_TERMS))
    cash_stipend = bool(_hits(blob, CASH_TERMS)) and bool(stipend_hits)

    return {
        "is_late_intake": bool(late_hits),
        "late_terms": late_hits[:4],
        "has_funding": bool(stipend_hits),
        "funding_terms": stipend_hits[:4],
        "free_tuition": free_tuition,
        "cash_stipend": cash_stipend,
    }


async def mine(record: Dict[str, Any]) -> Dict[str, Any]:
    """GROQ enrichment (best-effort): admission status, deadline, funding class."""
    text = f"{record.get('title','')} {record.get('description','')}"
    m = record.get("metadata") or {}
    det = flags(text, m)
    # Only spend an LLM call when there is a real signal to classify.
    if not (det["is_late_intake"] or det["has_funding"]):
        return det
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return det
        prompt = (
            "You are a cross-border academic intelligence engine. From the admission "
            "text, output ONLY JSON: {\"admission_status\": one of "
            "['Open','Late-Phase-Only','Rolling','Closed'], "
            "\"funding\": one of ['Full Waiver + Stipend','Full Waiver','Partial Scholarship','None'], "
            "\"deadline_hint\": short string or null, "
            "\"why_valuable\": one short sentence}. "
            f"Text: {text[:600]}"
        )
        raw = (await llm.complete(prompt, max_tokens=180, temperature=0.3)).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            raw = raw[4:] if raw.lower().startswith("json") else raw
        mt = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(mt.group(0) if mt else raw)
        det.update({
            "admission_status": data.get("admission_status"),
            "funding_class": data.get("funding"),
            "deadline_hint": data.get("deadline_hint"),
            "why_valuable": data.get("why_valuable"),
        })
    except Exception as exc:
        logger.warning("academic_intel: mine LLM failed: %s", exc)
    return det

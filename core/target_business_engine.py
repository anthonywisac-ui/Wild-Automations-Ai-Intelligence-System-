"""
Target Business Engine — Search Planning layer.

Maps a SERVICE to the CONCRETE, searchable business categories that BUY it
(dentist, restaurant, clinic, law firm, gym, salon, real estate, ecommerce…),
so the planner searches for buyers instead of the service (which returns
competitors). Blueprint-backed with LLM fallback (buyer-target prompt) and a
heuristic default. Deterministic-first, framework-agnostic.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

_BLUEPRINTS = Path(__file__).resolve().parent.parent / "data" / "niche_blueprints.json"
_CACHE = Path(__file__).resolve().parent.parent / "data" / "target_business_cache.json"

# Generic local-business categories that buy most B2B services.
_GENERIC_TARGETS = ["dentist", "restaurant", "clinic", "law firm", "gym", "salon",
                    "real estate agency", "construction company", "ecommerce store",
                    "accounting firm", "car dealership", "hotel"]


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("target_business_engine: save failed: %s", exc)


def _from_blueprint(service: str) -> Optional[List[str]]:
    bps = _load(_BLUEPRINTS, {}).get("blueprints", {})
    g = service.lower()
    for bp in bps.values():
        if any(kw in g for kw in bp.get("match", [])):
            cats = bp.get("target_business_categories")
            if cats:
                return list(cats)
    return None


async def _from_llm(service: str) -> Optional[List[str]]:
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return None
        prompt = (
            "A company sells this service. List the 10-15 CONCRETE, Google-Maps-searchable "
            "LOCAL BUSINESS TYPES that BUY this service (e.g. dentist, restaurant, law firm, "
            "gym). Do NOT list providers of the service. Return ONLY a JSON array of short "
            f"business-type names. Service: {service}"
        )
        raw = (await llm.complete(prompt, max_tokens=220, temperature=0.4)).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            raw = raw[4:] if raw.lower().startswith("json") else raw
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        cats = [str(x).strip() for x in json.loads(m.group(0) if m else raw) if x]
        return cats or None
    except Exception as exc:
        logger.warning("target_business_engine: LLM failed: %s", exc)
        return None


async def targets_for(service: str, *, refresh: bool = False) -> List[str]:
    """Concrete searchable business categories that buy `service`."""
    bp = _from_blueprint(service)
    if bp:
        return bp
    cache = _load(_CACHE, {})
    key = service.strip().lower()
    if not refresh and key in cache:
        return cache[key]
    llm = await _from_llm(service)
    result = llm or list(_GENERIC_TARGETS)
    try:
        cache[key] = result
        _save(_CACHE, cache)
    except Exception:
        pass
    return result

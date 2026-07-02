"""
Buyer Persona Engine — Wave 2. Fully data-driven (JSON config + LLM).

Given a service/goal, returns the buyer personas who purchase it. Resolution:
    1. niche blueprint match  (data/niche_blueprints.json)  — instant, no LLM
    2. persona config match    (data/personas.json, optional)
    3. LLM generation          (core.llm_client)             — cached to config
    4. heuristic fallback

No personas are hardcoded in this module — they come from config or the LLM.
Framework-agnostic.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.search_types import BuyerPersona

logger = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parent.parent / "data"
_BLUEPRINTS = _DATA / "niche_blueprints.json"
_PERSONAS = _DATA / "personas.json"          # optional user-defined personas
_CACHE = _DATA / "persona_cache.json"        # LLM results cached here


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
        logger.warning("persona_engine: save failed %s: %s", path.name, exc)


def _key(service: str) -> str:
    return hashlib.md5(service.strip().lower().encode("utf-8")).hexdigest()[:12]


def _from_blueprint(service: str) -> Optional[List[BuyerPersona]]:
    bps = _load(_BLUEPRINTS, {}).get("blueprints", {})
    g = service.lower()
    for name, bp in bps.items():
        if any(kw in g for kw in bp.get("match", [])):
            return [BuyerPersona(name=p, sector=name, origin=f"blueprint:{name}")
                    for p in bp.get("target_personas", [])]
    return None


def _from_config(service: str) -> Optional[List[BuyerPersona]]:
    cfg = _load(_PERSONAS, {}).get("services", {})
    g = service.lower()
    for key, personas in cfg.items():
        if key.lower() in g or g in key.lower():
            return [BuyerPersona(name=p if isinstance(p, str) else p.get("name", ""),
                                 sector=key,
                                 attributes=(p if isinstance(p, dict) else {}),
                                 origin="config")
                    for p in personas]
    return None


async def _from_llm(service: str) -> Optional[List[BuyerPersona]]:
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return None
        prompt = (
            "List the 6-10 business types who BUY this service. "
            "Return ONLY a JSON array of short names. Service: " + service
        )
        raw = (await llm.complete(prompt, max_tokens=200, temperature=0.4)).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            raw = raw[4:] if raw.lower().startswith("json") else raw
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        names = json.loads(m.group(0) if m else raw)
        return [BuyerPersona(name=str(n), origin=f"llm:{llm.provider}") for n in names if n]
    except Exception as exc:
        logger.warning("persona_engine: LLM generation failed: %s", exc)
        return None


def _heuristic(service: str) -> List[BuyerPersona]:
    return [BuyerPersona(name=service.strip(), origin="heuristic")]


async def generate(service: str, *, refresh: bool = False) -> List[BuyerPersona]:
    """Return buyer personas for a service (blueprint → config → cache → LLM → heuristic)."""
    if not service or not service.strip():
        return _heuristic("business leads")

    bp = _from_blueprint(service)
    if bp:
        return bp
    cfg = _from_config(service)
    if cfg:
        return cfg

    cache = _load(_CACHE, {})
    key = _key(service)
    if not refresh and key in cache:
        return [BuyerPersona(**p) for p in cache[key]]

    llm = await _from_llm(service)
    result = llm or _heuristic(service)
    try:
        cache[key] = [p.model_dump() for p in result]
        _save(_CACHE, cache)
    except Exception:
        pass
    return result

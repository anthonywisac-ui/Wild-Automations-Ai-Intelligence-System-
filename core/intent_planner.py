"""
Intent Planner — the "think-first, search-second" brain that runs BEFORE scrapers.

Given a business goal / service, it produces a search plan:
    { buyer_personas[], pain_points[], intent_queries{hot,warm,problem,hiring,comparison},
      priority_sources[], gmaps_keywords[], scoring_triggers{} }

Resolution order (fast → smart):
    1. Niche blueprint match  (data/niche_blueprints.json)  — instant, no LLM
    2. Cached plan            (data/intent_plans.json)      — reuse prior LLM plan
    3. GROQ generation        (core.llm_client)             — fresh plan, then cached

Also provides query ROTATION: each run pulls the next intent query from the pooled
list (round-robin), which improves coverage and reduces CAPTCHA/pattern risk.
Everything degrades gracefully — no LLM key → blueprint or a safe heuristic plan.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parent.parent / "data"
_BLUEPRINTS = _DATA / "niche_blueprints.json"
_PLANS = _DATA / "intent_plans.json"
_ROTATION = _DATA / "query_rotation.json"

_QUERY_TIERS = ("hot", "warm", "problem", "hiring", "comparison")


# ── small JSON helpers ────────────────────────────────────────────────────────
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
        logger.warning("intent_planner: could not save %s: %s", path.name, exc)


def _goal_key(goal: str) -> str:
    return hashlib.md5(goal.strip().lower().encode("utf-8")).hexdigest()[:12]


# ── blueprint match ───────────────────────────────────────────────────────────
def _match_blueprint(goal: str) -> Optional[Dict[str, Any]]:
    data = _load(_BLUEPRINTS, {}).get("blueprints", {})
    g = goal.lower()
    for name, bp in data.items():
        if any(kw in g for kw in bp.get("match", [])):
            plan = {
                "buyer_personas": bp.get("target_personas", []),
                "pain_points": bp.get("core_departments", []),
                "intent_queries": bp.get("intent_queries", {}),
                "priority_sources": bp.get("priority_sources", []),
                "gmaps_keywords": bp.get("target_personas", [])[:3],
                "scoring_triggers": bp.get("lead_scoring_triggers", {}),
                "_origin": f"blueprint:{name}",
            }
            return plan
    return None


# ── GROQ generation ───────────────────────────────────────────────────────────
_PLAN_PROMPT = (
    "You are the Search Intelligence Architect for a B2B lead-gen engine. "
    "Given a service/goal, output ONLY JSON with these keys:\n"
    "buyer_personas (6-10 business types who BUY this),\n"
    "pain_points (8-12 operational problems those buyers have),\n"
    "intent_queries: an object with keys hot, warm, problem, hiring, comparison — "
    "each a list of 4-6 SEARCH PHRASES that a BUYER expressing a NEED would type "
    "(never seller/directory phrases like 'marketing agency dubai'; use buyer intent "
    "like 'looking for', 'need', 'recommend', 'hiring', 'alternative to'),\n"
    "priority_sources (subset of: google, google_maps, instagram, facebook, linkedin, reddit, quora),\n"
    "gmaps_keywords (3-5 business categories to search on Google Maps).\n"
    "Goal: {goal}\n"
    "Return raw JSON only, no markdown."
)


async def _generate_plan(goal: str) -> Optional[Dict[str, Any]]:
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return None
        raw = await llm.complete(_PLAN_PROMPT.format(goal=goal), max_tokens=700, temperature=0.4)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            raw = raw[4:].strip() if raw.lower().startswith("json") else raw.strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        plan = json.loads(m.group(0) if m else raw)
        plan["_origin"] = f"llm:{llm.provider}"
        return plan
    except Exception as exc:
        logger.warning("intent_planner: LLM generation failed: %s", exc)
        return None


def _heuristic_plan(goal: str) -> Dict[str, Any]:
    """Last-resort plan when no blueprint + no LLM."""
    g = goal.strip()
    return {
        "buyer_personas": [g],
        "pain_points": ["missed calls", "slow response", "no follow up", "lost leads"],
        "intent_queries": {
            "hot": [f"looking for {g}", f"need {g}", f"recommend {g}"],
            "warm": [f"{g} not working", f"struggling with {g}"],
            "problem": [f"{g} problem", f"{g} complaints"],
            "hiring": [f"hiring for {g}"],
            "comparison": [f"best {g}", f"alternative to {g}"],
        },
        "priority_sources": ["google", "facebook", "instagram", "reddit"],
        "gmaps_keywords": [g],
        "scoring_triggers": {},
        "_origin": "heuristic",
    }


async def _buyerize(goal: str, base: Dict[str, Any]) -> Dict[str, Any]:
    """Override seller-oriented queries with BUYER-FIRST ones: concrete target
    business categories for Maps + validated buyer/pain phrases for social. Every
    phrase is gated by the query_validator so no seller query survives."""
    try:
        from core import target_business_engine, query_validator
        cats = await target_business_engine.targets_for(goal)
        if not cats:
            return base
        pains = base.get("pain_points") or [
            "poor reviews", "no whatsapp", "weak social media", "missed calls"]
        problem, hiring = [], []
        for biz in cats[:8]:
            for pain in pains[:4]:
                phrase = f'"{biz}" "{pain}"'
                qs = query_validator.score_query(
                    phrase, platform="reddit", tier="problem", mode="intent",
                    service=goal, target_categories=cats)
                if qs.accepted:
                    problem.append(phrase)
            hiring.append(f'"{biz}" hiring marketing')
        iq = {k: v for k, v in {"problem": problem, "hiring": hiring}.items() if v}
        if iq:
            base = dict(base)
            base["intent_queries"] = iq
            base["gmaps_keywords"] = cats                 # concrete buyer businesses
            base["target_business_categories"] = cats
            base["_origin"] = (base.get("_origin", "") + "+buyer-first").lstrip("+")
    except Exception as exc:
        logger.warning("intent_planner: buyerize failed: %s", exc)
    return base


# ── public: plan ──────────────────────────────────────────────────────────────
async def plan(goal: str, *, refresh: bool = False) -> Dict[str, Any]:
    """Return a BUYER-FIRST search plan for a goal (blueprint → cache → LLM →
    heuristic, then buyer-first override that targets businesses, not the service)."""
    if not goal or not goal.strip():
        return await _buyerize("business leads", _heuristic_plan("business leads"))

    bp = _match_blueprint(goal)
    if bp:
        return await _buyerize(goal, bp)

    key = _goal_key(goal)
    cache = _load(_PLANS, {})
    if not refresh and key in cache:
        return await _buyerize(goal, cache[key])

    generated = await _generate_plan(goal)
    result = generated or _heuristic_plan(goal)
    cache[key] = result
    _save(_PLANS, cache)
    return await _buyerize(goal, result)


# ── public: flatten + rotate queries ──────────────────────────────────────────
def pooled_queries(plan_obj: Dict[str, Any], tiers: Optional[List[str]] = None) -> List[str]:
    """Flatten intent_queries into a priority-ordered pool (hot first)."""
    iq = plan_obj.get("intent_queries", {}) or {}
    order = tiers or list(_QUERY_TIERS)
    pool: List[str] = []
    for tier in order:
        for q in (iq.get(tier) or []):
            if q and q not in pool:
                pool.append(q)
    return pool


def next_queries(goal: str, plan_obj: Dict[str, Any], count: int = 1,
                 tiers: Optional[List[str]] = None) -> List[str]:
    """Pick the next `count` queries — self-learning aware.

    The pool is re-ranked by learned performance (signal memory): queries that
    historically produced high-appeal leads bubble to the top, while unseen
    queries keep an optimistic prior so they still get explored. A persisted
    rotation index then cycles through the ranked pool for coverage.
    """
    pool = pooled_queries(plan_obj, tiers)
    if not pool:
        return []
    # Adaptive ranking: blend appeal-based (signal_memory) with outcome-based
    # (learning_engine) query performance — best-converting queries bubble up.
    try:
        from core import signal_memory
        try:
            from core import learning_engine
            pool = sorted(pool, key=lambda q: signal_memory.query_score(goal, q)
                          * learning_engine.weight("query", q), reverse=True)
        except Exception:
            pool = signal_memory.rank_queries(goal, pool)
    except Exception:
        pass
    state = _load(_ROTATION, {})
    key = _goal_key(goal)
    idx = int(state.get(key, 0))
    picked = [pool[(idx + i) % len(pool)] for i in range(min(count, len(pool)))]
    state[key] = (idx + len(picked)) % len(pool)
    _save(_ROTATION, state)
    return picked

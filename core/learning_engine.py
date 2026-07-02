"""
Learning Engine — Wave 5.

Learns from EVERY interaction event (not just Won/Lost): search, query, source,
contact, reply, booking, conversion, revenue. The Event Timeline is the single
source of truth; learned weights are computed from it on demand (feedback loop:
CRM events → learning → adaptive weights).

Provides adaptive multipliers (≈0.5–1.5, neutral=1.0) per dimension:
    query · source · offer · channel · persona
plus Outcome Attribution (credit an outcome back to the query/source/offer/
persona that produced the lead).

Reuses core.event_timeline (events) and core.signal_memory (appeal-based query
ranking). Framework-agnostic, fail-soft.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core import event_timeline
from core.event_timeline import EventType

logger = logging.getLogger(__name__)

# Success weighting per outcome event type (how much each signals a "win").
_OUTCOME_WEIGHT = {
    EventType.CONTACT: 0.3,
    EventType.REPLY: 0.5,
    EventType.MEETING: 0.7,
    EventType.BOOKING: 0.8,
    EventType.CONVERSION: 0.9,
    EventType.SALE: 1.0,
    EventType.WON: 1.0,
    EventType.REVENUE: 1.0,
    EventType.LOST: 0.0,
}

_DIMENSIONS = ("query", "source", "offer", "channel", "persona")
_PRIOR = 0.5          # neutral prior outcome
_PRIOR_WEIGHT = 3.0   # Bayesian smoothing strength
_MIN, _MAX = 0.5, 1.5  # multiplier range


def _lineage(canonical_id: str) -> Dict[str, str]:
    """Recover a lead's origin (query/source/offer/channel/persona) from its
    RECOMMENDATION / discovery events — used for outcome attribution."""
    lin: Dict[str, str] = {}
    for e in event_timeline.timeline(canonical_id):
        import json
        try:
            p = json.loads(e.get("payload") or "{}")
        except Exception:
            p = {}
        for d in _DIMENSIONS:
            if p.get(d) and d not in lin:
                lin[d] = p[d]
    return lin


def record_outcome(canonical_id: str, event_type: EventType,
                   value: Optional[float] = None,
                   attribution: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Record a CRM outcome event and attribute it to the lead's origin lineage."""
    lin = dict(attribution or {})
    if canonical_id and not lin:
        lin = _lineage(canonical_id)
    outcome = _OUTCOME_WEIGHT.get(event_type, 0.5)
    payload = {**lin, "attributed": True}
    event_timeline.record(event_type, canonical_id=canonical_id,
                          payload=payload, outcome=outcome, value=value)
    return {"recorded": event_type.value, "attribution": lin, "outcome": outcome}


def _aggregate(dimension: str) -> Dict[str, Dict[str, float]]:
    """Aggregate outcome signals by a dimension key across all outcome events."""
    import json
    agg: Dict[str, Dict[str, float]] = {}
    for et in _OUTCOME_WEIGHT:
        for e in event_timeline.recent(et, days=365):
            try:
                p = json.loads(e.get("payload") or "{}")
            except Exception:
                continue
            key = p.get(dimension)
            if not key:
                continue
            o = e.get("outcome")
            if o is None:
                o = _OUTCOME_WEIGHT.get(et, 0.5)
            a = agg.setdefault(key, {"n": 0.0, "sum": 0.0})
            a["n"] += 1
            a["sum"] += float(o)
    return agg


def _smoothed(stat: Dict[str, float]) -> float:
    return (stat["sum"] + _PRIOR * _PRIOR_WEIGHT) / (stat["n"] + _PRIOR_WEIGHT)


def weight(dimension: str, key: str) -> float:
    """Adaptive multiplier for a (dimension, key) — neutral 1.0 until learned."""
    if not key:
        return 1.0
    agg = _aggregate(dimension)
    stat = agg.get(key)
    if not stat or stat["n"] < 1:
        return 1.0
    # map smoothed outcome (0..1, prior 0.5) → multiplier (_MIN.._MAX, neutral 1.0)
    s = _smoothed(stat)
    return round(_MIN + (_MAX - _MIN) * s, 3)


def weights(dimension: str) -> Dict[str, float]:
    agg = _aggregate(dimension)
    return {k: round(_MIN + (_MAX - _MIN) * _smoothed(v), 3) for k, v in agg.items()}


def rank(dimension: str, items: List[str]) -> List[str]:
    """Sort items by learned outcome weight (best-first); unseen keep neutral 1.0."""
    return sorted(items, key=lambda k: weight(dimension, k), reverse=True)


def attribution_summary() -> Dict[str, Any]:
    """What is actually driving outcomes (for transparency / the feedback loop)."""
    out: Dict[str, Any] = {}
    for d in _DIMENSIONS:
        w = weights(d)
        if w:
            best = max(w.items(), key=lambda kv: kv[1])
            out[d] = {"learned_keys": len(w), "best": best[0], "best_weight": best[1]}
    return out

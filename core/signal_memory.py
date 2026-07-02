"""
Signal Memory — the self-learning layer (Phase 4 / Phase 5 vision).

Closes the loop: after leads are scored, it records HOW each intent query and
source performed (average appeal, number of Hidden Gems). Over time the Intent
Planner uses this memory to prioritise the queries/sources that actually produce
high-value leads — the engine gets better the more it runs.

Persisted to data/signal_memory.json.

    record_outcome(goal, query, source, appeal_scores, ratings)
    query_score(goal, query) -> float          # learned 0..1 (optimistic for new)
    rank_queries(goal, queries) -> [queries]    # best-performing first, explores new
    source_performance(goal) -> {source: score}
    summary(goal) -> compact stats for the dashboard
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MEM = Path(__file__).resolve().parent.parent / "data" / "signal_memory.json"

# Optimistic prior for unseen queries → guarantees exploration before exploitation.
_PRIOR_SCORE = 0.7
_PRIOR_WEIGHT = 2.0   # pseudo-observations backing the prior (Bayesian smoothing)
_GEM_THRESHOLD = 0.8


def _key(goal: str) -> str:
    return hashlib.md5((goal or "").strip().lower().encode("utf-8")).hexdigest()[:12]


def _load() -> Dict[str, Any]:
    try:
        return json.loads(_MEM.read_text(encoding="utf-8"))
    except Exception:
        return {"goals": {}}


def _save(data: Dict[str, Any]) -> None:
    try:
        _MEM.parent.mkdir(parents=True, exist_ok=True)
        _MEM.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("signal_memory: save failed: %s", exc)


def _bucket(entry: Dict[str, Any]) -> Dict[str, Any]:
    entry.setdefault("runs", 0)
    entry.setdefault("leads", 0)
    entry.setdefault("sum_appeal", 0.0)
    entry.setdefault("gems", 0)
    return entry


def record_outcome(goal: str, query: Optional[str], source: Optional[str],
                   appeal_scores: List[float]) -> None:
    """Log the appeal outcomes for a (goal, query, source) after scoring."""
    if not goal:
        return
    data = _load()
    g = data["goals"].setdefault(_key(goal), {"goal": goal, "queries": {}, "sources": {}})
    n = len(appeal_scores)
    total = sum(appeal_scores)
    gems = sum(1 for a in appeal_scores if a >= _GEM_THRESHOLD)

    for field, val in (("queries", query), ("sources", source)):
        if not val:
            continue
        e = _bucket(g[field].setdefault(val, {}))
        e["runs"] += 1
        e["leads"] += n
        e["sum_appeal"] += total
        e["gems"] += gems
    _save(data)


def _smoothed(entry: Dict[str, Any]) -> float:
    """Bayesian-smoothed average appeal (falls back toward the optimistic prior)."""
    leads = entry.get("leads", 0)
    s = entry.get("sum_appeal", 0.0)
    return (s + _PRIOR_SCORE * _PRIOR_WEIGHT) / (leads + _PRIOR_WEIGHT)


def query_score(goal: str, query: str) -> float:
    data = _load()
    g = data["goals"].get(_key(goal), {})
    e = (g.get("queries") or {}).get(query)
    if not e:
        return _PRIOR_SCORE
    return round(_smoothed(e), 3)


def rank_queries(goal: str, queries: List[str]) -> List[str]:
    """Best-performing queries first; unseen queries keep the optimistic prior so
    they still get explored before the engine converges on winners."""
    if not queries:
        return queries
    data = _load()
    g = data["goals"].get(_key(goal), {})
    qstats = g.get("queries") or {}

    def score(q: str) -> float:
        e = qstats.get(q)
        return _smoothed(e) if e else _PRIOR_SCORE
    return sorted(queries, key=score, reverse=True)


def source_performance(goal: str) -> Dict[str, float]:
    data = _load()
    g = data["goals"].get(_key(goal), {})
    return {src: round(_smoothed(e), 3) for src, e in (g.get("sources") or {}).items()}


def aggregate_source_performance() -> Dict[str, Dict[str, Any]]:
    """Cross-goal learned performance per source: {source: {score, leads, gems}}.

    Used by core.source_reliability to blend learned outcomes with the configured
    base reliability — so weights improve as the system accumulates history.
    """
    data = _load()
    merged: Dict[str, Dict[str, Any]] = {}
    for g in data.get("goals", {}).values():
        for src, e in (g.get("sources") or {}).items():
            m = merged.setdefault(src, {"leads": 0, "sum_appeal": 0.0, "gems": 0})
            m["leads"] += e.get("leads", 0)
            m["sum_appeal"] += e.get("sum_appeal", 0.0)
            m["gems"] += e.get("gems", 0)
    out: Dict[str, Dict[str, Any]] = {}
    for src, m in merged.items():
        out[src] = {
            "score": round(_smoothed(m), 3),
            "leads": m["leads"],
            "gems": m["gems"],
        }
    return out


def summary(goal: str) -> Dict[str, Any]:
    data = _load()
    g = data["goals"].get(_key(goal), {})
    qs = g.get("queries") or {}
    best_q = max(qs.items(), key=lambda kv: _smoothed(kv[1]), default=(None, None))
    return {
        "goal": goal,
        "queries_learned": len(qs),
        "total_runs": sum(e.get("runs", 0) for e in qs.values()),
        "total_gems": sum(e.get("gems", 0) for e in qs.values()),
        "best_query": best_q[0],
        "best_query_score": round(_smoothed(best_q[1]), 3) if best_q[1] else None,
        "source_performance": source_performance(goal),
    }

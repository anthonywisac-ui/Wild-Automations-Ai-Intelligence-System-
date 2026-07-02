"""
Source Reliability — Wave 2. Configurable + continuously learning.

Blends a configured base weight (core.domain.SOURCE_RELIABILITY, overridable via
data/source_reliability.json) with LEARNED performance from historical results
(core.signal_memory). The more observations a source accumulates, the more the
learned signal is trusted — so reliability is not a fixed table, it adapts.

    score(source) -> float in [0,1]
    ranked(sources) -> [(source, score, reason)] sorted best-first

Framework-agnostic; degrades gracefully if history is empty (pure config).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core import domain

logger = logging.getLogger(__name__)

_OVERRIDE_FILE = Path(__file__).resolve().parent.parent / "data" / "source_reliability.json"

# Learning-trust ramp: alpha (weight on learned signal) grows with observations.
_MIN_OBS_TO_LEARN = 8       # below this, trust config only
_MAX_ALPHA = 0.6            # cap on how much learned can override config
_OBS_FOR_MAX_ALPHA = 60     # observations at which alpha reaches the cap


def _load_overrides() -> Dict[str, int]:
    try:
        if _OVERRIDE_FILE.exists():
            data = json.loads(_OVERRIDE_FILE.read_text(encoding="utf-8"))
            return {str(k).lower(): int(v) for k, v in (data.get("weights") or {}).items()}
    except Exception as exc:
        logger.warning("source_reliability: override load failed: %s", exc)
    return {}


def _base(source: str, category: str = "") -> float:
    """Configured base reliability in [0,1] (override file wins over the registry)."""
    s = (source or "").lower()
    for key, val in _load_overrides().items():
        if key in s:
            return max(0.0, min(1.0, val / 100.0))
    return domain.reliability_for(source, category) / 100.0


def _alpha(observations: int) -> float:
    if observations < _MIN_OBS_TO_LEARN:
        return 0.0
    frac = min(1.0, (observations - _MIN_OBS_TO_LEARN) / max(1, _OBS_FOR_MAX_ALPHA - _MIN_OBS_TO_LEARN))
    return round(_MAX_ALPHA * frac, 3)


def score(source: str, category: str = "") -> float:
    """Blended reliability in [0,1]: config base, adjusted toward learned outcomes."""
    base = _base(source, category)
    try:
        from core import signal_memory
        perf = signal_memory.aggregate_source_performance()
    except Exception:
        perf = {}
    # match learned stats by substring (sources are tagged e.g. 'instagram_live')
    learned_score, obs = None, 0
    s = (source or "").lower()
    for src, stats in perf.items():
        if s in src.lower() or src.lower() in s or s.split("_")[0] in src.lower():
            learned_score = stats.get("score")
            obs = stats.get("leads", 0)
            break
    if learned_score is None or obs < _MIN_OBS_TO_LEARN:
        blended = base
    else:
        a = _alpha(obs)
        blended = (1 - a) * base + a * float(learned_score)

    # Adaptive: apply the Learning Engine's event-outcome multiplier for this source
    try:
        from core import learning_engine
        mult = learning_engine.weight("source", (source or "").split("_")[0])
        blended *= mult
    except Exception:
        pass
    return round(max(0.0, min(1.0, blended)), 3)


def ranked(sources: List[str], category: str = "") -> List[Tuple[str, float, str]]:
    """Rank sources best-first with a human-readable reason."""
    out: List[Tuple[str, float, str]] = []
    for src in sources:
        sc = score(src, category)
        base = _base(src, category)
        reason = "config" if abs(sc - base) < 1e-6 else f"config {base:.2f} + learned"
        out.append((src, sc, reason))
    out.sort(key=lambda t: t[1], reverse=True)
    return out

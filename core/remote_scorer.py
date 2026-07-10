"""Remote Probability Scorer — 0.0 (onsite) to 1.0 (fully remote)."""
from __future__ import annotations
import re

_STRONG_REMOTE = [
    "fully remote", "100% remote", "work from anywhere",
    "remote-first", "remote first", "distributed team",
    "async-first", "async first", "remote worldwide",
    "globally remote", "remote globally", "location independent",
    "anywhere in the world", "no office required",
]
_WEAK_REMOTE = [
    "remote", "wfh", "work from home", "home based",
    "home-based", "telecommute", "virtual position",
]
_HYBRID = [
    "hybrid", "flexible", "2 days", "3 days", "4 days",
    "occasionally remote", "partially remote",
]
_ONSITE = [
    "on-site", "onsite", "on site", "in-office", "in office",
    "must be in", "relocation required", "must relocate",
    "required to be on", "physically present", "office based",
    "office-based", "no remote", "not remote",
]
_GLOBAL_LOCS = [
    "worldwide", "global", "anywhere", "earth",
    "international", "all countries", "any country",
]


def remote_score(title: str, location: str, description: str) -> float:
    """Returns 0.0–1.0 remote probability."""
    text = f"{title} {location} {description}".lower()
    loc_lower = location.lower()

    # Strong onsite signals kill remote probability
    if any(p in text for p in _ONSITE):
        # but hybrid still possible
        if any(p in text for p in _HYBRID):
            return 0.35
        return 0.05

    # Strong remote signals
    if any(p in text for p in _STRONG_REMOTE):
        return 0.95

    # Location explicitly says Remote
    if "remote" in loc_lower:
        return 0.90

    # Global location hints
    if any(g in loc_lower for g in _GLOBAL_LOCS):
        return 0.85

    # Hybrid
    if any(p in text for p in _HYBRID):
        return 0.40

    # Weak remote signals
    if any(p in text for p in _WEAK_REMOTE):
        return 0.70

    # No signals — assume onsite
    return 0.15


def remote_label(score: float) -> str:
    if score >= 0.80:
        return "Remote"
    if score >= 0.50:
        return "Hybrid"
    if score >= 0.30:
        return "Flexible"
    return "On-site"

"""
Negative-Keyword Generator — Search Planning layer.

For a service, derives the seller/provider terms that must be EXCLUDED so the
retrieval layer targets buyers, not competitors. Sources: blueprint
`negative_keywords` + a universal seller-term set + the service's own tokens
(a business searching for its own service name is almost always a provider).

Deterministic, framework-agnostic.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List, Set

logger = logging.getLogger(__name__)

_BLUEPRINTS = Path(__file__).resolve().parent.parent / "data" / "niche_blueprints.json"

# Universal provider/seller markers (never a buyer expressing a need).
UNIVERSAL_SELLER_TERMS: Set[str] = {
    "agency", "agencies", "vendor", "supplier", "consultant", "consultancy",
    "freelancer", "provider", "company", "services", "solutions", "studio",
    "we offer", "we provide", "our services", "our platform", "our software",
    "hire us", "get a quote", "book a demo", "contact us for", "smma",
    "reseller", "white label", "outsource", "outsourcing",
}

# Service words that identify a PROVIDER when searched directly.
_SERVICE_MARKERS = ("marketing", "seo", "social media", "advertising", "ads",
                    "web design", "branding", "software", "crm", "automation")


def _blueprint_negatives(service: str) -> List[str]:
    try:
        bps = json.loads(_BLUEPRINTS.read_text(encoding="utf-8")).get("blueprints", {})
        g = service.lower()
        for bp in bps.values():
            if any(kw in g for kw in bp.get("match", [])):
                return bp.get("negative_keywords", [])
    except Exception as exc:
        logger.warning("negative_keywords: blueprint read failed: %s", exc)
    return []


def _service_tokens(service: str) -> List[str]:
    """Meaningful service tokens (a lead should not be found by these alone)."""
    toks = re.findall(r"[a-z]+", (service or "").lower())
    stop = {"for", "my", "the", "a", "an", "clients", "client", "leads", "business", "of", "and"}
    return [t for t in toks if t not in stop and len(t) > 2]


def for_service(service: str) -> List[str]:
    """Full negative-keyword list for a service (blueprint + universal + service tokens)."""
    negs: Set[str] = set(UNIVERSAL_SELLER_TERMS)
    negs.update(k.lower() for k in _blueprint_negatives(service))
    # include the service's own defining markers (searching them → providers)
    g = (service or "").lower()
    for marker in _SERVICE_MARKERS:
        if marker in g:
            negs.add(marker)
    return sorted(negs)


def google_exclusions(service: str, limit: int = 8) -> str:
    """Google `-term` exclusion suffix for a query (single tokens only)."""
    singles = [n for n in for_service(service) if " " not in n][:limit]
    return " ".join(f"-{t}" for t in singles)

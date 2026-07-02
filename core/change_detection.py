"""
Change Detection Engine — turns the platform from a static scraper into a
continuous AI Sales Intelligence system.

On re-enrichment it diffs the new enrichment against the cached snapshot and
emits ONLY the changes (new reviews, website update, new hiring, new branch,
Meta Pixel added, WhatsApp added, social activated, SEO improved, booking/chatbot
added) as events onto the Event Timeline (the CRM source of truth). Nothing is
sent when nothing changed.

Framework-agnostic, fail-soft.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def detect(old: Dict[str, Any], new: Dict[str, Any],
           review_count_old: Optional[int] = None,
           review_count_new: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return the list of meaningful changes between two enrichment snapshots."""
    changes: List[Dict[str, Any]] = []
    old = old or {}
    new = new or {}
    old_tech = old.get("tech") or {}
    new_tech = new.get("tech") or {}

    def added(field):
        return bool(new.get(field)) and not bool(old.get(field))

    if review_count_old and review_count_new and review_count_new > review_count_old:
        changes.append({"type": "new_reviews", "from": review_count_old, "to": review_count_new})
    if added("website"):
        changes.append({"type": "website_added", "value": new.get("website")})
    elif old.get("website") and new.get("website") and old.get("website") != new.get("website"):
        changes.append({"type": "website_changed", "from": old.get("website"), "to": new.get("website")})
    if added("whatsapp"):
        changes.append({"type": "whatsapp_added"})
    if added("booking_system"):
        changes.append({"type": "booking_added", "value": new.get("booking_system")})
    if added("chatbot"):
        changes.append({"type": "chatbot_added", "value": new.get("chatbot")})
    if added("hiring"):
        changes.append({"type": "new_hiring"})
    if new_tech.get("meta_pixel") and not old_tech.get("meta_pixel"):
        changes.append({"type": "meta_pixel_added"})
    if new_tech.get("google_analytics") and not old_tech.get("google_analytics"):
        changes.append({"type": "analytics_added"})
    new_socials = set(new.get("socials") or {}) - set(old.get("socials") or {})
    if new_socials:
        changes.append({"type": "social_activated", "platforms": sorted(new_socials)})
    # SEO improvement
    old_seo, new_seo = old.get("seo") or {}, new.get("seo") or {}
    improved = [k for k in ("has_meta_desc", "mobile_viewport", "https")
                if new_seo.get(k) and not old_seo.get(k)]
    if improved:
        changes.append({"type": "seo_improved", "fields": improved})
    return changes


# change type → Event Timeline event
_EVENT_MAP = {
    "new_reviews": "review",
    "website_added": "website_change", "website_changed": "website_change",
    "whatsapp_added": "technology_change", "booking_added": "technology_change",
    "chatbot_added": "technology_change", "meta_pixel_added": "technology_change",
    "analytics_added": "technology_change", "social_activated": "technology_change",
    "seo_improved": "website_change", "new_hiring": "hiring",
}


def emit(changes: List[Dict[str, Any]], *, canonical_id: str = "",
         business_key: str = "") -> int:
    """Record changes as events on the Event Timeline (CRM). Returns count."""
    if not changes:
        return 0
    try:
        from core import event_timeline
        from core.event_timeline import EventType
    except Exception as exc:
        logger.warning("change_detection: event timeline unavailable: %s", exc)
        return 0
    n = 0
    for ch in changes:
        try:
            et = EventType(_EVENT_MAP.get(ch["type"], "technology_change"))
            event_timeline.record(et, canonical_id=canonical_id,
                                  payload={**ch, "business_key": business_key, "detected_change": True})
            n += 1
        except Exception:
            continue
    return n

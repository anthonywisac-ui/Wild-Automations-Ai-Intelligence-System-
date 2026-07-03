"""
Concierge Delivery — format matched results and send them to the user.

Self-contained sender (WHAPI first, Meta Cloud fallback) driven purely by env
vars — no DeliveryEngine config wiring needed:

    WHAPI_API_KEY                          -> WhatsApp via whapi.cloud
    META_ACCESS_TOKEN + META_PHONE_NUMBER_ID -> WhatsApp via Meta Cloud API
    NOTIFY_TO                              -> default recipient

Best-effort: returns a status dict, never raises into the pipeline.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_WHAPI_BASE = os.getenv("WHAPI_BASE_URL", "https://api.whapi.cloud")
_META_BASE = "https://graph.facebook.com/v19.0"


def _default_to() -> str:
    return (os.getenv("NOTIFY_TO") or "").strip()


def channels_available() -> Dict[str, bool]:
    return {
        "whapi": bool(os.getenv("WHAPI_API_KEY")),
        "meta": bool(os.getenv("META_ACCESS_TOKEN") and os.getenv("META_PHONE_NUMBER_ID")),
        "recipient_set": bool(_default_to()),
    }


def format_matches(persona: str, requirement: Dict[str, Any],
                   matches: List[Dict[str, Any]], limit: int = 5) -> str:
    """Build a concise WhatsApp-friendly message from the top matches."""
    icons = {"student": "🎓", "job_seeker": "💼", "travel_agent": "✈️", "car_dealer": "🚗"}
    title = {"student": "Admission matches", "job_seeker": "Job matches",
             "travel_agent": "Visa routes", "car_dealer": "Car listings"}.get(persona, "Matches")
    want = ", ".join(f"{k}: {v}" for k, v in (requirement or {}).items() if v and k != "cv_text")
    lines = [f"{icons.get(persona,'🔎')} *Wild Automations — {title}*"]
    if want:
        lines.append(f"_For: {want}_")
    lines.append("")
    for i, m in enumerate(matches[:limit], 1):
        md = m.get("metadata") or {}
        name = (m.get("title") or "").strip()[:80]
        loc = m.get("location") or md.get("country") or ""
        url = m.get("source_url") or ""
        score = m.get("_match_score")
        extra = f" · {int(score*100)}% match" if isinstance(score, (int, float)) else ""
        lines.append(f"{i}. *{name}*")
        if loc:
            lines.append(f"   📍 {loc}{extra}")
        if url:
            lines.append(f"   🔗 {url}")
    if not matches:
        lines.append("No strong matches this run — try widening the criteria.")
    return "\n".join(lines)


async def send_whatsapp(message: str, to: Optional[str] = None) -> Dict[str, Any]:
    """Send one WhatsApp message. WHAPI first, Meta fallback. Best-effort."""
    to = (to or _default_to()).strip()
    if not to:
        return {"sent": False, "reason": "no recipient (set NOTIFY_TO or pass 'to')"}

    whapi_key = os.getenv("WHAPI_API_KEY")
    if whapi_key:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    f"{_WHAPI_BASE}/messages",
                    headers={"Authorization": f"Bearer {whapi_key}",
                             "Content-Type": "application/json"},
                    json={"to": to, "body": message, "type": "text"})
                if r.status_code < 300:
                    d = r.json()
                    return {"sent": True, "channel": "whapi",
                            "message_id": d.get("id") or d.get("message_id")}
                logger.warning("whapi send %s: %s", r.status_code, r.text[:200])
        except Exception as exc:
            logger.warning("whapi send error: %s", exc)

    token, phone_id = os.getenv("META_ACCESS_TOKEN"), os.getenv("META_PHONE_NUMBER_ID")
    if token and phone_id:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    f"{_META_BASE}/{phone_id}/messages",
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json"},
                    json={"messaging_product": "whatsapp", "recipient_type": "individual",
                          "to": to.lstrip("+"), "type": "text", "text": {"body": message}})
                if r.status_code < 300:
                    return {"sent": True, "channel": "meta"}
                logger.warning("meta send %s: %s", r.status_code, r.text[:200])
        except Exception as exc:
            logger.warning("meta send error: %s", exc)

    return {"sent": False, "reason": "no WhatsApp channel configured (WHAPI_API_KEY or META_*)"}


async def deliver_matches(persona: str, requirement: Dict[str, Any],
                          matches: List[Dict[str, Any]], to: Optional[str] = None
                          ) -> Dict[str, Any]:
    """Format the top matches and send them over WhatsApp."""
    text = format_matches(persona, requirement, matches)
    result = await send_whatsapp(text, to)
    result["preview"] = text[:600]
    return result

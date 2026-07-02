"""
Notification Delivery — multi-channel dispatch (WhatsApp, email, push, web).
Documented in: docs/NOTIFICATION ENGINE.md § 3.1

Wires into the existing core/delivery_engine.py for WhatsApp.
Other channels (email, push, web) are logged as stubs until provider keys added.

Usage:
    from delivery.notification_delivery import NotificationDelivery
    nd = NotificationDelivery(whatsapp_engine=delivery_engine_instance)
    ok = await nd.deliver({
        "user_id": "+923351021321",
        "user_phone": "+923351021321",
        "title": "New Job Alert",
        "message": "Senior Dev at Careem — Dubai",
        "opportunity_id": "abc123",
        "channels": ["whatsapp"],
    })
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from delivery.templates import NotificationTemplates

logger = logging.getLogger(__name__)


class NotificationDelivery:
    """
    Multi-channel notification dispatcher.
    whatsapp_engine: existing core.delivery_engine.DeliveryEngine instance (optional).
    """

    def __init__(self, whatsapp_engine=None) -> None:
        self._wa = whatsapp_engine
        self._templates = NotificationTemplates()
        self._delivery_log: List[Dict[str, Any]] = []

    # ──────────────────────────────────────────────────────────────────────────
    # Main dispatch
    # ──────────────────────────────────────────────────────────────────────────

    async def deliver(self, notification: Dict[str, Any]) -> bool:
        """
        Route notification to all requested channels.
        notification keys:
            user_id, user_phone, user_email (optional),
            title, message,
            opportunity_id (optional),
            channels: list of "whatsapp" | "email" | "push" | "web"
        Returns True if at least one channel succeeded.
        """
        channels = notification.get("channels") or self._default_channels(notification)
        formatted = self._format_messages(notification, channels)

        results = await asyncio.gather(
            *[self._deliver_channel(ch, msg, notification) for ch, msg in formatted.items()],
            return_exceptions=True,
        )

        successes = [r for r in results if r is True]
        self._track(notification, channels, len(successes))
        return bool(successes)

    # ──────────────────────────────────────────────────────────────────────────
    # Per-channel formatters
    # ──────────────────────────────────────────────────────────────────────────

    def _default_channels(self, notification: Dict) -> List[str]:
        channels = []
        if notification.get("user_phone"):
            channels.append("whatsapp")
        if notification.get("user_email"):
            channels.append("email")
        return channels or ["whatsapp"]

    def _format_messages(
        self, notification: Dict[str, Any], channels: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        out = {}
        for ch in channels:
            if ch == "whatsapp":
                out[ch] = self._format_whatsapp(notification)
            elif ch == "email":
                out[ch] = self._format_email(notification)
            elif ch == "web":
                out[ch] = self._format_web(notification)
            elif ch == "push":
                out[ch] = self._format_push(notification)
        return out

    def _format_whatsapp(self, n: Dict) -> Dict:
        return {
            "to": n.get("user_phone") or n.get("user_id"),
            "message": n.get("message") or n.get("title", ""),
            "opportunity_id": n.get("opportunity_id"),
        }

    def _format_email(self, n: Dict) -> Dict:
        return {
            "to": n.get("user_email"),
            "subject": n.get("title", "New Opportunity Alert"),
            "body": n.get("message", ""),
        }

    def _format_web(self, n: Dict) -> Dict:
        return {
            "user_id": n.get("user_id"),
            "title": n.get("title", "New Alert"),
            "message": n.get("message", ""),
            "url": f"/opportunities/{n.get('opportunity_id', '')}",
            "icon": "🔔",
        }

    def _format_push(self, n: Dict) -> Dict:
        return {
            "title": n.get("title", "New Opportunity"),
            "body": n.get("message", ""),
            "data": {"opportunity_id": n.get("opportunity_id"), "type": "opportunity_alert"},
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Delivery per channel
    # ──────────────────────────────────────────────────────────────────────────

    async def _deliver_channel(
        self, channel: str, message: Dict[str, Any], original: Dict[str, Any]
    ) -> bool:
        try:
            if channel == "whatsapp":
                return await self._send_whatsapp(message, original)
            elif channel == "email":
                return await self._send_email(message)
            elif channel in ("web", "push"):
                logger.info("notification_delivery: %s stub — message=%s", channel, message)
                return True
            else:
                logger.warning("notification_delivery: unknown channel %s", channel)
                return False
        except Exception as exc:
            logger.error("notification_delivery: channel=%s error=%s", channel, exc)
            return False

    async def _send_whatsapp(self, message: Dict, original: Dict) -> bool:
        if not self._wa:
            logger.warning("notification_delivery: no WhatsApp engine configured")
            return False
        to = message.get("to")
        text = message.get("message", "")
        if not to or not text:
            return False
        region = original.get("region", "")
        metadata = original.get("metadata", {})
        await self._wa.send(to=to, message=text, region=region, metadata=metadata)
        logger.info("notification_delivery: whatsapp sent to=%s", to)
        return True

    async def _send_email(self, message: Dict) -> bool:
        # Stub — wire SMTP/SendGrid here when ready
        logger.info("notification_delivery: email stub to=%s subject=%s", message.get("to"), message.get("subject"))
        return True

    # ──────────────────────────────────────────────────────────────────────────
    # Tracking
    # ──────────────────────────────────────────────────────────────────────────

    def _track(self, notification: Dict, channels: List[str], success_count: int) -> None:
        self._delivery_log.append({
            "user_id": notification.get("user_id"),
            "channels": channels,
            "success_count": success_count,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # keep last 1000 entries in memory
        if len(self._delivery_log) > 1000:
            self._delivery_log = self._delivery_log[-1000:]

    def delivery_stats(self) -> Dict[str, Any]:
        total = len(self._delivery_log)
        successes = sum(1 for e in self._delivery_log if e["success_count"] > 0)
        return {
            "total_attempts": total,
            "successful": successes,
            "failed": total - successes,
        }

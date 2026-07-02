"""
Notification Scheduler — queues immediate / scheduled / daily-summary notifications.
Documented in: docs/NOTIFICATION ENGINE.md § 4

No external queue needed — uses asyncio.Queue internally.
Persist to Supabase via database_layer if db injected.

Usage:
    from delivery.scheduler import NotificationScheduler
    from delivery.notification_delivery import NotificationDelivery

    nd = NotificationDelivery(whatsapp_engine=wa)
    sched = NotificationScheduler(delivery=nd)
    asyncio.create_task(sched.run())          # start background worker

    # Immediate notify
    await sched.schedule(user_id="+923...", message="Job found!", channels=["whatsapp"])

    # Daily summary (runs once/day if start_daily_job called)
    asyncio.create_task(sched.start_daily_summary(hour=8))
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VALID_TYPES = ("immediate", "scheduled", "daily_summary", "weekly_summary")


class NotificationScheduler:

    def __init__(self, delivery=None, db=None) -> None:
        self._delivery = delivery  # NotificationDelivery instance
        self._db = db              # optional SupabaseDB for persistence
        self._queue: asyncio.Queue = asyncio.Queue()
        self._pending: List[Dict[str, Any]] = []  # scheduled (non-immediate) items
        self._running = False

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    async def schedule(
        self,
        user_id: str,
        message: str,
        title: str = "New Opportunity",
        channels: Optional[List[str]] = None,
        schedule_type: str = "immediate",
        scheduled_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Enqueue a notification.
        schedule_type: immediate | scheduled | daily_summary | weekly_summary
        """
        if schedule_type not in VALID_TYPES:
            raise ValueError(f"Invalid schedule_type: {schedule_type}. Valid: {VALID_TYPES}")

        entry: Dict[str, Any] = {
            "user_id": user_id,
            "user_phone": user_id,
            "title": title,
            "message": message,
            "channels": channels or ["whatsapp"],
            "type": schedule_type,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "scheduled_at": (scheduled_at or datetime.utcnow()).isoformat(),
            "metadata": metadata or {},
        }

        if schedule_type == "immediate":
            await self._queue.put(entry)
            entry["status"] = "queued"
            logger.info("scheduler: immediate queued user=%s", user_id)
        else:
            self._pending.append(entry)
            logger.info("scheduler: %s scheduled user=%s at=%s", schedule_type, user_id, entry["scheduled_at"])

        return entry

    async def run(self) -> None:
        """Background worker — process immediate queue + check scheduled items."""
        self._running = True
        logger.info("scheduler: worker started")
        while self._running:
            # Drain immediate queue
            try:
                entry = self._queue.get_nowait()
                await self._dispatch(entry)
                self._queue.task_done()
            except asyncio.QueueEmpty:
                pass

            # Check scheduled items
            await self._process_scheduled()

            await asyncio.sleep(30)  # tick every 30s

    def stop(self) -> None:
        self._running = False

    # ──────────────────────────────────────────────────────────────────────────
    # Daily / Weekly summary jobs
    # ──────────────────────────────────────────────────────────────────────────

    async def start_daily_summary(
        self,
        recipients: List[str],
        get_summary_fn,
        hour: int = 8,
    ) -> None:
        """
        Infinite loop — fires get_summary_fn(user_id) → dict each day at `hour` UTC.
        get_summary_fn must return {"total": int, "new": int, "match_rate": int, "top_opportunities": str}
        """
        logger.info("scheduler: daily_summary job started for %d recipients at %02d:00 UTC", len(recipients), hour)
        while True:
            now = datetime.utcnow()
            next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            wait_secs = (next_run - now).total_seconds()
            logger.info("scheduler: daily_summary next run in %.0f seconds", wait_secs)
            await asyncio.sleep(wait_secs)

            for user_id in recipients:
                try:
                    summary_data = await get_summary_fn(user_id)
                    from delivery.templates import NotificationTemplates
                    t = NotificationTemplates()
                    msg = t.render("whatsapp", "daily_summary", {
                        "date": datetime.utcnow().strftime("%Y-%m-%d"),
                        **summary_data,
                    })
                    await self.schedule(
                        user_id=user_id,
                        message=msg,
                        title="Daily Summary",
                        schedule_type="immediate",
                    )
                except Exception as exc:
                    logger.error("scheduler: daily_summary failed user=%s: %s", user_id, exc)

    # ──────────────────────────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────────────────────────

    async def _process_scheduled(self) -> None:
        now = datetime.utcnow()
        due = [e for e in self._pending if datetime.fromisoformat(e["scheduled_at"]) <= now and e["status"] == "pending"]
        for entry in due:
            await self._dispatch(entry)
            entry["status"] = "done"
        # Remove completed
        self._pending = [e for e in self._pending if e["status"] == "pending"]

    async def _dispatch(self, entry: Dict[str, Any]) -> None:
        if not self._delivery:
            logger.warning("scheduler: no delivery engine configured — dropping message user=%s", entry.get("user_id"))
            return
        try:
            ok = await self._delivery.deliver(entry)
            entry["status"] = "sent" if ok else "failed"
            entry["executed_at"] = datetime.utcnow().isoformat()
        except Exception as exc:
            logger.error("scheduler: dispatch failed user=%s: %s", entry.get("user_id"), exc)
            entry["status"] = "failed"

    def queue_size(self) -> int:
        return self._queue.qsize()

    def pending_count(self) -> int:
        return len([e for e in self._pending if e["status"] == "pending"])

"""
WhatsApp Session Manager — per-user conversation state.
Documented in: docs/WHATSAPP AI ARCHITECTURE.md § 3.1

In-memory by default; Redis supported via injected cache_service.

Usage:
    from whatsapp.session_manager import SessionManager
    mgr = SessionManager(cache_service=None)  # in-memory
    session = await mgr.get_session(user_id)
    session.add_message("user", "find jobs in Dubai")
    await mgr.save_session(session)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class Session:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.messages: List[Dict] = []
        self.context: Dict = {}
        self.filters: Dict = {}
        self.saved_searches: List[Dict] = []
        self.last_activity: datetime = datetime.utcnow()
        self.state: str = "idle"
        self.intent_history: List[str] = []

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]
        self.last_activity = datetime.utcnow()

    def update_filters(self, filters: Dict) -> None:
        self.filters.update(filters)

    def get_filters(self) -> Dict:
        return self.filters

    def get_context(self) -> Dict:
        return {
            "messages": self.messages[-10:],
            "filters": self.filters,
            "saved_searches": self.saved_searches[-5:],
            "state": self.state,
            "intent_history": self.intent_history[-5:],
        }

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        elapsed = (datetime.utcnow() - self.last_activity).total_seconds() / 60
        return elapsed > timeout_minutes


class SessionManager:
    def __init__(self, cache_service=None, timeout_minutes: int = 30) -> None:
        self._cache = cache_service
        self._sessions: Dict[str, Session] = {}
        self.timeout_minutes = timeout_minutes

    async def get_session(self, user_id: str) -> Session:
        # Check in-memory
        if user_id in self._sessions:
            session = self._sessions[user_id]
            if not session.is_expired(self.timeout_minutes):
                return session

        # Check Redis if available
        if self._cache:
            try:
                data = await self._cache.get(f"whatsapp_session:{user_id}")
                if data:
                    session = self._deserialize(data if isinstance(data, dict) else json.loads(data))
                    self._sessions[user_id] = session
                    return session
            except Exception as exc:
                logger.warning("session_manager: redis get failed: %s", exc)

        session = Session(user_id)
        self._sessions[user_id] = session
        await self._persist(user_id, session)
        return session

    async def save_session(self, session: Session) -> None:
        self._sessions[session.user_id] = session
        await self._persist(session.user_id, session)

    async def clear_session(self, user_id: str) -> None:
        self._sessions.pop(user_id, None)
        if self._cache:
            try:
                await self._cache.delete(f"whatsapp_session:{user_id}")
            except Exception as exc:
                logger.warning("session_manager: redis delete failed: %s", exc)

    def active_sessions(self) -> int:
        return len([s for s in self._sessions.values() if not s.is_expired(self.timeout_minutes)])

    # ──────────────────────────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────────────────────────

    async def _persist(self, user_id: str, session: Session) -> None:
        if not self._cache:
            return
        try:
            data = self._serialize(session)
            await self._cache.set(
                f"whatsapp_session:{user_id}",
                json.dumps(data),
                ttl=self.timeout_minutes * 60,
            )
        except Exception as exc:
            logger.warning("session_manager: redis set failed: %s", exc)

    def _serialize(self, session: Session) -> Dict[str, Any]:
        return {
            "user_id": session.user_id,
            "messages": session.messages,
            "context": session.context,
            "filters": session.filters,
            "saved_searches": session.saved_searches,
            "last_activity": session.last_activity.isoformat(),
            "state": session.state,
            "intent_history": session.intent_history,
        }

    def _deserialize(self, data: Dict[str, Any]) -> Session:
        session = Session(data["user_id"])
        session.messages = data.get("messages", [])
        session.context = data.get("context", {})
        session.filters = data.get("filters", {})
        session.saved_searches = data.get("saved_searches", [])
        session.last_activity = datetime.fromisoformat(data["last_activity"])
        session.state = data.get("state", "idle")
        session.intent_history = data.get("intent_history", [])
        return session

"""
Conversation Context Manager — per-user in-memory session with optional Redis persistence.
Documented in: docs/AI ARCHITECTURE.md § 2.2

No Redis dependency required — works in-memory only. Redis layer is wired in if
a cache_service is injected (must implement async get/set methods).

Usage:
    from context_manager import ContextManager
    mgr = ContextManager()
    ctx = await mgr.get_context("+923351021321")
    ctx.add_message("user", "find jobs in Dubai")
    await mgr.update_context("+923351021321", ctx)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Max items kept per list to avoid unbounded memory growth
_MAX_MESSAGES = 50
_MAX_INTENTS = 20
_MAX_SEARCHES = 50
_TIMEOUT_MINUTES = 30


class ConversationContext:
    """Holds full conversation state for one user."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.messages: List[Dict[str, Any]] = []
        self.intent_history: List[Dict[str, Any]] = []
        self.current_intent: Optional[str] = None
        self.entities: Dict[str, Any] = {}
        self.last_activity: datetime = datetime.utcnow()
        self.search_history: List[Dict[str, Any]] = []
        self.preferences: Dict[str, Any] = {}
        self.filters: Dict[str, Any] = {}

    # ── Mutators ──────────────────────────────────────────────────────────────

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        })
        if len(self.messages) > _MAX_MESSAGES:
            self.messages = self.messages[-_MAX_MESSAGES:]
        self.last_activity = datetime.utcnow()

    def add_intent(self, intent: Dict[str, Any]) -> None:
        self.intent_history.append({
            **intent,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.current_intent = intent.get("intent")
        self.entities.update(intent.get("entities", {}))
        if len(self.intent_history) > _MAX_INTENTS:
            self.intent_history = self.intent_history[-_MAX_INTENTS:]

    def add_search(self, query: str, results_count: int) -> None:
        self.search_history.append({
            "query": query,
            "results_count": results_count,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(self.search_history) > _MAX_SEARCHES:
            self.search_history = self.search_history[-_MAX_SEARCHES:]

    def update_filters(self, filters: Dict[str, Any]) -> None:
        self.filters.update(filters)

    def get_filters(self) -> Dict[str, Any]:
        return dict(self.filters)

    # ── Readers ───────────────────────────────────────────────────────────────

    def get_context(self) -> str:
        """Compact string for AI prompt injection."""
        parts = []
        if self.preferences:
            parts.append(f"Preferences: {self.preferences}")
        if self.intent_history:
            parts.append(f"Recent intents: {self.intent_history[-3:]}")
        if self.entities:
            parts.append(f"Known entities: {self.entities}")
        if self.search_history:
            parts.append(f"Recent searches: {self.search_history[-3:]}")
        if self.messages:
            parts.append(f"Last messages: {self.messages[-5:]}")
        return "\n".join(parts)

    def is_expired(self, timeout_minutes: int = _TIMEOUT_MINUTES) -> bool:
        elapsed = (datetime.utcnow() - self.last_activity).total_seconds() / 60
        return elapsed > timeout_minutes

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "messages": self.messages,
            "intent_history": self.intent_history,
            "current_intent": self.current_intent,
            "entities": self.entities,
            "last_activity": self.last_activity.isoformat(),
            "search_history": self.search_history,
            "preferences": self.preferences,
            "filters": self.filters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContext":
        ctx = cls(data["user_id"])
        ctx.messages = data.get("messages", [])
        ctx.intent_history = data.get("intent_history", [])
        ctx.current_intent = data.get("current_intent")
        ctx.entities = data.get("entities", {})
        ctx.last_activity = datetime.fromisoformat(data.get("last_activity", datetime.utcnow().isoformat()))
        ctx.search_history = data.get("search_history", [])
        ctx.preferences = data.get("preferences", {})
        ctx.filters = data.get("filters", {})
        return ctx


class ContextManager:
    """
    Get/update/expire per-user ConversationContext.
    Works purely in-memory. Optionally persists to Redis if cache_service injected.
    cache_service must implement:  async get(key) -> Optional[dict]
                                   async set(key, value, ttl=int) -> None
    """

    def __init__(self, cache_service=None, timeout_minutes: int = _TIMEOUT_MINUTES) -> None:
        self._cache_service = cache_service
        self._contexts: Dict[str, ConversationContext] = {}
        self.timeout_minutes = timeout_minutes

    async def get_context(self, user_id: str) -> ConversationContext:
        # 1. In-memory hit
        if user_id in self._contexts:
            ctx = self._contexts[user_id]
            if not ctx.is_expired(self.timeout_minutes):
                return ctx

        # 2. Redis hit
        if self._cache_service:
            try:
                data = await self._cache_service.get(f"ctx:{user_id}")
                if data:
                    ctx = ConversationContext.from_dict(data)
                    self._contexts[user_id] = ctx
                    return ctx
            except Exception as exc:
                logger.warning("context_manager: redis get failed user=%s: %s", user_id, exc)

        # 3. Fresh context
        ctx = ConversationContext(user_id)
        self._contexts[user_id] = ctx
        return ctx

    async def update_context(self, user_id: str, ctx: ConversationContext) -> None:
        self._contexts[user_id] = ctx
        if self._cache_service:
            try:
                await self._cache_service.set(
                    f"ctx:{user_id}",
                    ctx.to_dict(),
                    ttl=self.timeout_minutes * 60,
                )
            except Exception as exc:
                logger.warning("context_manager: redis set failed user=%s: %s", user_id, exc)

    def clear_context(self, user_id: str) -> None:
        self._contexts.pop(user_id, None)

    def active_sessions(self) -> int:
        return sum(1 for ctx in self._contexts.values() if not ctx.is_expired(self.timeout_minutes))

# Inspired By: Event dispatcher pattern
# Feature: Event dispatcher
# Reason: Route events to handlers
# ============================================================

import asyncio
from typing import List, Dict, Type, Optional
import logging
from ..interfaces import Event, EventHandler, EventDispatcher as IEventDispatcher

logger = logging.getLogger(__name__)

class EventDispatcher(IEventDispatcher):
    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}

    def register(self, handler: EventHandler) -> None:
        for event_type in handler.event_types:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            logger.info("Registered handler %s for event %s", handler.__class__.__name__, event_type)

    def unregister(self, handler: EventHandler) -> None:
        for event_type in handler.event_types:
            if event_type in self._handlers:
                self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]
                if not self._handlers[event_type]:
                    del self._handlers[event_type]

    async def dispatch(self, event: Event) -> None:
        event_type = event.event_type
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug("No handlers for event %s", event_type)
            return
        logger.info("Dispatching event %s to %d handlers", event_type, len(handlers))
        tasks = [self._safe_handle(handler, event) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_handle(self, handler: EventHandler, event: Event) -> None:
        try:
            await handler.handle(event)
        except Exception as e:
            logger.exception("Handler %s failed for event %s", handler.__class__.__name__, event.event_type)

_dispatcher: Optional[EventDispatcher] = None

def get_event_dispatcher() -> EventDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = EventDispatcher()
    return _dispatcher

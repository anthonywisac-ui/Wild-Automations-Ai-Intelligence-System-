# Inspired By: TADD event-driven architecture
# Feature: Plugin event emitter
# Reason: Allow plugins to emit and subscribe to events
# ============================================================

from typing import Dict, Any, Callable, Awaitable, List
import asyncio
from collections import defaultdict
import logging
from ..interfaces import Event

logger = logging.getLogger(__name__)

class PluginEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[[Event], Awaitable[None]]]] = defaultdict(list)

    def on(self, event_type: str, listener: Callable[[Event], Awaitable[None]]) -> None:
        self._listeners[event_type].append(listener)

    def off(self, event_type: str, listener: Callable[[Event], Awaitable[None]]) -> None:
        if event_type in self._listeners:
            self._listeners[event_type] = [l for l in self._listeners[event_type] if l != listener]

    async def emit(self, event: Event) -> None:
        event_type = event.event_type
        listeners = self._listeners.get(event_type, [])
        if not listeners:
            return
        tasks = [listener(event) for listener in listeners]
        await asyncio.gather(*tasks, return_exceptions=True)

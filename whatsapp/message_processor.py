"""
WhatsApp Message Processor — routes detected intents to handlers.
Documented in: docs/WHATSAPP AI ARCHITECTURE.md § 2.3

Connects IntentDetector → domain handlers → ResponseGenerator.
Wires into existing core/database_layer.py for search/save.

Usage:
    from whatsapp.message_processor import MessageProcessor
    processor = MessageProcessor(db=db_layer, response_gen=gen, session_mgr=mgr)
    response = await processor.process(user_id, "+923351021321", "find jobs in Dubai")
"""

import logging
from typing import Any, Dict, List, Optional

from whatsapp.intent_detector import IntentDetector
from whatsapp.response_generator import ResponseGenerator
from whatsapp.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Simple keyword domain mapper
_DOMAIN_HINTS = {
    "jobs": ["job", "work", "career", "employment", "hiring", "vacancy", "vacancies", "position"],
    "real_estate": ["property", "apartment", "villa", "flat", "rent", "buy", "house", "studio", "room"],
    "vehicles": ["car", "truck", "suv", "vehicle", "auto", "motorbike", "bike"],
}


def _guess_domain(text: str) -> str:
    t = text.lower()
    for domain, kws in _DOMAIN_HINTS.items():
        if any(kw in t for kw in kws):
            return domain
    return "jobs"  # default


class MessageProcessor:
    def __init__(
        self,
        db=None,
        response_gen: Optional[ResponseGenerator] = None,
        session_mgr: Optional[SessionManager] = None,
        intent_detector: Optional[IntentDetector] = None,
    ) -> None:
        self._db = db
        self._gen = response_gen or ResponseGenerator()
        self._sessions = session_mgr or SessionManager()
        self._detector = intent_detector or IntentDetector()

    # ──────────────────────────────────────────────────────────────────────────
    # Entry point
    # ──────────────────────────────────────────────────────────────────────────

    async def process(
        self, user_id: str, phone: str, text: str
    ) -> Dict[str, Any]:
        """
        Full pipeline:
        1. Get/create session
        2. Detect intent
        3. Route to handler
        4. Update session
        5. Return response dict
        """
        session = await self._sessions.get_session(user_id)
        session.add_message("user", text)

        try:
            intent = await self._detector.detect_intent(text, session.get_context())
            session.intent_history.append(intent["intent"])

            response = await self._route(user_id, phone, text, intent, session)

        except Exception as exc:
            logger.error("message_processor: error user=%s: %s", user_id, exc)
            response = await self._gen.generate_error_response()

        session.add_message("assistant", response.get("text", ""))
        await self._sessions.save_session(session)
        return response

    # ──────────────────────────────────────────────────────────────────────────
    # Intent routing
    # ──────────────────────────────────────────────────────────────────────────

    async def _route(
        self, user_id: str, phone: str, text: str, intent: Dict, session: Any
    ) -> Dict[str, Any]:
        itype = intent.get("intent", "general")

        if itype == "search":
            return await self._handle_search(user_id, text, intent, session)
        elif itype == "filter":
            return await self._handle_filter(user_id, text, intent, session)
        elif itype == "save":
            return await self._handle_save(user_id, text, intent, session)
        elif itype == "view":
            return await self._handle_view(user_id, text, intent)
        elif itype in ("help", "general"):
            return await self._gen.generate_help_response()
        elif itype == "my_saves":
            return await self._handle_my_saves(user_id)
        elif itype == "notify":
            return await self._handle_notify(user_id, text, session)
        else:
            return await self._gen.generate_help_response()

    # ──────────────────────────────────────────────────────────────────────────
    # Handlers
    # ──────────────────────────────────────────────────────────────────────────

    async def _handle_search(
        self, user_id: str, text: str, intent: Dict, session: Any
    ) -> Dict[str, Any]:
        domain = intent.get("entities", {}).get("domain") or _guess_domain(text)
        location = intent.get("entities", {}).get("location", "")
        filters = session.get_filters()

        results = await self._search(domain, text, location, filters)
        return await self._gen.generate_search_response(user_id, text, results, intent)

    async def _handle_filter(
        self, user_id: str, text: str, intent: Dict, session: Any
    ) -> Dict[str, Any]:
        entities = intent.get("entities", {})
        new_filters = {}
        if "location" in entities:
            new_filters["location"] = entities["location"]
        if "budget_mention" in entities:
            new_filters["budget"] = entities["budget_mention"]
        session.update_filters(new_filters)

        domain = _guess_domain(text)
        results = await self._search(domain, text, entities.get("location", ""), session.get_filters())
        return await self._gen.generate_filter_response(user_id, session.get_filters(), results)

    async def _handle_save(
        self, user_id: str, text: str, intent: Dict, session: Any
    ) -> Dict[str, Any]:
        words = text.lower().split()
        item_id = words[-1] if words else "unknown"
        title = item_id

        if self._db:
            try:
                await self._db.save_item(user_id, item_id)
            except Exception as exc:
                logger.warning("message_processor: save failed: %s", exc)

        return await self._gen.generate_save_response(title, item_id)

    async def _handle_view(
        self, user_id: str, text: str, intent: Dict
    ) -> Dict[str, Any]:
        words = text.lower().split()
        item_id = words[-1] if words else ""
        if item_id and self._db:
            try:
                item = await self._db.get_item(item_id)
                if item:
                    return {"text": self._format_detail(item), "type": "text", "buttons": [
                        {"label": "Save", "action": f"save_{item_id}"},
                        {"label": "Back to Search", "action": "search"},
                    ]}
            except Exception as exc:
                logger.warning("message_processor: view failed: %s", exc)
        return await self._gen.generate_help_response()

    async def _handle_my_saves(self, user_id: str) -> Dict[str, Any]:
        items: List[Dict] = []
        if self._db:
            try:
                items = await self._db.get_saved_items(user_id) or []
            except Exception as exc:
                logger.warning("message_processor: my_saves failed: %s", exc)

        if not items:
            return {"text": "You don't have any saved items yet. Use *save [ID]* to bookmark opportunities.", "type": "text", "buttons": []}

        text = "\U0001f4cb *Your Saved Items*\n\n"
        for i, item in enumerate(items[:10], 1):
            text += f"{i}. {item.get('title', 'Item')} — {item.get('location', '')}\n"
        return {"text": text, "type": "text", "buttons": [{"label": "Search More", "action": "search"}]}

    async def _handle_notify(
        self, user_id: str, text: str, session: Any
    ) -> Dict[str, Any]:
        return {
            "text": (
                "\U0001f514 *Alerts Activated!*\n\n"
                "I'll notify you when new opportunities match your criteria.\n"
                "You'll receive alerts as soon as new items are scraped.\n\n"
                "Reply *settings* to manage alert preferences."
            ),
            "type": "text",
            "buttons": [{"label": "Settings", "action": "settings"}],
        }

    # ──────────────────────────────────────────────────────────────────────────
    # DB search wrapper
    # ──────────────────────────────────────────────────────────────────────────

    async def _search(
        self, domain: str, query: str, location: str, filters: Dict
    ) -> List[Dict[str, Any]]:
        if not self._db:
            logger.debug("message_processor: no db — returning empty results")
            return []
        try:
            results = await self._db.search(
                domain=domain,
                query=query,
                location=location,
                filters=filters,
                limit=20,
            )
            return results or []
        except Exception as exc:
            logger.error("message_processor: search error: %s", exc)
            return []

    def _format_detail(self, item: Dict) -> str:
        lines = [f"*{item.get('title', 'Opportunity')}*\n"]
        for key in ("description", "location", "price", "salary", "company", "url"):
            val = item.get(key)
            if val:
                lines.append(f"{key.capitalize()}: {val}")
        return "\n".join(lines)

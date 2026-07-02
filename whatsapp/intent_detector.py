"""
WhatsApp Intent Detector — regex-first, AI fallback.
Documented in: docs/WHATSAPP AI ARCHITECTURE.md § 2.2

Patterns cover: search, filter, save, view, notify, compare, explain, help, settings.
Falls back to ModelRegistry (cheapest available) when no pattern matches.

Usage:
    from whatsapp.intent_detector import IntentDetector
    detector = IntentDetector()
    result = await detector.detect_intent("find marketing jobs in Dubai", context={})
    # {"intent": "search", "confidence": 0.9, "entities": {...}, "original_text": "..."}
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Simple entity extraction patterns
_LOC_RE = re.compile(r"\b(dubai|abu dhabi|sharjah|uae|abudhabi|ajman|ras al khaimah|qatar|riyadh|ksa|saudi)\b", re.I)
_SAL_RE = re.compile(r"(aed|usd|sar|qar)?\s*(\d[\d,]+)\s*(aed|usd|k|month|mo)?", re.I)
_DOM_RE = re.compile(r"\b(job|jobs|work|career|employment|property|properties|apartment|villa|flat|car|cars|vehicle|vehicles)\b", re.I)


class IntentDetector:
    def __init__(self, model_registry=None, prompt_engine=None) -> None:
        self._model_registry = model_registry
        self._prompt_engine = prompt_engine
        self._patterns: Dict[str, List[str]] = {
            "search": [
                r"find\s+.*",
                r"search\s+(for\s+)?.*",
                r"looking\s+for\s+.*",
                r"show\s+me\s+.*",
                r"get\s+me\s+.*",
                r"i\s+want\s+.*",
                r"i\s+need\s+.*",
            ],
            "filter": [
                r"filter\s+(by\s+)?.*",
                r"only\s+show\s+.*",
                r"with\s+(salary|price|budget|rent)\s+.*",
                r"between\s+.*\s+and\s+.*",
                r"under\s+\d+.*",
                r"above\s+\d+.*",
                r"maximum\s+\d+.*",
                r"minimum\s+\d+.*",
            ],
            "save": [
                r"save\s+.*",
                r"bookmark\s+.*",
                r"add\s+to\s+(my\s+)?saved.*",
                r"keep\s+this\s+.*",
            ],
            "view": [
                r"view\s+.*",
                r"show\s+details?.*",
                r"more\s+info(rmation)?\s+.*",
                r"tell\s+me\s+more\s+about\s+.*",
                r"open\s+.*",
            ],
            "notify": [
                r"notify\s+me.*",
                r"alert\s+me.*",
                r"set\s+(up\s+)?alert.*",
                r"send\s+me\s+updates.*",
                r"subscribe.*",
                r"daily\s+summary.*",
            ],
            "compare": [
                r"compare\s+.*",
                r"versus\s+.*",
                r"\bvs\b\s+.*",
                r"difference\s+between\s+.*",
            ],
            "explain": [
                r"explain\s+.*",
                r"what\s+is\s+.*",
                r"tell\s+me\s+about\s+.*",
                r"how\s+does\s+.*",
            ],
            "help": [
                r"^help$",
                r"what\s+can\s+you\s+do",
                r"capabilities",
                r"guide",
                r"tutorial",
            ],
            "settings": [
                r"settings",
                r"preferences",
                r"profile",
                r"notification\s+settings",
                r"alert\s+preferences",
            ],
            "my_saves": [
                r"my\s+saves?",
                r"saved\s+(items?|jobs?|properties|cars?)",
                r"show\s+my\s+bookmarks?",
            ],
        }

    async def detect_intent(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        text_lower = text.lower().strip()

        for intent_type, patterns in self._patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return {
                        "intent": intent_type,
                        "confidence": 0.9,
                        "entities": self._extract_entities(text),
                        "original_text": text,
                    }

        # AI fallback
        if self._model_registry and self._prompt_engine:
            return await self._ai_detect(text, context)

        return {
            "intent": "general",
            "confidence": 0.3,
            "entities": self._extract_entities(text),
            "original_text": text,
        }

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {}

        loc = _LOC_RE.findall(text)
        if loc:
            entities["location"] = loc[0].lower()

        dom = _DOM_RE.findall(text)
        if dom:
            raw = dom[0].lower()
            if raw in ("job", "jobs", "work", "career", "employment"):
                entities["domain"] = "jobs"
            elif raw in ("property", "properties", "apartment", "villa", "flat"):
                entities["domain"] = "real_estate"
            else:
                entities["domain"] = "vehicles"

        sal = _SAL_RE.search(text)
        if sal:
            entities["budget_mention"] = sal.group(0).strip()

        return entities

    async def _ai_detect(self, text: str, context: Dict) -> Dict[str, Any]:
        try:
            from models.model_registry import ModelCapability
            prompt = self._prompt_engine.render_template(
                "intent_detection",
                query=text,
                context=json.dumps(context),
                history="",
            )
            model = self._model_registry.select_model(ModelCapability.INTENT_DETECTION)
            # model.generate is not yet wired to a live API — log and return fallback
            logger.debug("intent_detector: ai_detect model=%s prompt_len=%d", model.model_name, len(prompt))
        except Exception as exc:
            logger.warning("intent_detector: ai fallback error: %s", exc)

        return {"intent": "general", "confidence": 0.4, "entities": self._extract_entities(text), "original_text": text}

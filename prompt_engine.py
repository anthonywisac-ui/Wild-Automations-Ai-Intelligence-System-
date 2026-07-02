"""
Prompt Engine — renders structured prompt templates for every AI stage.
Documented in: docs/AI ARCHITECTURE.md § 2.1, docs/PROMPT ENGINEERING GUIDE.md

Usage:
    from prompt_engine import PromptEngine
    engine = PromptEngine()
    prompt = engine.render_template("intent_detection", query="find jobs in Dubai", context="")
"""

from typing import Any, Dict, Optional


class PromptEngine:
    def __init__(self) -> None:
        self.templates: Dict[str, str] = self._load_templates()

    # ──────────────────────────────────────────────────────────────────────────
    # Template library
    # ──────────────────────────────────────────────────────────────────────────

    def _load_templates(self) -> Dict[str, str]:
        return {

            # ── Intent detection ─────────────────────────────────────────────
            "intent_detection": """
You are an intent detection system for WildAutomations AI Opportunity Intelligence Platform.

SYSTEM CONTEXT:
- Platform helps users find opportunities (jobs, real estate, vehicles, education, etc.)
- Users ask in natural language; support multi-domain, complex queries.

TASK: Identify primary intent, secondary intents, domains, key entities, confidence.

INTENTS: SEARCH, FILTER, SAVE, COMPARE, EXPLAIN, NOTIFY, HELP, SETTINGS

DOMAINS: JOBS, REAL_ESTATE, VEHICLES, EDUCATION, IMMIGRATION, SCHOLARSHIPS, AUCTIONS, BUSINESS

OUTPUT (JSON only):
{{
    "intent": "SEARCH",
    "secondary_intents": ["FILTER"],
    "domains": ["JOBS"],
    "entities": {{
        "job_title": "Data Scientist",
        "location": "Dubai",
        "visa_sponsorship": true
    }},
    "confidence": 0.95,
    "suggestions": []
}}

USER QUERY: {query}
USER CONTEXT: {context}
HISTORICAL INTERACTIONS: {history}

RULES:
1. Always include confidence score (0.0-1.0).
2. Extract all relevant entities.
3. Consider context for ambiguous queries.
4. Output ONLY valid JSON — no prose, no markdown code fences.
""",

            # ── Entity extraction ─────────────────────────────────────────────
            "entity_extraction": """
You are an entity extraction system for WildAutomations AI Opportunity Intelligence Platform.

TEXT: {text}
DOMAIN: {domain}
SCHEMA: {schema}

Extract all relevant entities and map them to the schema.
Set confidence scores (0.0-1.0) per entity.
Only extract explicitly stated or strongly implied information.

OUTPUT (JSON only):
{{
    "entities": {{...}},
    "confidence": 0.90,
    "warnings": []
}}
""",

            # ── Response generation ───────────────────────────────────────────
            "response_generation": """
You are an AI assistant for WildAutomations Opportunity Intelligence Platform.
Format your response for WhatsApp delivery: plain text, concise, no markdown.

USER QUERY: {query}
USER CONTEXT: {context}
SEARCH RESULTS: {results}
INTENT: {intent}

GUIDELINES:
1. Be conversational and helpful.
2. Highlight the most relevant opportunities (max 3).
3. Include: title, location, salary/price.
4. Suggest a follow-up action.
5. If results are empty, suggest alternative queries.
6. Keep response under 300 words.

Response format based on intent:
- SEARCH: Summary + top results + next steps
- FILTER: Explain applied filters + results
- SAVE: Confirmation + next steps
- COMPARE: Plain-text comparison + recommendation
""",

            # ── Opportunity normalization ─────────────────────────────────────
            "opportunity_normalization": """
You are an opportunity normalization system.

RAW DATA: {raw_data}
DOMAIN: {domain}
SOURCE: {source}
TARGET SCHEMA: {schema}

Normalize the raw data into the standard schema:
1. Map all fields.
2. Convert dates to ISO 8601 UTC.
3. Normalize currencies to ISO 4217 codes.
4. Clean and validate text.
5. Calculate per-field confidence.
6. Flag missing/uncertain data in warnings.

OUTPUT (JSON only):
{{
    "normalized": {{...}},
    "confidence": 0.92,
    "warnings": ["missing field: salary_min"],
    "source_fields": {{...}}
}}
""",

            # ── Deduplication check ───────────────────────────────────────────
            "deduplication_check": """
You are a deduplication engine.

NEW OPPORTUNITY: {new_opportunity}
EXISTING OPPORTUNITIES: {existing_opportunities}

Determine if the new opportunity is a duplicate of any existing one.

Criteria:
1. Title similarity > 0.85
2. Description similarity > 0.75
3. Domain-specific field match (company + location + salary)
4. Source + source_id exact match

OUTPUT (JSON only):
{{
    "is_duplicate": false,
    "matched_id": null,
    "similarity_score": 0.45,
    "explanation": "No duplicate found"
}}
""",

            # ── Opportunity scoring ───────────────────────────────────────────
            "scoring": """
You are a scoring system for opportunity-to-profile matching.

USER PROFILE: {profile}
OPPORTUNITY: {opportunity}
DOMAIN: {domain}
WEIGHTS: {weights}

Score these dimensions (0-100 each):
1. Location match
2. Budget/Salary match
3. Skills/Requirements match
4. Education match
5. Experience match
6. Visa sponsorship match
7. Language match

OUTPUT (JSON only):
{{
    "overall_score": 87,
    "dimensions": {{
        "location": 95,
        "budget": 82,
        "skills": 88,
        "education": 92,
        "experience": 80,
        "visa": 90,
        "language": 85
    }},
    "confidence": 0.93,
    "top_matches": ["location", "education"],
    "suggestions": []
}}
""",

            # ── WhatsApp opportunity alert (passthrough-compatible) ────────────
            "whatsapp_alert": """You are a WhatsApp notification formatter for {bot_name}.

ITEM DATA:
{item_data}

Write a short WhatsApp alert (plain text, max 250 words) with:
- Relevant emoji at start
- Title / key fact on line 1
- 2-3 bullet highlights
- Source URL if available
- One clear call-to-action

No markdown, no headers, no asterisks. Plain text only.
""",
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def render_template(self, template_name: str, **kwargs: Any) -> str:
        """Render a named template with keyword variables."""
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"PromptEngine: template not found: {template_name!r}")
        try:
            return template.format(**kwargs)
        except KeyError as exc:
            raise ValueError(f"PromptEngine: missing variable {exc} in template {template_name!r}") from exc

    def add_template(self, name: str, template: str) -> None:
        """Register a custom template at runtime."""
        self.templates[name] = template

    def list_templates(self) -> list:
        return list(self.templates.keys())

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RuntimeConfig:
    """Config-driven runtime settings, sourced from environment variables."""

    supabase_url: Optional[str] = field(default_factory=lambda: os.environ.get("SUPABASE_URL"))
    supabase_key: Optional[str] = field(default_factory=lambda: os.environ.get("SUPABASE_KEY"))
    supabase_table: str = field(default_factory=lambda: os.environ.get("SUPABASE_TABLE", "bot_alerts"))

    apify_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("APIFY_API_KEY"))

    openai_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    gemini_model: str = field(default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
    ai_provider: str = field(default_factory=lambda: os.environ.get("AI_PROVIDER", "passthrough"))

    whapi_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("WHAPI_API_KEY"))
    meta_phone_number_id: Optional[str] = field(default_factory=lambda: os.environ.get("META_PHONE_NUMBER_ID"))
    meta_access_token: Optional[str] = field(default_factory=lambda: os.environ.get("META_ACCESS_TOKEN"))
    twilio_account_sid: Optional[str] = field(default_factory=lambda: os.environ.get("TWILIO_ACCOUNT_SID"))
    twilio_auth_token: Optional[str] = field(default_factory=lambda: os.environ.get("TWILIO_AUTH_TOKEN"))
    twilio_from_number: Optional[str] = field(default_factory=lambda: os.environ.get("TWILIO_FROM_NUMBER"))

    max_pipeline_retries: int = field(default_factory=lambda: int(os.environ.get("MAX_PIPELINE_RETRIES", "3")))
    worker_concurrency: int = field(default_factory=lambda: int(os.environ.get("WORKER_CONCURRENCY", "5")))
    domain_concurrency: int = field(default_factory=lambda: int(os.environ.get("DOMAIN_CONCURRENCY", "2")))
    respect_robots: bool = field(default_factory=lambda: os.environ.get("RESPECT_ROBOTS", "true").lower() == "true")
    notify_to: Optional[str] = field(default_factory=lambda: os.environ.get("NOTIFY_TO"))
    dry_run: bool = field(default_factory=lambda: os.environ.get("DRY_RUN", "false").lower() == "true")


def build_ai_processor(cfg: RuntimeConfig, bots: List[Dict[str, Any]]) -> AIProcessor:
    """Build a per-bot prompt template map and the shared AIProcessor."""
    from core.ai_processor import AIProcessor, AIConfig, PromptTemplate

    templates: Dict[str, PromptTemplate] = {}
    for bot in bots:
        templates[bot["bot_name"]] = PromptTemplate(
            template=(
                "Bot: $bot_name\n"
                "Region: $region_routing\n"
                "Listing: $title $description $price ($location)\n\n"
                "Summarize this into a JSON object with keys 'subject' and 'body' "
                "suitable for a WhatsApp alert."
            ),
            variables={
                "bot_name": "bot name",
                "region_routing": "region",
                "title": "listing title",
                "description": "listing description",
                "price": "listing price",
                "location": "listing location",
            },
        )

    return AIProcessor(
        config=AIConfig(
            openai_api_key=cfg.openai_api_key,
            anthropic_api_key=cfg.anthropic_api_key,
            gemini_api_key=cfg.gemini_api_key,
            gemini_model=cfg.gemini_model,
            default_provider=cfg.ai_provider,
            max_retries=cfg.max_pipeline_retries,
        ),
        templates=templates,
        concurrency=cfg.worker_concurrency,
    )

"""
Wild Automations - Bot Orchestration Engine.

Loads the bot manifest, validates per-portal crawl configs, then runs every
bot's pipeline (crawl -> normalize -> score -> dedupe -> AI process -> deliver)
concurrently on an asyncio queue-based architecture.
"""

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import httpx as _httpx_module
_orig_async_init = _httpx_module.AsyncClient.__init__
def _patch_async_client(self, *a, **kw):
    kw["verify"] = False
    _orig_async_init(self, *a, **kw)
_httpx_module.AsyncClient.__init__ = _patch_async_client
_orig_sync_init = _httpx_module.Client.__init__
def _patch_sync_client(self, *a, **kw):
    kw["verify"] = False
    _orig_sync_init(self, *a, **kw)
_httpx_module.Client.__init__ = _patch_sync_client

import asyncio
import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.scraper_engine import SmartScraperEngine, ScrapedItem, validate_portal_config
from core.apify_client import ApifyClient
from core.dedupe_engine import DedupEngine, DedupConfig
from core.scoring_engine import ScoringEngine, ScoringConfig
from core.ai_processor import AIProcessor, AIConfig, PromptTemplate
from core.delivery_engine import DeliveryEngine, DeliveryConfig
from core.database_layer import SupabaseDB
from delivery.notification_delivery import NotificationDelivery
from delivery.scheduler import NotificationScheduler
from whatsapp.message_processor import MessageProcessor
from whatsapp.intent_detector import IntentDetector
from whatsapp.response_generator import ResponseGenerator
from whatsapp.session_manager import SessionManager

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("orchestrator")


def _load_bot_manifest_module():
    """Load config/bot_manifests.py.py via importlib (filename is not a valid module path)."""
    manifest_path = BASE_DIR / "config" / "bot_manifests.py.py"
    spec = importlib.util.spec_from_file_location("bot_manifests", manifest_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class RuntimeConfig:
    """Config-driven runtime settings, sourced from environment variables."""

    supabase_url: Optional[str] = field(default_factory=lambda: os.environ.get("SUPABASE_URL"))
    supabase_key: Optional[str] = field(default_factory=lambda: os.environ.get("SUPABASE_KEY"))
    supabase_table: str = field(default_factory=lambda: os.environ.get("SUPABASE_TABLE", "bot_alerts"))

    apify_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("APIFY_API_KEY"))

    openai_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
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


def build_delivery_engine(cfg: RuntimeConfig) -> DeliveryEngine:
    """Construct DeliveryEngine from whichever provider credentials are present."""
    providers: Dict[str, Dict[str, Any]] = {}

    if cfg.whapi_api_key:
        providers["whapi"] = {"type": "whatsapp_whapi", "api_key": cfg.whapi_api_key}
    if cfg.meta_phone_number_id and cfg.meta_access_token:
        providers["meta"] = {
            "type": "whatsapp_meta",
            "phone_number_id": cfg.meta_phone_number_id,
            "access_token": cfg.meta_access_token,
        }
    if cfg.twilio_account_sid and cfg.twilio_auth_token and cfg.twilio_from_number:
        providers["twilio"] = {
            "type": "twilio",
            "account_sid": cfg.twilio_account_sid,
            "auth_token": cfg.twilio_auth_token,
            "from_number": cfg.twilio_from_number,
        }

    region_routing = {
        "uae": [name for name in ("whapi", "meta") if name in providers],
        "global": [name for name in ("meta", "twilio", "whapi") if name in providers],
    }

    return DeliveryEngine(
        DeliveryConfig(providers=providers, region_routing=region_routing, default_region="global")
    )


def build_ai_processor(cfg: RuntimeConfig, bots: List[Dict[str, Any]]) -> AIProcessor:
    """Build a per-bot prompt template map and the shared AIProcessor."""
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
            default_provider=cfg.ai_provider,
            max_retries=cfg.max_pipeline_retries,
        ),
        templates=templates,
        concurrency=cfg.worker_concurrency,
    )


@dataclass
class BotJob:
    """A single ScrapedItem queued for downstream processing."""

    bot_name: str
    region: str
    delivery_channels: List[str]
    item: ScrapedItem


# --------------------------------------------------------------------------
# Boot-time validation
# --------------------------------------------------------------------------

def validate_manifest(manifest_module) -> Dict[str, Any]:
    """
    Walk every bot's target_portals, validate each portal_config, and report
    which (bot, portal) pairs are crawlable vs. skipped. Never invents config.
    """
    bots = manifest_module.bot_manifest["bots"]
    crawlable: Dict[str, List[str]] = {}
    skipped: Dict[str, List[str]] = {}

    for bot in bots:
        bot_name = bot["bot_name"]
        for portal_name, portal_config in manifest_module.iter_bot_portal_configs(bot):
            is_valid, reason = validate_portal_config(portal_config)
            if is_valid:
                crawlable.setdefault(bot_name, []).append(portal_name)
            else:
                skipped.setdefault(bot_name, []).append(f"{portal_name} ({reason})")
                logger.warning("Skipping portal bot=%s portal=%s reason=%s", bot_name, portal_name, reason)

    return {"bots": bots, "crawlable": crawlable, "skipped": skipped}


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------

class Orchestrator:
    """
    Async, queue-based pipeline runner.

    Flow per bot: crawl (SmartScraperEngine) -> normalize -> score -> dedupe
    -> AI process -> deliver. Bots/portals run concurrently; each stage is
    non-blocking and retried on failure. Portals missing config are skipped
    upstream by validate_manifest(), so the orchestrator only ever sees
    crawlable (bot, portal) pairs.
    """

    def __init__(self, cfg: RuntimeConfig, manifest_module, validated: Dict[str, Any]):
        self.cfg = cfg
        self.manifest_module = manifest_module
        self.bots = validated["bots"]
        self.crawlable = validated["crawlable"]

        self.scraper = SmartScraperEngine(
            max_concurrency_per_domain=cfg.domain_concurrency,
            respect_robots=cfg.respect_robots,
            retries=cfg.max_pipeline_retries,
        )
        self.apify: Optional[ApifyClient] = None
        if cfg.apify_api_key:
            self.apify = ApifyClient(cfg.apify_api_key)
        else:
            logger.warning("APIFY_API_KEY not set; Apify-sourced portals will be skipped")
        self.dedupe = DedupEngine(DedupConfig())
        self.scoring = ScoringEngine(ScoringConfig())
        self.ai_processor = build_ai_processor(cfg, self.bots)
        self.delivery = build_delivery_engine(cfg)

        self.db: Optional[SupabaseDB] = None
        if cfg.supabase_url and cfg.supabase_key:
            self.db = SupabaseDB(cfg.supabase_url, cfg.supabase_key, cfg.supabase_table)
        else:
            logger.warning("Supabase credentials not set; persistence is disabled")

        self.pipeline_queue: "asyncio.Queue[BotJob]" = asyncio.Queue()

        # Layer 2: notification delivery + WhatsApp chatbot processor
        self.notification_delivery = NotificationDelivery(whatsapp_engine=self.delivery)
        self.scheduler = NotificationScheduler(delivery=self.notification_delivery, db=self.db)
        self.message_processor = MessageProcessor(
            db=self.db,
            response_gen=ResponseGenerator(),
            session_mgr=SessionManager(),
            intent_detector=IntentDetector(),
        )

    async def run(self) -> None:
        logger.info(
            "Starting orchestration | bots=%d crawlable_bots=%d dry_run=%s worker_concurrency=%d",
            len(self.bots), len(self.crawlable), self.cfg.dry_run, self.cfg.worker_concurrency,
        )
        await self.ai_processor.start()
        scheduler_task = asyncio.create_task(self.scheduler.run())

        await self._crawl_all_bots()

        if self.cfg.dry_run:
            logger.info("DRY_RUN=true: stopping before delivery stage.")
            scheduler_task.cancel()
            await self.ai_processor.stop()
            await self.delivery.shutdown()
            self._log_stats()
            return

        consumer_count = max(1, self.cfg.worker_concurrency)
        consumers = [asyncio.create_task(self._pipeline_worker()) for _ in range(consumer_count)]

        await self.pipeline_queue.join()
        for task in consumers:
            task.cancel()
        await asyncio.gather(*consumers, return_exceptions=True)

        scheduler_task.cancel()
        await self.ai_processor.stop()
        await self.delivery.shutdown()
        self._log_stats()
        logger.info("Orchestration complete")

    async def _crawl_all_bots(self) -> None:
        bot_by_name = {bot["bot_name"]: bot for bot in self.bots}

        PORTAL_TIMEOUT = 120  # seconds per portal max

        async def crawl_one(bot_name: str, portal_name: str):
            bot = bot_by_name[bot_name]
            portal_config = self.manifest_module.get_portal_config(portal_name)
            try:
                if portal_config.get("source") == "apify":
                    await asyncio.wait_for(
                        self._crawl_via_apify(bot, portal_name, portal_config),
                        timeout=PORTAL_TIMEOUT,
                    )
                else:
                    items = await asyncio.wait_for(
                        self.scraper.crawl_bot(bot_name, portal_config),
                        timeout=PORTAL_TIMEOUT,
                    )
                    for item in items:
                        await self.pipeline_queue.put(
                            BotJob(
                                bot_name=bot_name,
                                region=bot.get("region_routing", "global"),
                                delivery_channels=bot.get("delivery_channels", []),
                                item=item,
                            )
                        )
            except asyncio.TimeoutError:
                logger.warning("crawl:timeout bot=%s portal=%s (>%ds) — skipping", bot_name, portal_name, PORTAL_TIMEOUT)
            except Exception as exc:
                logger.error("crawl:error bot=%s portal=%s error=%s", bot_name, portal_name, exc)

        tasks = [
            crawl_one(bot_name, portal_name)
            for bot_name, portal_names in self.crawlable.items()
            for portal_name in portal_names
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _crawl_via_apify(self, bot: Dict[str, Any], portal_name: str, portal_config: Dict[str, Any]) -> None:
        """Fetch results from Apify actor and push to pipeline queue."""
        if not self.apify:
            logger.warning("Skipping apify portal=%s — APIFY_API_KEY not set", portal_name)
            return

        from config.apify_actors import get_actor
        actor_key = portal_config.get("apify_actor_key")
        try:
            actor_cfg = get_actor(actor_key)
        except KeyError:
            logger.error("Unknown apify_actor_key=%s for portal=%s", actor_key, portal_name)
            return

        input_data = {**actor_cfg.get("default_input", {}), **portal_config.get("apify_input_override", {})}
        logger.info("apify:crawl portal=%s actor=%s", portal_name, actor_cfg["actor_id"])

        try:
            raw_items = await self.apify.run_actor(actor_cfg["actor_id"], input_data)
        except Exception as exc:
            logger.error("apify:failed portal=%s error=%s", portal_name, exc)
            return

        logger.info("apify:done portal=%s items=%d", portal_name, len(raw_items))
        for raw in raw_items:
            item = self._apify_raw_to_scraped_item(raw, portal_name, portal_config)
            await self.pipeline_queue.put(
                BotJob(
                    bot_name=bot["bot_name"],
                    region=bot.get("region_routing", "global"),
                    delivery_channels=bot.get("delivery_channels", []),
                    item=item,
                )
            )

    def _apify_raw_to_scraped_item(self, raw: Dict[str, Any], portal_name: str, portal_config: Dict[str, Any]) -> ScrapedItem:
        """Normalize raw Apify JSON dict → ScrapedItem."""
        schema = portal_config.get("extraction_schema", {})
        # Try schema-mapped keys first, then common fallback keys
        def _get(field_key: str, *fallbacks: str) -> str:
            mapped = schema.get(field_key)
            for key in ([mapped] if mapped else []) + list(fallbacks):
                if key and raw.get(key):
                    return str(raw[key])
            return ""

        return ScrapedItem(
            source_portal=portal_name,
            source_url=raw.get("url", raw.get("link", raw.get("detailUrl", ""))),
            title=_get("title", "title", "name", "Make/Model", "Title"),
            price=_get("price", "price", "Price", "currentBid", "Current Bid"),
            location=_get("location", "location", "Location", "city", "address"),
            description=_get("description", "description", "Description", "Item Description", "details"),
            raw_text=str(raw),
            metadata={"apify_raw": raw},
            confidence=0.8,
            crawl_mode_used="apify",
        )

    def _log_stats(self) -> None:
        for portal_name in self.scraper.stats:
            logger.info("Portal stats: %s", self.scraper.get_stats(portal_name))

    async def _pipeline_worker(self) -> None:
        while True:
            try:
                job = await self.pipeline_queue.get()
            except asyncio.CancelledError:
                return
            try:
                await self._process_with_retry(job)
            except Exception:
                logger.exception("Pipeline failed permanently for bot=%s", job.bot_name)
            finally:
                self.pipeline_queue.task_done()

    async def _process_with_retry(self, job: BotJob) -> None:
        for attempt in range(1, self.cfg.max_pipeline_retries + 1):
            try:
                await self._process_job(job)
                return
            except Exception as exc:
                wait = 2 ** attempt
                logger.warning(
                    "Pipeline attempt %d/%d failed for bot=%s: %s",
                    attempt, self.cfg.max_pipeline_retries, job.bot_name, exc,
                )
                if attempt == self.cfg.max_pipeline_retries:
                    raise
                await asyncio.sleep(wait)

    async def _process_job(self, job: BotJob) -> None:
        normalized = self._to_scoring_dict(job.item)

        is_dup, details = self.dedupe.is_duplicate(
            url=job.item.source_url, content=normalized, title=job.item.title
        )
        if is_dup:
            logger.info("Duplicate skipped bot=%s reason=%s", job.bot_name, details.get("reason"))
            return

        score = self.scoring.compute_score(normalized)
        normalized["_score"] = score

        if self.db:
            await self.db.insert(raw_data=asdict(job.item), normalized_data=normalized)

        await self.ai_processor.add_job(job.bot_name, normalized)
        ai_result = await self.ai_processor.results.get()
        structured = ai_result.get("structured", {})

        message = structured.get("body") or job.item.title or "New alert"
        recipient = self.cfg.notify_to
        if recipient:
            await self.delivery.send(
                to=recipient,
                message=message,
                region=job.region,
                metadata={"bot": job.bot_name, "score": score, "portal": job.item.source_portal},
            )
        else:
            logger.warning("NOTIFY_TO not configured; skipping delivery for bot=%s", job.bot_name)

        self.dedupe.add_record(url=job.item.source_url, content=normalized, title=job.item.title)

    @staticmethod
    def _to_scoring_dict(item: ScrapedItem) -> Dict[str, Any]:
        """Map ScrapedItem into the flat dict shape scoring/AI stages expect."""
        return {
            "url": item.source_url,
            "title": item.title or "",
            "description": item.description or "",
            "price": item.price or "",
            "location": item.location or "",
            "keyword_match": 1.0 if item.title else 0.0,
            "urgency": 0.5,
            "price_drop": 0.0,
            "recency": 0.0,
            "seller_type": item.metadata.get("seller_type", "unknown"),
            "confidence": item.confidence,
            "crawl_mode_used": item.crawl_mode_used,
        }


async def main() -> None:
    cfg = RuntimeConfig()
    manifest_module = _load_bot_manifest_module()
    validated = validate_manifest(manifest_module)

    logger.info(
        "Manifest validated | crawlable_bots=%s skipped_bots=%s",
        list(validated["crawlable"].keys()), list(validated["skipped"].keys()),
    )

    orchestrator = Orchestrator(cfg, manifest_module, validated)
    try:
        await orchestrator.run()
    except Exception:
        logger.exception("Orchestration crashed")
        raise


if __name__ == "__main__":
    asyncio.run(main())

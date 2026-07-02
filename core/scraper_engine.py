"""
SmartScraperEngine - unified crawling service.

Replaces the old single-spider scraper with a strategy-routed crawler that
separates acquisition (fetching pages), extraction (selector/schema parsing),
and normalization (shared ScrapedItem model).

Engines used opportunistically, never required:
    - Scrapy concepts (scheduling, retry/backoff, auto-throttle, dedupe) are
      reimplemented with asyncio primitives below so this module has no hard
      dependency on the Scrapy reactor.
    - Crawl4AI, if installed, powers deep/structured extraction for
      crawl_mode="deep" and "hybrid".
    - Scrapling, if installed, powers stealthy/browser-like fetches for
      crawl_mode="browser" and anti_bot_profile != "none".

If a portal has no config, or the config is missing required fields, the
engine logs a structured warning and skips it. It never invents selectors.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse, urljoin
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False

try:
    import crawl4ai  # noqa: F401
    _HAS_CRAWL4AI = True
except ImportError:
    _HAS_CRAWL4AI = False

try:
    import scrapling  # noqa: F401
    _HAS_SCRAPLING = True
except ImportError:
    _HAS_SCRAPLING = False


REQUIRED_PORTAL_FIELDS = ("portal_name", "crawl_mode")
VALID_CRAWL_MODES = (
    "http", "browser", "deep", "hybrid", "apify", "jobspy",
    # GitHub-direct clients (no Apify)
    "gulftalent",           # direct HTTP scraper → gulftalent_client.py
    "visa_bulletin",        # travel.state.gov + Canada IRCC → visa_client.py
    "visa_wiki",            # Wikipedia visa requirements → visa_client.py
    "university_api",       # HIPO Labs + College Scorecard + THE → university_client.py
    "qs_rankings",          # QS World + subject rankings → qs_client.py
    "passport_index",       # Passport Index Dataset (alsonpr) → passport_index_client.py
    "uk_sponsored_jobs",    # UK Skilled Worker visa jobs → uk_jobs_client.py
    "eu_visa_policy",       # EU Schengen visa stats → eu_visa_client.py
    "car_auction",          # NHTSA vehicle data → car_auction_client.py
    "admissions_data",      # College Scorecard admission stats → admissions_client.py
    "ats_jobs",             # Greenhouse + WeWorkRemotely + RemoteOK → ats_client.py
    "admissions_news",      # PIE News + ICEF Monitor RSS → admissions_news_client.py
    "global_admissions",    # 7-region admissions guide → global_admissions_client.py
)


# --------------------------------------------------------------------------
# Shared output model
# --------------------------------------------------------------------------

@dataclass
class ScrapedItem:
    source_portal: str
    source_url: str
    title: Optional[str] = None
    price: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    raw_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    crawl_mode_used: str = ""


@dataclass
class PortalStats:
    """Per-portal observability counters."""

    portal_name: str
    pages_fetched: int = 0
    items_extracted: int = 0
    duplicates_dropped: int = 0
    failures_by_reason: Dict[str, int] = field(default_factory=dict)
    confidence_samples: List[float] = field(default_factory=list)

    def record_failure(self, reason: str) -> None:
        self.failures_by_reason[reason] = self.failures_by_reason.get(reason, 0) + 1

    def summary(self) -> Dict[str, Any]:
        avg_confidence = (
            sum(self.confidence_samples) / len(self.confidence_samples)
            if self.confidence_samples
            else 0.0
        )
        return {
            "portal_name": self.portal_name,
            "pages_fetched": self.pages_fetched,
            "items_extracted": self.items_extracted,
            "duplicates_dropped": self.duplicates_dropped,
            "failures_by_reason": dict(self.failures_by_reason),
            "avg_confidence": round(avg_confidence, 3),
        }


# --------------------------------------------------------------------------
# Config validation
# --------------------------------------------------------------------------

def validate_portal_config(config: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Validate a portal_config dict has the minimum fields needed to crawl.
    Returns (is_valid, reason). Never fills in missing data.
    """
    if not config:
        return False, "missing_config"

    missing = [f for f in REQUIRED_PORTAL_FIELDS if not config.get(f)]
    if missing:
        return False, f"missing_fields:{','.join(missing)}"

    if config["crawl_mode"] not in VALID_CRAWL_MODES:
        return False, f"invalid_crawl_mode:{config['crawl_mode']}"

    _GITHUB_DIRECT_MODES = (
        "jobspy", "gulftalent", "visa_bulletin", "visa_wiki", "university_api",
        "qs_rankings", "passport_index", "uk_sponsored_jobs", "eu_visa_policy",
        "car_auction", "admissions_data",
        "ats_jobs", "admissions_news", "global_admissions",
    )
    if config["crawl_mode"] in _GITHUB_DIRECT_MODES:
        return True, "ok"

    if not config.get("start_urls") or not config.get("allowed_domains"):
        return False, "missing_fields:start_urls,allowed_domains"

    if not config.get("listing_selectors") and not config.get("extraction_schema"):
        return False, "no_extraction_target"

    return True, "ok"


def _canonical_url(url: str) -> str:
    """Normalize a URL for dedupe purposes (scheme/host lowercased, no fragment, sorted query)."""
    parsed = urlparse(url)
    query_parts = sorted(parsed.query.split("&")) if parsed.query else []
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.params,
            "&".join(query_parts),
            "",
        )
    )


# --------------------------------------------------------------------------
# Domain-level safety controls
# --------------------------------------------------------------------------

class DomainThrottle:
    """Per-domain concurrency cap + delay + robots.txt gate."""

    def __init__(self, max_concurrency_per_domain: int = 2, respect_robots: bool = True):
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._robots_cache: Dict[str, RobotFileParser] = {}
        self.max_concurrency_per_domain = max_concurrency_per_domain
        self.respect_robots = respect_robots

    def _semaphore_for(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._semaphores:
            self._semaphores[domain] = asyncio.Semaphore(self.max_concurrency_per_domain)
        return self._semaphores[domain]

    async def is_allowed(self, url: str, user_agent: str = "*") -> bool:
        if not self.respect_robots:
            return True
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain not in self._robots_cache:
            rp = RobotFileParser()
            rp.set_url(f"{parsed.scheme}://{domain}/robots.txt")
            try:
                await asyncio.get_event_loop().run_in_executor(None, rp.read)
            except Exception:
                pass  # if robots.txt is unreachable, default to allow
            self._robots_cache[domain] = rp
        return self._robots_cache[domain].can_fetch(user_agent, url)

    def slot(self, url: str) -> asyncio.Semaphore:
        return self._semaphore_for(urlparse(url).netloc)


async def _retry_with_backoff(coro_factory, retries: int, base_delay: float, reason_sink: PortalStats, label: str):
    """Run coro_factory() with exponential backoff retries."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            reason_sink.record_failure(f"{label}:{type(exc).__name__}")
            if attempt == retries:
                break
            wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, base_delay)
            logger.warning("%s attempt %d/%d failed: %s. Retrying in %.2fs", label, attempt, retries, exc, wait)
            await asyncio.sleep(wait)
    raise last_exc


# --------------------------------------------------------------------------
# Acquisition strategies (fetch raw page content)
# --------------------------------------------------------------------------

class AcquisitionStrategy:
    name = "base"

    async def fetch(self, url: str, portal_config: Dict[str, Any]) -> str:
        raise NotImplementedError


try:
    from curl_cffi.requests import Session as CurlSession
    _HAS_CURL_CFFI = True
except ImportError:
    _HAS_CURL_CFFI = False


class HttpStrategy(AcquisitionStrategy):
    """Fast path: curl_cffi (browser TLS) → httpx fallback."""

    name = "http"

    async def fetch(self, url: str, portal_config: Dict[str, Any]) -> str:
        headers = portal_config.get("request_headers") or {}
        if _HAS_CURL_CFFI:
            def _curl_get():
                with CurlSession(impersonate="chrome120") as s:
                    r = s.get(url, headers=headers, timeout=30, allow_redirects=True, verify=False)
                    r.raise_for_status()
                    return r.text
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _curl_get)
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, verify=False) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text


_BROWSER_SEM: Optional[asyncio.Semaphore] = None

def _get_browser_sem() -> asyncio.Semaphore:
    global _BROWSER_SEM
    if _BROWSER_SEM is None:
        _BROWSER_SEM = asyncio.Semaphore(1)
    return _BROWSER_SEM


class BrowserStrategy(AcquisitionStrategy):
    """JS-heavy pages: render with a real browser engine (Playwright)."""

    name = "browser"

    async def fetch(self, url: str, portal_config: Dict[str, Any]) -> str:
        if not _HAS_PLAYWRIGHT:
            raise RuntimeError("playwright not installed; cannot run browser strategy")
        headers = portal_config.get("request_headers") or {}
        async with _get_browser_sem():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--max_old_space_size=512"])
                try:
                    context = await browser.new_context(
                        extra_http_headers=headers,
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                        viewport={"width": 1280, "height": 800},
                    )
                    page = await context.new_page()
                    await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                    return await page.content()
                finally:
                    await browser.close()


class StealthStrategy(AcquisitionStrategy):
    """Anti-bot resilient fetch. Uses Scrapling if available and configured, else falls back to BrowserStrategy."""

    name = "stealth"

    def __init__(self):
        self._browser_fallback = BrowserStrategy()

    async def fetch(self, url: str, portal_config: Dict[str, Any]) -> str:
        if _HAS_SCRAPLING:
            try:
                from scrapling.fetchers import StealthyFetcher  # type: ignore

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: StealthyFetcher.fetch(url)
                )
                return response.html_content if hasattr(response, "html_content") else str(response)
            except FileNotFoundError as exc:
                # camoufox not installed — `camoufox fetch` was not run.
                # Fall through immediately without retrying.
                logger.warning(
                    "scrapling/camoufox not configured (%s); using browser strategy for %s", exc, url
                )
            except Exception as exc:
                # Sync Playwright conflict or other scrapling error; fall through.
                logger.warning(
                    "scrapling failed (%s); using browser strategy for %s", type(exc).__name__, url
                )
        else:
            logger.warning("scrapling not installed; falling back to browser strategy for stealth fetch of %s", url)
        return await self._browser_fallback.fetch(url, portal_config)


class DeepCrawlStrategy(AcquisitionStrategy):
    """
    Category/listing discovery: crawl start_urls, follow pagination and
    listing links up to max_depth/max_pages. Uses Crawl4AI's deep crawler if
    available, else a lightweight BFS over HttpStrategy.
    """

    name = "deep"

    def __init__(self):
        self._http = HttpStrategy()

    async def discover(
        self, portal_config: Dict[str, Any], stats: PortalStats
    ) -> List[str]:
        if _HAS_CRAWL4AI:
            return await self._discover_with_crawl4ai(portal_config)
        return await self._discover_with_bfs(portal_config, stats)

    async def _discover_with_crawl4ai(self, portal_config: Dict[str, Any]) -> List[str]:
        from crawl4ai import AsyncWebCrawler  # type: ignore

        max_pages = portal_config.get("max_pages", 50)
        urls: List[str] = []
        async with AsyncWebCrawler() as crawler:
            for start_url in portal_config["start_urls"]:
                result = await crawler.arun(url=start_url, max_depth=portal_config.get("max_depth", 1))
                links = getattr(result, "links", {}) or {}
                internal = links.get("internal", []) if isinstance(links, dict) else []
                urls.extend(link.get("href", "") for link in internal if link.get("href"))
                if len(urls) >= max_pages:
                    break
        return urls[: portal_config.get("max_pages", 50)]

    async def _discover_with_bfs(self, portal_config: Dict[str, Any], stats: PortalStats) -> List[str]:
        """Minimal BFS fallback: follow pagination_selectors' 'next' link only."""
        import re

        max_pages = portal_config.get("max_pages", 1)
        allowed_domains = set(portal_config.get("allowed_domains", []))
        pagination = portal_config.get("pagination_selectors") or {}
        next_pattern = pagination.get("next_href_regex")

        urls = list(portal_config["start_urls"])
        seen = set(urls)
        page_count = 0
        url = urls[0] if urls else None

        while url and page_count < max_pages:
            try:
                html = await self._http.fetch(url, portal_config)
                stats.pages_fetched += 1
            except Exception as exc:
                stats.record_failure(f"deep_discover:{type(exc).__name__}")
                break

            page_count += 1
            if not next_pattern:
                break

            match = re.search(next_pattern, html)
            if not match:
                break
            next_url = urljoin(url, match.group(1))
            parsed_next = urlparse(next_url)
            if allowed_domains and parsed_next.netloc not in allowed_domains:
                break
            if next_url in seen:
                break
            seen.add(next_url)
            urls.append(next_url)
            url = next_url

        return urls[:max_pages]


class FallbackStrategy(AcquisitionStrategy):
    """
    Used when the primary strategy's extraction yields nothing usable.
    Goes straight to BrowserStrategy (async Playwright) to avoid the
    scrapling/camoufox dependency and sync-Playwright-in-asyncio conflict.
    """

    name = "fallback"

    def __init__(self):
        self._browser = BrowserStrategy()

    async def fetch(self, url: str, portal_config: Dict[str, Any]) -> str:
        return await self._browser.fetch(url, portal_config)


# --------------------------------------------------------------------------
# Strategy router
# --------------------------------------------------------------------------

class StrategyRouter:
    """Selects an acquisition strategy based on crawl_mode and prior failures."""

    def __init__(self):
        self._http = HttpStrategy()
        self._browser = BrowserStrategy()
        self._stealth = StealthStrategy()
        self._deep = DeepCrawlStrategy()
        self._fallback = FallbackStrategy()

    def primary_for(self, portal_config: Dict[str, Any]) -> AcquisitionStrategy:
        mode = portal_config["crawl_mode"]
        anti_bot = portal_config.get("anti_bot_profile", "none")

        if anti_bot and anti_bot != "none":
            return self._stealth
        if mode == "http":
            return self._http
        if mode == "browser":
            return self._browser
        if mode in ("deep", "hybrid"):
            return self._browser if _HAS_PLAYWRIGHT else self._http
        return self._http

    @property
    def deep(self) -> DeepCrawlStrategy:
        return self._deep

    @property
    def fallback(self) -> FallbackStrategy:
        return self._fallback


# --------------------------------------------------------------------------
# Extraction (selector / schema based, never invents selectors)
# --------------------------------------------------------------------------

class Extractor:
    """Parses raw HTML into item dicts using portal-provided selectors/schema only."""

    @staticmethod
    def extract_listing_items(html: str, portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            from selectolax.lexbor import LexborHTMLParser as _Parser  # type: ignore
        except ImportError:
            from bs4 import BeautifulSoup  # type: ignore
            return Extractor._extract_with_bs4(html, portal_config)

        item_selectors = portal_config.get("item_selectors") or {}
        listing_selectors = portal_config.get("listing_selectors") or {}
        container_sel = listing_selectors.get("item_container")
        if not container_sel:
            return []

        tree = _Parser(html)
        items = []
        for node in tree.css(container_sel):
            item = {"raw_text": node.text(strip=True)}
            for field_name, sel in item_selectors.items():
                found = node.css_first(sel)
                item[field_name] = found.text(strip=True) if found else None
            items.append(item)
        return items

    @staticmethod
    def _extract_with_bs4(html: str, portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        from bs4 import BeautifulSoup  # type: ignore

        item_selectors = portal_config.get("item_selectors") or {}
        listing_selectors = portal_config.get("listing_selectors") or {}
        container_sel = listing_selectors.get("item_container")
        if not container_sel:
            return []

        soup = BeautifulSoup(html, "html.parser")
        items = []
        for node in soup.select(container_sel):
            item = {"raw_text": node.get_text(strip=True)}
            for field_name, sel in item_selectors.items():
                found = node.select_one(sel)
                item[field_name] = found.get_text(strip=True) if found else None
            items.append(item)
        return items


# --------------------------------------------------------------------------
# Normalization
# --------------------------------------------------------------------------

def normalize_item(
    raw_item: Dict[str, Any], source_url: str, portal_name: str, crawl_mode_used: str
) -> ScrapedItem:
    """Map a raw extracted dict into the shared ScrapedItem model."""
    extracted_fields = ("title", "price", "location", "description", "created_at")
    present = sum(1 for f in extracted_fields if raw_item.get(f))
    confidence = round(present / len(extracted_fields), 3) if present else 0.0

    return ScrapedItem(
        source_portal=portal_name,
        source_url=source_url,
        title=raw_item.get("title"),
        price=raw_item.get("price"),
        location=raw_item.get("location"),
        description=raw_item.get("description"),
        created_at=raw_item.get("created_at"),
        raw_text=raw_item.get("raw_text"),
        metadata={k: v for k, v in raw_item.items() if k not in extracted_fields and k != "raw_text"},
        confidence=confidence,
        crawl_mode_used=crawl_mode_used,
    )


# --------------------------------------------------------------------------
# SmartScraperEngine - the single public interface
# --------------------------------------------------------------------------

class SmartScraperEngine:
    """
    Unified async crawling service.

    Usage:
        engine = SmartScraperEngine()
        items = await engine.crawl_bot(bot_name, portal_config)
    """

    def __init__(
        self,
        max_concurrency_per_domain: int = 2,
        respect_robots: bool = True,
        retries: int = 3,
        retry_base_delay: float = 1.5,
    ):
        self.router = StrategyRouter()
        self.throttle = DomainThrottle(max_concurrency_per_domain, respect_robots)
        self.retries = retries
        self.retry_base_delay = retry_base_delay
        self.stats: Dict[str, PortalStats] = {}
        self._seen_canonical: set = set()

    def get_stats(self, portal_name: str) -> Dict[str, Any]:
        stats = self.stats.get(portal_name)
        return stats.summary() if stats else {}

    async def crawl_bot(self, bot_name: str, portal_config: Optional[Dict[str, Any]]) -> List[ScrapedItem]:
        """Single public entry point. Skips cleanly if config is missing/invalid."""
        is_valid, reason = validate_portal_config(portal_config)
        if not is_valid:
            logger.warning(
                "Skipping crawl bot=%s portal_config_invalid reason=%s", bot_name, reason
            )
            return []

        portal_name = portal_config["portal_name"]
        stats = self.stats.setdefault(portal_name, PortalStats(portal_name=portal_name))

        if portal_config["crawl_mode"] == "jobspy":
            return await self._crawl_jobspy(portal_name, portal_config, stats)

        if portal_config["crawl_mode"] == "gulftalent":
            return await self._crawl_github_client(portal_name, portal_config, stats, "gulftalent")

        if portal_config["crawl_mode"] in ("visa_bulletin", "visa_wiki"):
            return await self._crawl_github_client(portal_name, portal_config, stats, "visa")

        if portal_config["crawl_mode"] == "university_api":
            return await self._crawl_github_client(portal_name, portal_config, stats, "university")

        if portal_config["crawl_mode"] == "qs_rankings":
            return await self._crawl_github_client(portal_name, portal_config, stats, "qs")

        if portal_config["crawl_mode"] == "passport_index":
            return await self._crawl_github_client(portal_name, portal_config, stats, "passport_index")

        if portal_config["crawl_mode"] == "uk_sponsored_jobs":
            return await self._crawl_github_client(portal_name, portal_config, stats, "uk_jobs")

        if portal_config["crawl_mode"] == "eu_visa_policy":
            return await self._crawl_github_client(portal_name, portal_config, stats, "eu_visa")

        if portal_config["crawl_mode"] == "car_auction":
            return await self._crawl_github_client(portal_name, portal_config, stats, "car_auction")

        if portal_config["crawl_mode"] == "admissions_data":
            return await self._crawl_github_client(portal_name, portal_config, stats, "admissions")

        if portal_config["crawl_mode"] == "ats_jobs":
            return await self._crawl_github_client(portal_name, portal_config, stats, "ats_jobs")

        if portal_config["crawl_mode"] == "admissions_news":
            return await self._crawl_github_client(portal_name, portal_config, stats, "admissions_news")

        if portal_config["crawl_mode"] == "global_admissions":
            return await self._crawl_github_client(portal_name, portal_config, stats, "global_admissions")

        try:
            urls = await self._resolve_urls(portal_config, stats)
        except Exception as exc:
            stats.record_failure(f"url_discovery:{type(exc).__name__}")
            logger.error("URL discovery failed for portal=%s: %s", portal_name, exc)
            return []

        delay_range = portal_config.get("delay_range") or [0, 0]
        items: List[ScrapedItem] = []

        # Per-portal robots bypass: respect_robots=False in portal config overrides engine default
        portal_respect_robots = portal_config.get("respect_robots", True)

        for url in urls:
            if portal_respect_robots and not await self.throttle.is_allowed(url):
                stats.record_failure("robots_disallowed")
                continue

            async with self.throttle.slot(url):
                await asyncio.sleep(random.uniform(*delay_range))
                page_items = await self._fetch_and_extract(url, portal_config, stats, bot_name)
                items.extend(page_items)

        deduped = self._dedupe_batch(items, stats)
        logger.info(
            "crawl_bot complete bot=%s portal=%s pages=%d items=%d duplicates=%d",
            bot_name, portal_name, stats.pages_fetched, len(deduped), stats.duplicates_dropped,
        )
        return deduped

    async def _resolve_urls(self, portal_config: Dict[str, Any], stats: PortalStats) -> List[str]:
        mode = portal_config["crawl_mode"]
        if mode in ("deep", "hybrid") and (portal_config.get("pagination_selectors") or portal_config.get("max_depth", 1) > 1):
            return await self.router.deep.discover(portal_config, stats)
        return list(portal_config["start_urls"])[: portal_config.get("max_pages", len(portal_config["start_urls"]))]

    async def _fetch_and_extract(
        self, url: str, portal_config: Dict[str, Any], stats: PortalStats, bot_name: str
    ) -> List[ScrapedItem]:
        strategy = self.router.primary_for(portal_config)

        async def _do_fetch():
            return await strategy.fetch(url, portal_config)

        try:
            html = await _retry_with_backoff(_do_fetch, self.retries, self.retry_base_delay, stats, f"fetch:{strategy.name}")
            stats.pages_fetched += 1
        except Exception as exc:
            logger.warning("Primary strategy %s failed for %s; trying fallback: %s", strategy.name, url, exc)
            try:
                html = await self.router.fallback.fetch(url, portal_config)
                stats.pages_fetched += 1
                strategy = self.router.fallback
            except Exception as fallback_exc:
                stats.record_failure(f"fetch_exhausted:{type(fallback_exc).__name__}")
                logger.error("All strategies failed for url=%s bot=%s: %s", url, bot_name, fallback_exc)
                return []

        raw_items = Extractor.extract_listing_items(html, portal_config)
        if not raw_items:
            stats.record_failure("no_items_extracted")
            return []

        normalized = [
            normalize_item(raw, url, portal_config["portal_name"], strategy.name) for raw in raw_items
        ]
        for item in normalized:
            stats.confidence_samples.append(item.confidence)
        stats.items_extracted += len(normalized)
        return normalized

    def _dedupe_batch(self, items: List[ScrapedItem], stats: PortalStats) -> List[ScrapedItem]:
        """Dedupe by canonical URL + normalized title/price/location."""
        deduped = []
        for item in items:
            key = (
                _canonical_url(item.source_url),
                (item.title or "").strip().lower(),
                (item.price or "").strip().lower(),
                (item.location or "").strip().lower(),
            )
            if key in self._seen_canonical:
                stats.duplicates_dropped += 1
                continue
            self._seen_canonical.add(key)
            deduped.append(item)
        return deduped

    async def _crawl_jobspy(
        self, portal_name: str, portal_config: Dict[str, Any], stats: PortalStats
    ) -> List[ScrapedItem]:
        from core.jobspy_client import fetch_jobspy  # local import to keep optional

        raw_records = await fetch_jobspy(portal_config)
        if not raw_records:
            stats.record_failure("jobspy_no_results")
            return []

        items: List[ScrapedItem] = []
        for raw in raw_records:
            source_url = raw.pop("source_url", "") or portal_config.get("start_urls", [""])[0] if portal_config.get("start_urls") else ""
            item = normalize_item(raw, source_url, portal_name, "jobspy")
            items.append(item)

        stats.items_extracted += len(items)
        stats.pages_fetched += 1
        deduped = self._dedupe_batch(items, stats)
        logger.info(
            "crawl_bot[jobspy] complete portal=%s items=%d duplicates=%d",
            portal_name, len(deduped), stats.duplicates_dropped,
        )
        return deduped

    async def _crawl_github_client(
        self,
        portal_name: str,
        portal_config: Dict[str, Any],
        stats: PortalStats,
        client_type: str,
    ) -> List[ScrapedItem]:
        """Generic dispatcher for GitHub-direct Python clients (no Apify)."""
        try:
            if client_type == "gulftalent":
                from core.gulftalent_client import fetch_gulftalent
                raw_records = await fetch_gulftalent(portal_config)
                mode_tag = "gulftalent"
            elif client_type == "visa":
                from core.visa_client import fetch_visa_data
                raw_records = await fetch_visa_data(portal_config)
                mode_tag = portal_config.get("crawl_mode", "visa_bulletin")
            elif client_type == "university":
                from core.university_client import fetch_university_data
                raw_records = await fetch_university_data(portal_config)
                mode_tag = "university_api"
            elif client_type == "qs":
                from core.qs_client import fetch_qs_data
                raw_records = await fetch_qs_data(portal_config)
                mode_tag = "qs_rankings"
            elif client_type == "passport_index":
                from core.passport_index_client import fetch_passport_index
                raw_records = await fetch_passport_index(portal_config)
                mode_tag = "passport_index"
            elif client_type == "uk_jobs":
                from core.uk_jobs_client import fetch_uk_sponsored_jobs
                raw_records = await fetch_uk_sponsored_jobs(portal_config)
                mode_tag = "uk_sponsored_jobs"
            elif client_type == "eu_visa":
                from core.eu_visa_client import fetch_eu_visa_data
                raw_records = await fetch_eu_visa_data(portal_config)
                mode_tag = "eu_visa_policy"
            elif client_type == "car_auction":
                from core.car_auction_client import fetch_car_auction_data
                raw_records = await fetch_car_auction_data(portal_config)
                mode_tag = "car_auction"
            elif client_type == "admissions":
                from core.admissions_client import fetch_admissions_data
                raw_records = await fetch_admissions_data(portal_config)
                mode_tag = "admissions_data"
            elif client_type == "ats_jobs":
                from core.ats_client import fetch_ats_jobs
                raw_records = await fetch_ats_jobs(portal_config)
                mode_tag = "ats_jobs"
            elif client_type == "admissions_news":
                from core.admissions_news_client import fetch_admissions_news
                raw_records = await fetch_admissions_news(portal_config)
                mode_tag = "admissions_news"
            elif client_type == "global_admissions":
                from core.global_admissions_client import fetch_global_admissions
                raw_records = await fetch_global_admissions(portal_config)
                mode_tag = "global_admissions"
            else:
                logger.error("_crawl_github_client: unknown client_type=%s", client_type)
                return []
        except Exception as exc:
            stats.record_failure(f"{client_type}_error:{type(exc).__name__}")
            logger.error("_crawl_github_client client=%s portal=%s error: %s", client_type, portal_name, exc)
            return []

        if not raw_records:
            stats.record_failure(f"{client_type}_no_results")
            return []

        items: List[ScrapedItem] = []
        for raw in raw_records:
            source_url = raw.pop("source_url", "") or ""
            item = normalize_item(raw, source_url, portal_name, mode_tag)
            items.append(item)

        stats.items_extracted += len(items)
        stats.pages_fetched += 1
        deduped = self._dedupe_batch(items, stats)
        logger.info(
            "crawl_bot[%s] complete portal=%s items=%d duplicates=%d",
            mode_tag, portal_name, len(deduped), stats.duplicates_dropped,
        )
        return deduped

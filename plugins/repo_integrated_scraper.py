"""
repo_integrated_scraper.py
AI Sales Intelligence — Integration of stealth GitHub repos with graceful fallback.

Priority chain (each degrades to the next if unavailable):
  1. Agentic Stealth Browser  (github.com/shanewas/agentic-stealth-browser)
  2. LinkedIn Spider          (github.com/vertexcover-io/linkedin-spider)
  3. Custom Playwright        (basic stealth)
  4. → returns []  (caller then falls back to Apify / static)

IMPORTANT: browser scraping of LinkedIn/Instagram/Facebook is ToS-sensitive and
selectors go stale. This module NEVER raises on missing deps or stale DOM — it
returns [] so the CRM stays reliable. Install the optional packages to enable it:
    pip install playwright && playwright install chromium
    pip install git+https://github.com/shanewas/agentic-stealth-browser.git
    pip install git+https://github.com/vertexcover-io/linkedin-spider.git
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── LeadRecord (aligned with plugins/scrapers_analyzer.py) ────────────────────
class LeadRecord(BaseModel):
    lead_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    source: str
    source_url: str
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    enrichment_data: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    status: str = "new"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True


# ── Optional stealth backends (graceful) ──────────────────────────────────────
AGENTIC_AVAILABLE = False
LINKEDIN_SPIDER_AVAILABLE = False
PLAYWRIGHT_AVAILABLE = False
AgentBrowser = None
LinkedInSpiderScraper = None
async_playwright = None

try:  # Agentic Stealth Browser — package import path may vary across versions
    from agentic_stealth_browser import AgentBrowser as _AB  # type: ignore
    AgentBrowser = _AB
    AGENTIC_AVAILABLE = True
    logger.info("repo_integrated: Agentic Stealth Browser loaded")
except Exception:
    logger.info("repo_integrated: Agentic Stealth Browser not installed")

try:
    from linkedin_spider import LinkedInScraper as _LSS  # type: ignore
    LinkedInSpiderScraper = _LSS
    LINKEDIN_SPIDER_AVAILABLE = True
    logger.info("repo_integrated: LinkedIn Spider loaded")
except Exception:
    logger.info("repo_integrated: LinkedIn Spider not installed")

try:
    from playwright.async_api import async_playwright as _AP  # type: ignore
    async_playwright = _AP
    PLAYWRIGHT_AVAILABLE = True
    logger.info("repo_integrated: Playwright loaded (fallback)")
except Exception:
    logger.info("repo_integrated: Playwright not installed")


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


def random_delay(min_sec: float = 2.0, max_sec: float = 7.0) -> float:
    return random.uniform(min_sec, max_sec)


def stealth_available() -> bool:
    return AGENTIC_AVAILABLE or LINKEDIN_SPIDER_AVAILABLE or PLAYWRIGHT_AVAILABLE


def _to_float(s):
    try:
        return float(str(s).replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


def _to_int(s):
    try:
        return int(re.sub(r"[^\d]", "", str(s)) or 0) or None
    except (ValueError, TypeError):
        return None


# ── LinkedIn (agentic → spider → custom playwright) ───────────────────────────
class LinkedInScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mode = config.get("mode", "agentic")

    async def fetch_leads(self, tenant_id: UUID, limit: int = 10, keyword: str = "cto") -> List[LeadRecord]:
        try:
            # 0. Vendored cookie-auth scraper (Playwright, li_at) — preferred when a
            #    LinkedIn session cookie is configured; the agentic/spider GitHub
            #    packages are not installed, so this is the real working path.
            vendored = await self._fetch_vendored(tenant_id, limit, keyword)
            if vendored:
                return vendored
            if self.mode == "agentic" and AGENTIC_AVAILABLE:
                return await self._fetch_agentic(tenant_id, limit, keyword)
            if self.mode == "spider" and LINKEDIN_SPIDER_AVAILABLE:
                return await self._fetch_spider(tenant_id, limit, keyword)
            if AGENTIC_AVAILABLE:
                return await self._fetch_agentic(tenant_id, limit, keyword)
            if LINKEDIN_SPIDER_AVAILABLE:
                return await self._fetch_spider(tenant_id, limit, keyword)
            if PLAYWRIGHT_AVAILABLE:
                return await self._fetch_custom(tenant_id, limit, keyword)
        except Exception as exc:
            logger.warning("repo_integrated LinkedIn failed: %s", exc)
        return []

    async def _fetch_vendored(self, tenant_id: UUID, limit: int, keyword: str) -> List[LeadRecord]:
        """Vendored cookie-auth LinkedIn scraper (plugins/linkedin_vendor.py)."""
        try:
            from plugins.linkedin_vendor import LinkedInVendorScraper, vendor_available
            if not vendor_available():
                return []
            scraper = LinkedInVendorScraper(headless=self.config.get("headless", True),
                                            proxy=self.config.get("proxy"))
            profiles = await scraper.search_people(keyword, limit=limit)
            out: List[LeadRecord] = []
            for pr in profiles or []:
                out.append(LeadRecord(
                    tenant_id=tenant_id, name=pr.get("name", "Unknown"), source="linkedin",
                    source_url=pr.get("profile_url") or f"linkedin_{uuid4()}",
                    title=pr.get("headline", ""), company=pr.get("company", ""),
                    enrichment_data={"linkedin_profile": pr}))
            return out
        except Exception as exc:
            logger.warning("repo_integrated LinkedIn vendored failed: %s", exc)
            return []

    async def _fetch_agentic(self, tenant_id: UUID, limit: int, keyword: str) -> List[LeadRecord]:
        results: List[LeadRecord] = []
        async with AgentBrowser(session_name="linkedin_session") as browser:
            await browser.launch(headless=self.config.get("headless", True))
            url = f"https://www.linkedin.com/search/results/people/?keywords={keyword.replace(' ', '%20')}"
            await browser.safe_goto(url)
            await asyncio.sleep(random_delay(3, 5))
            for _ in range(random.randint(2, 4)):
                await browser.page.mouse.wheel(0, random.randint(400, 800))
                await asyncio.sleep(random_delay(1, 2))
            data = await browser.page.evaluate(
                """() => {
                    const items = document.querySelectorAll('.search-result__info, .entity-result__content');
                    return Array.from(items).slice(0, 10).map(el => ({
                        name: (el.querySelector('.actor-name, .entity-result__title-text')||{}).innerText || 'Unknown',
                        title: (el.querySelector('.subtitle, .entity-result__primary-subtitle')||{}).innerText || '',
                        url: (el.querySelector('a')||{}).href || ''
                    }));
                }"""
            )
            for item in (data or [])[:limit]:
                results.append(LeadRecord(
                    tenant_id=tenant_id, name=item.get("name", "Unknown"), source="linkedin",
                    source_url=item.get("url") or f"linkedin_{uuid4()}",
                    title=item.get("title", ""), enrichment_data={"raw": item},
                ))
        return results

    async def _fetch_spider(self, tenant_id: UUID, limit: int, keyword: str) -> List[LeadRecord]:
        scraper = LinkedInSpiderScraper(headless=self.config.get("headless", True),
                                        proxy=self.config.get("proxy"))
        profiles = await scraper.search_profiles(keyword, limit=limit)
        results: List[LeadRecord] = []
        for profile in (profiles or []):
            results.append(LeadRecord(
                tenant_id=tenant_id, name=profile.get("name", "Unknown"), source="linkedin",
                source_url=profile.get("profile_url") or f"linkedin_{uuid4()}",
                title=profile.get("headline", ""), company=profile.get("company", ""),
                enrichment_data={"linkedin_profile": profile},
            ))
        return results

    async def _fetch_custom(self, tenant_id: UUID, limit: int, keyword: str) -> List[LeadRecord]:
        results: List[LeadRecord] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.config.get("headless", True),
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": random.choice([1280, 1440]), "height": 900},
            )
            page = await context.new_page()
            url = f"https://www.linkedin.com/search/results/people/?keywords={keyword.replace(' ', '%20')}"
            await page.goto(url, timeout=45000)
            await asyncio.sleep(random_delay(3, 5))
            cards = await page.query_selector_all(".search-result__info, .entity-result__content")
            for card in cards[:limit]:
                name_elem = await card.query_selector(".actor-name, .entity-result__title-text")
                name = (await name_elem.inner_text()) if name_elem else "Unknown"
                title_elem = await card.query_selector(".subtitle, .entity-result__primary-subtitle")
                title = (await title_elem.inner_text()) if title_elem else ""
                link_elem = await card.query_selector("a")
                href = (await link_elem.get_attribute("href")) if link_elem else ""
                profile_url = href if href.startswith("http") else f"https://www.linkedin.com{href}"
                results.append(LeadRecord(
                    tenant_id=tenant_id, name=name.strip(), source="linkedin",
                    source_url=profile_url, title=title.strip(),
                    enrichment_data={"raw": {"name": name, "title": title}},
                ))
            await browser.close()
        return results


# ── Instagram (agentic → custom playwright) ───────────────────────────────────
class InstagramScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def fetch_leads(self, tenant_id: UUID, limit: int = 10, username: str = None) -> List[LeadRecord]:
        username = username or "google"
        try:
            if AGENTIC_AVAILABLE:
                return await self._fetch_agentic(tenant_id, username)
            if PLAYWRIGHT_AVAILABLE:
                return await self._fetch_custom(tenant_id, username)
        except Exception as exc:
            logger.warning("repo_integrated Instagram failed: %s", exc)
        return []

    async def _fetch_agentic(self, tenant_id: UUID, username: str) -> List[LeadRecord]:
        async with AgentBrowser(session_name="instagram_session") as browser:
            await browser.launch(headless=self.config.get("headless", True))
            url = f"https://www.instagram.com/{username}/"
            await browser.safe_goto(url)
            await asyncio.sleep(random_delay(3, 5))
            data = await browser.page.evaluate(
                """() => {
                    const name = (document.querySelector('header h2, header h1')||{}).innerText || 'Unknown';
                    const bio = (document.querySelector('header section')||{}).innerText || '';
                    return { name, bio };
                }"""
            )
            return [LeadRecord(
                tenant_id=tenant_id, name=(data or {}).get("name", username), source="instagram",
                source_url=url, title=(data or {}).get("bio", "")[:200],
                enrichment_data={"instagram_data": data},
            )]

    async def _fetch_custom(self, tenant_id: UUID, username: str) -> List[LeadRecord]:
        url = f"https://www.instagram.com/{username}/"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.config.get("headless", True))
            page = await browser.new_page()
            await page.goto(url)
            await asyncio.sleep(random_delay(3, 5))

            # Clean display name from og:title (e.g. "Nike (@nike) • Instagram ...")
            display_name = username
            try:
                og = await page.get_attribute('meta[property="og:title"]', "content")
                if og:
                    display_name = re.split(r"\s*[\(•|]", og)[0].strip() or username
            except Exception:
                pass

            header_txt = ""
            try:
                header_txt = await page.inner_text("header")
            except Exception:
                pass
            await browser.close()

            # Parse followers + bio (last non-metric line) from the header blob
            followers = ""
            m = re.search(r"([\d.,]+[KMB]?)\s+followers", header_txt, re.I)
            if m:
                followers = m.group(1)
            lines = [ln.strip() for ln in header_txt.splitlines() if ln.strip()]
            bio_lines = [ln for ln in lines
                         if not re.search(r"posts|followers|following", ln, re.I)
                         and ln.lower() not in (username.lower(), display_name.lower())]
            bio = " ".join(bio_lines[:3])[:220]

            return [LeadRecord(
                tenant_id=tenant_id, name=display_name, source="instagram", source_url=url,
                title=bio, company=display_name,
                enrichment_data={"username": username, "followers": followers,
                                 "bio": bio, "instagram_header": header_txt[:500]},
            )]


# ── Facebook (agentic only; else empty) ───────────────────────────────────────
class FacebookScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def fetch_leads(self, tenant_id: UUID, limit: int = 10, page_id: str = "cocacola") -> List[LeadRecord]:
        if not AGENTIC_AVAILABLE:
            return []
        results: List[LeadRecord] = []
        try:
            async with AgentBrowser(session_name="facebook_session") as browser:
                await browser.launch(headless=self.config.get("headless", True))
                await browser.safe_goto(f"https://www.facebook.com/{page_id}")
                await asyncio.sleep(random_delay(4, 7))
                for _ in range(random.randint(2, 4)):
                    await browser.page.mouse.wheel(0, random.randint(500, 900))
                    await asyncio.sleep(random_delay(1, 2))
                posts = await browser.page.evaluate(
                    """() => {
                        const items = document.querySelectorAll('[role="article"]');
                        return Array.from(items).slice(0, 10).map(el => ({
                            text: el.innerText.slice(0, 300),
                            timestamp: (el.querySelector('time')||{}).innerText || ''
                        }));
                    }"""
                )
                for post in (posts or [])[:limit]:
                    results.append(LeadRecord(
                        tenant_id=tenant_id, name="Facebook User", source="facebook",
                        source_url=f"fb_post_{uuid4()}", title=post.get("text", "")[:200],
                        enrichment_data={"post": post},
                    ))
        except Exception as exc:
            logger.warning("repo_integrated Facebook failed: %s", exc)
        return results


# ── Shared Playwright helpers (consent / CAPTCHA aware) ───────────────────────
async def _new_stealth_page(headless: bool):
    """Launch a stealth chromium page. Caller must close browser via returned handle."""
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": random.choice([1280, 1366, 1440]), "height": 900},
        locale="en-US",
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    page = await context.new_page()
    return p, browser, page


async def _dismiss_google_consent(page) -> None:
    """Dismiss Google's cookie-consent interstitial (privacy-preserving: reject)."""
    for sel in ('button:has-text("Reject all")', 'button:has-text("Reject")',
                'button:has-text("Accept all")', '[aria-label*="Reject"]'):
        try:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(random_delay(1, 2))
                return
        except Exception:
            continue


async def _google_blocked(page) -> bool:
    """True if Google is showing a CAPTCHA / 'unusual traffic' wall. We NEVER solve it."""
    try:
        body = (await page.inner_text("body"))[:2000].lower()
    except Exception:
        return False
    return any(k in body for k in ("unusual traffic", "not a robot", "recaptcha",
                                   "detected unusual", "verify you're human"))


# ── Google Maps business search (Playwright, no API key) ──────────────────────
class GoogleMapsScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def fetch_leads(self, tenant_id: UUID, limit: int = 10,
                          keyword: str = "marketing agency", location: str = "Dubai") -> List[LeadRecord]:
        if not PLAYWRIGHT_AVAILABLE:
            return []
        results: List[LeadRecord] = []
        p = browser = None
        try:
            p, browser, page = await _new_stealth_page(self.config.get("headless", True))
            query = f"{keyword} in {location}".replace(" ", "+")
            await page.goto(f"https://www.google.com/maps/search/{query}?hl=en&gl=us", timeout=45000)
            await _dismiss_google_consent(page)
            await asyncio.sleep(random_delay(2, 3))
            # Results feed
            try:
                await page.wait_for_selector('a.hfpxzc, a[href*="/maps/place/"]', timeout=10000)
            except Exception:
                pass
            for _ in range(2):
                await page.mouse.wheel(0, 1800)
                await asyncio.sleep(random_delay(0.8, 1.4))
            # Extract name + rating-label + card text per result (pain signals).
            items = await page.evaluate(
                """() => {
                    const out = [];
                    document.querySelectorAll('a.hfpxzc').forEach(a => {
                        const card = a.closest('.Nv2PK, .bfdHYd, [role="article"]') || a.parentElement;
                        const ratingImg = card ? card.querySelector('[role="img"][aria-label*="star"], [aria-label*="Review"]') : null;
                        out.push({
                            name: a.getAttribute('aria-label') || '',
                            href: a.getAttribute('href') || '',
                            rating_label: ratingImg ? ratingImg.getAttribute('aria-label') : '',
                            text: card ? card.innerText : ''
                        });
                    });
                    return out;
                }"""
            )
            seen = set()
            for it in (items or []):
                if len(results) >= limit:
                    break
                name, href = (it.get("name") or "").strip(), it.get("href") or ""
                if not name or href in seen:
                    continue
                seen.add(href)
                text = it.get("text") or ""
                rlabel = it.get("rating_label") or ""
                # Rating + reviews: try aria-label ("4.9 stars 123 Reviews"), then
                # card text ("4.9(123)" or "4.9 (1,234)").
                rating = reviews = None
                rm = re.search(r"([\d.]+)\s*stars?", rlabel)
                cm = re.search(r"([\d,]+)\s*[Rr]eview", rlabel)
                if rm:
                    rating = _to_float(rm.group(1))
                if cm:
                    reviews = _to_int(cm.group(1))
                if rating is None:
                    tm = re.search(r"\b([1-5]\.\d)\b", text)
                    if tm:
                        rating = _to_float(tm.group(1))
                if reviews is None:
                    vm = re.search(r"\(([\d,]{2,})\)", text)     # "(1,234)" near rating
                    if vm:
                        reviews = _to_int(vm.group(1))
                # Category = first meaningful card line (skip name / numbers / ads)
                cat = ""
                for ln in text.splitlines():
                    ln = ln.strip()
                    low = ln.lower()
                    if (ln and ln != name and "review" not in low and low != "sponsored"
                            and not re.match(r"^[\d.,()★\s·]+$", ln)
                            and not name.startswith(ln)):
                        cat = ln.split("·")[0].strip()
                        break
                desc = f"{cat or keyword} · {location}"
                if rating:
                    desc += f" · {rating}★ ({reviews} reviews)"
                results.append(LeadRecord(
                    tenant_id=tenant_id, name=name, source="google_maps",
                    source_url=href, title=desc, company=name,
                    enrichment_data={"place": {"name": name, "keyword": keyword, "category": cat,
                                               "location": location, "url": href,
                                               "rating": rating, "review_count": reviews}},
                ))
        except Exception as exc:
            logger.warning("repo_integrated GoogleMaps failed: %s", exc)
        finally:
            if browser:
                await browser.close()
            if p:
                await p.stop()
        return results


# ── Instagram / Facebook posts via Google search (Playwright) ─────────────────
class GoogleSocialScraper:
    """Find IG/FB public posts through Google SERP (site: search), extract snippets
    as post text. Optionally opens each result to pull post text + top comments."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.site = config.get("site", "instagram.com")      # instagram.com | facebook.com
        self.source = config.get("source", "instagram")
        self.open_posts = config.get("open_posts", False)     # open each URL for comments

    async def fetch_leads(self, tenant_id: UUID, limit: int = 5,
                          query: str = "marketing") -> List[LeadRecord]:
        if not PLAYWRIGHT_AVAILABLE:
            return []
        results: List[LeadRecord] = []
        p = browser = None
        try:
            p, browser, page = await _new_stealth_page(self.config.get("headless", True))
            q = f"site:{self.site} {query}".replace(" ", "+")
            await page.goto(f"https://www.google.com/search?q={q}&num=20", timeout=45000)
            await _dismiss_google_consent(page)
            await asyncio.sleep(random_delay(2, 4))
            if await _google_blocked(page):
                logger.warning("repo_integrated GoogleSocial: blocked by Google (CAPTCHA) -> []")
                return []
            # 1. Extract SERP results (fast — snippet already carries post text)
            blocks = await page.query_selector_all("div.g, div.MjjYud")
            harvested = []  # (name, href, snippet)
            for b in blocks:
                if len(harvested) >= limit:
                    break
                try:
                    link = await b.query_selector("a")
                    href = await link.get_attribute("href") if link else None
                    if not href or self.site not in href:
                        continue
                    h3 = await b.query_selector("h3")
                    title = (await h3.inner_text()) if h3 else self.source
                    snip_el = await b.query_selector("div[data-sncf], .VwiC3b, .lyLwlc")
                    snippet = (await snip_el.inner_text()) if snip_el else ""
                    harvested.append((title.split("•")[0].strip()[:80] or self.source, href, snippet))
                except Exception:
                    continue

            # 2. Optionally open each post CONCURRENTLY for comments (bounded)
            comments_map = {}
            if self.open_posts and harvested:
                async def grab(href, fallback):
                    return href, await self._open_post(page.context, href, fallback)
                try:
                    done = await asyncio.wait_for(
                        asyncio.gather(*(grab(h, s) for _, h, s in harvested[:limit]),
                                       return_exceptions=True),
                        timeout=22,
                    )
                    for item in done:
                        if isinstance(item, tuple):
                            href, (txt, cmts) = item
                            comments_map[href] = (txt, cmts)
                except Exception:
                    pass

            for name, href, snippet in harvested:
                txt, cmts = comments_map.get(href, (snippet, []))
                results.append(LeadRecord(
                    tenant_id=tenant_id, name=name, source=self.source,
                    source_url=href, title=(txt or snippet)[:220],
                    enrichment_data={"post": {"message": txt or snippet, "url": href,
                                              "comments": cmts, "query": query}},
                ))
        except Exception as exc:
            logger.warning("repo_integrated GoogleSocial failed: %s", exc)
        finally:
            if browser:
                await browser.close()
            if p:
                await p.stop()
        return results

    async def _open_post(self, context, url: str, fallback_text: str):
        """Open a post URL and pull text + a few comments (fast, best-effort)."""
        page = None
        try:
            page = await context.new_page()
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            await asyncio.sleep(random_delay(0.5, 1.5))
            text = fallback_text
            try:
                og = await page.get_attribute('meta[property="og:description"]', "content")
                if og:
                    text = og
            except Exception:
                pass
            comments = []
            try:
                nodes = await page.query_selector_all('ul li span, [role="article"] span')
                for n in nodes[:8]:
                    t = (await n.inner_text()).strip()
                    if 8 < len(t) < 200:
                        comments.append(t)
            except Exception:
                pass
            return text, comments[:5]
        except Exception:
            return fallback_text, []
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass


# ── Pipeline ──────────────────────────────────────────────────────────────────
async def run_pipeline(
    tenant_id: UUID,
    sources: List[str] = None,
    limit_per_source: int = 3,
    targets: Dict[str, Any] = None,
) -> List[LeadRecord]:
    """Run browser scrapers against configurable targets.

    targets = {
        "gmaps_keyword": "marketing agency", "gmaps_location": "Dubai",
        "social_query": "looking for marketing",   # Google site: query for IG/FB
        "open_posts": False,                        # open each post for comments (slower)
        "linkedin_keyword": "cto",
        "headless": True,
    }
    Sources: "google_maps", "instagram", "facebook", "linkedin".
    IG/FB are scraped THROUGH Google search (site: query) — avoids login walls.
    Returns [] gracefully if no backend is available.
    """
    if not stealth_available():
        logger.info("repo_integrated: no stealth backend available -> []")
        return []

    sources = sources or ["google_maps", "instagram", "facebook"]
    t = targets or {}
    headless = t.get("headless", True)
    gk = t.get("gmaps_keyword", "marketing agency")
    gl = t.get("gmaps_location", "Dubai")
    social_q = t.get("social_query", "marketing")
    open_posts = bool(t.get("open_posts", False))
    li_kw = t.get("linkedin_keyword", "cto")

    tasks = []
    for s in sources:
        if s == "google_maps":
            tasks.append(GoogleMapsScraper({"headless": headless})
                         .fetch_leads(tenant_id, limit=limit_per_source, keyword=gk, location=gl))
        elif s == "instagram":
            tasks.append(GoogleSocialScraper({"headless": headless, "site": "instagram.com",
                                              "source": "instagram", "open_posts": open_posts})
                         .fetch_leads(tenant_id, limit=limit_per_source, query=social_q))
        elif s == "facebook":
            tasks.append(GoogleSocialScraper({"headless": headless, "site": "facebook.com",
                                              "source": "facebook", "open_posts": open_posts})
                         .fetch_leads(tenant_id, limit=limit_per_source, query=social_q))
        elif s == "linkedin":
            tasks.append(LinkedInScraper({"mode": "agentic", "headless": headless})
                         .fetch_leads(tenant_id, limit=limit_per_source, keyword=li_kw))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_leads: List[LeadRecord] = []
    for leads in results:
        if isinstance(leads, list):
            all_leads.extend(leads)
        else:
            logger.warning("repo_integrated scraper error: %s", leads)

    seen, unique = set(), []
    for lead in all_leads:
        if lead.source_url not in seen:
            seen.add(lead.source_url)
            unique.append(lead)
    logger.info("repo_integrated: returned %d unique leads", len(unique))
    return unique

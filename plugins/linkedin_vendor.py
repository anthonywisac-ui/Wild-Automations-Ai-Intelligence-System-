"""
linkedin_vendor.py — self-contained LinkedIn people scraper (vendored).

Pattern adopted from vertexcover-io/linkedin-spider (cookie auth + stealth +
human-like delays), re-implemented on Playwright (already installed) instead of
Selenium — so it adds NO new heavy dependency and NO top-level package that could
shadow the project's own `core`/`plugins` modules.

Authentication: LinkedIn people-search is login-walled, so this uses the user's
own `li_at` session cookie (read from env LINKEDIN_LI_AT, or passed in). We never
handle the user's password — the cookie is supplied by the user in their own .env.

Guarantees: never raises. Returns [] on missing cookie, missing Playwright, a
login wall, a CAPTCHA/challenge, or stale DOM — so the CRM stays reliable.

    scraper = LinkedInVendorScraper(headless=True)
    profiles = await scraper.search_people("dental clinic owner Dubai", limit=10)
    # -> [{name, headline, profile_url, location, company}, ...]
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright  # type: ignore
    _PLAYWRIGHT = True
except Exception:
    async_playwright = None  # type: ignore
    _PLAYWRIGHT = False

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

_CHALLENGE_MARKERS = ("checkpoint/challenge", "authwall", "uas/login",
                      "please verify", "security verification", "unusual activity")


def _cookie() -> str:
    return (os.getenv("LINKEDIN_LI_AT") or "").strip().strip('"')


def vendor_available() -> bool:
    """True only when Playwright is present AND a li_at cookie is configured."""
    return _PLAYWRIGHT and bool(_cookie())


def _delay(a: float = 1.5, b: float = 4.0) -> float:
    return random.uniform(a, b)


class LinkedInVendorScraper:
    def __init__(self, li_at: Optional[str] = None, headless: bool = True,
                 proxy: Optional[str] = None):
        self.li_at = (li_at or _cookie())
        self.headless = headless
        self.proxy = proxy

    async def search_people(self, keyword: str, limit: int = 10,
                            location: Optional[str] = None) -> List[Dict[str, Any]]:
        if not _PLAYWRIGHT:
            logger.info("linkedin_vendor: Playwright not installed -> []")
            return []
        if not self.li_at:
            logger.info("linkedin_vendor: no LINKEDIN_LI_AT cookie configured -> []")
            return []

        p = browser = None
        try:
            p = await async_playwright().start()
            launch_kw: Dict[str, Any] = {
                "headless": self.headless,
                "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            }
            if self.proxy:
                launch_kw["proxy"] = {"server": self.proxy}
            browser = await p.chromium.launch(**launch_kw)
            context = await browser.new_context(
                user_agent=_UA,
                viewport={"width": random.choice([1280, 1366, 1440]), "height": 900},
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            # authenticate via li_at cookie (both apex + www)
            await context.add_cookies([
                {"name": "li_at", "value": self.li_at, "domain": ".linkedin.com",
                 "path": "/", "httpOnly": True, "secure": True},
            ])
            page = await context.new_page()

            kw = keyword.strip()
            q = kw.replace(" ", "%20")
            url = f"https://www.linkedin.com/search/results/people/?keywords={q}&origin=SWITCH_SEARCH_VERTICAL"
            await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            await asyncio.sleep(_delay(3, 5))

            cur = (page.url or "").lower()
            if any(m in cur for m in _CHALLENGE_MARKERS):
                logger.warning("linkedin_vendor: hit auth/challenge wall (cookie expired?) -> []")
                return []

            # human-like scroll to load lazy results
            for _ in range(random.randint(2, 4)):
                await page.mouse.wheel(0, random.randint(500, 900))
                await asyncio.sleep(_delay(1, 2))

            profiles = await self._extract(page, limit)
            logger.info("linkedin_vendor: extracted %d profiles for %r", len(profiles), kw)
            return profiles[:limit]
        except Exception as exc:
            logger.warning("linkedin_vendor: failed (%s) -> []", exc)
            return []
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if p:
                try:
                    await p.stop()
                except Exception:
                    pass

    async def _extract(self, page, limit: int) -> List[Dict[str, Any]]:
        """Extract people cards. LinkedIn DOM churns, so we use resilient anchor-
        based extraction (every profile card carries an /in/ link) plus text lines."""
        try:
            raw = await page.evaluate(
                """() => {
                    const out = [];
                    const seen = new Set();
                    document.querySelectorAll('a[href*="/in/"]').forEach(a => {
                        const href = (a.href || '').split('?')[0];
                        if (!href.includes('/in/') || seen.has(href)) return;
                        // climb to the result card
                        let card = a;
                        for (let i = 0; i < 6 && card && card.parentElement; i++) {
                            card = card.parentElement;
                            if (card.querySelector && card.querySelectorAll('span').length > 2) break;
                        }
                        const txt = card ? card.innerText : (a.innerText || '');
                        const lines = txt.split('\\n').map(s => s.trim()).filter(Boolean);
                        seen.add(href);
                        out.push({ href, lines });
                    });
                    return out.slice(0, 40);
                }"""
            )
        except Exception:
            raw = []

        results: List[Dict[str, Any]] = []
        for item in raw or []:
            href = item.get("href", "")
            lines = [ln for ln in (item.get("lines") or [])
                     if ln.lower() not in ("status is online", "status is offline")
                     and not ln.lower().startswith("view ")
                     and "connection" not in ln.lower()
                     and "• " != ln]
            if not href or not lines:
                continue
            name = lines[0][:120]
            # skip obvious non-name noise
            if name.lower() in ("linkedin member",) or len(name) < 2:
                continue
            headline = lines[1][:200] if len(lines) > 1 else ""
            location = lines[2][:120] if len(lines) > 2 else ""
            company = ""
            m = re.search(r"\bat\s+(.+)$", headline)
            if m:
                company = m.group(1).strip()[:120]
            results.append({
                "name": name, "headline": headline, "profile_url": href,
                "location": location, "company": company,
            })
            if len(results) >= limit:
                break
        return results

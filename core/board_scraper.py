"""
Board Scraper — universal job-board reader (no per-site parsers, no 404 rot).

Two problems, two real routes:

1. HTML-only boards (NoDesk, JustRemote, DailyRemote, Remote.co, Remoters):
   no API/RSS exists. Instead of brittle CSS selectors, we pull every anchor
   from the page and let heuristics + an LLM decide which are job postings.
   The site can redesign completely — as long as jobs are links, this works.

2. Datacenter-blocked boards (Bayt, NaukriGulf, Wellfound): they block Railway
   IPs. We route the fetch through Jina Reader (https://r.jina.ai/<url>) — a
   free, keyless service whose own infrastructure fetches and renders the page
   (including JS), so the block never sees our IP.

Every board is config, not code:  add a dict entry → new source. Results are
cached per (board, query) for 2 h so repeated searches cost nothing.

    records = await fetch_all("project manager")   # normalized job records
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
       "Accept": "text/html,application/xhtml+xml"}

# board registry — url may contain {q} (url-encoded query slot)
BOARDS: List[Dict[str, Any]] = [
    # Remote.co renders server-side — direct works, jobs live at /job-details/
    {"name": "Remote.co",    "url": "https://remote.co/remote-jobs/",              "via": "direct",
     "link_pat": r"remote\.co/job-details/[a-z0-9-]+"},
    # these render listings with JS → Jina Reader renders the page for us
    {"name": "NoDesk",       "url": "https://nodesk.co/remote-jobs/",              "via": "jina",
     "link_pat": r"nodesk\.co/remote-jobs/[a-z0-9-]+/[a-z0-9-]+"},
    {"name": "JustRemote",   "url": "https://justremote.co/remote-{q}-jobs",       "via": "jina",
     "link_pat": r"justremote\.co/remote-jobs/[a-z0-9-]+"},
    {"name": "DailyRemote",  "url": "https://dailyremote.com/remote-jobs/search?searchTerm={q}", "via": "jina",
     "link_pat": r"dailyremote\.com/remote-job/[a-z0-9-]+"},
    {"name": "Remoters",     "url": "https://remoters.net/jobs/",                  "via": "jina",
     "link_pat": r"remoters\.net/(?:job|jobs)/[a-z0-9-]+"},
    # blocked on datacenter IPs → routed through Jina Reader
    {"name": "Bayt",         "url": "https://www.bayt.com/en/international/jobs/{q}-jobs/", "via": "jina",
     "link_pat": r"/en/[a-z-]+/jobs/[a-z0-9-]+"},
    {"name": "NaukriGulf",   "url": "https://www.naukrigulf.com/{q}-jobs",         "via": "jina",
     "link_pat": r"/[a-z0-9-]+-jobs?-"},
    {"name": "Wellfound",    "url": "https://wellfound.com/role/r/{q}",            "via": "jina",
     "link_pat": r"/jobs/\d+"},
]

_CACHE: Dict[Tuple[str, str], Tuple[float, List[Dict[str, Any]]]] = {}
_TTL = 7200   # 2 h


def _rec(title, company, location, url, source):
    return {"title": (title or "").strip()[:160], "source_url": url or "",
            "location": (location or "Remote").strip()[:100],
            "description": "", "price": "",
            "metadata": {"type": "job", "company": (company or "").strip()[:100],
                         "source": source, "remote": True}}


async def _get(client: httpx.AsyncClient, url: str, via: str) -> str:
    """Fetch a page directly, or through Jina Reader for blocked sites.
    Direct fetches that come back blocked (403/429/503) retry via Jina."""
    try:
        if via == "direct":
            r = await client.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 500:
                # decode as UTF-8 ourselves — httpx guessing wrong charsets is
                # what produced 'â€"' mojibake in titles/companies
                return r.content.decode("utf-8", errors="ignore")
            if r.status_code not in (403, 429, 503):
                return ""
        # jina route (also the fallback when direct is blocked)
        r = await client.get(f"https://r.jina.ai/{url}",
                             headers={"X-Return-Format": "html"}, timeout=25)
        return r.content.decode("utf-8", errors="ignore") if r.status_code == 200 else ""
    except Exception:
        return ""


def _anchors(html: str, base: str) -> List[Tuple[str, str]]:
    """(text, absolute-href) for every meaningful anchor on the page."""
    out = []
    import html as _html
    for m in re.finditer(r'(?is)<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', html):
        href, inner = m.group(1), re.sub(r"(?s)<[^>]+>", " ", m.group(2))
        text = _html.unescape(re.sub(r"\s+", " ", inner)).strip()
        # strip decorative separators/mojibake remnants at the edges
        text = text.strip("—–|·•-· ").strip()
        if not (8 <= len(text) <= 120):
            continue
        if href.startswith("/"):
            root = re.match(r"https?://[^/]+", base)
            href = (root.group(0) if root else "") + href
        if href.startswith("http"):
            out.append((text, href))
    return out


_NOISE = re.compile(
    r"^(remote [a-z &]+ jobs?|browse|view all|see all|list your|post a job|sign|"
    r"log ?in|register|about|contact|blog|faq|pricing|companies|categories)\b", re.I)


def _heuristic_pick(anchors: List[Tuple[str, str]], pat: str) -> List[Tuple[str, str]]:
    rx = re.compile(pat, re.I)
    picked = [(t, h) for t, h in anchors if rx.search(h) and not _NOISE.match(t)]
    # dedup by href
    seen, out = set(), []
    for t, h in picked:
        if h not in seen:
            seen.add(h)
            out.append((t, h))
    return out[:40]


async def _llm_extract(board: str, picked: List[Tuple[str, str]],
                       query: str) -> List[Dict[str, Any]]:
    """LLM turns raw anchor texts into clean {title, company, location} — and
    drops navigation noise. Falls back to raw anchors if no model."""
    if not picked:
        return []
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if llm:
            lines = "\n".join(f"[{i}] {t}" for i, (t, _) in enumerate(picked[:35]))
            out = await llm.complete(
                f"These are link texts scraped from the job board '{board}'. Some are "
                f"job postings, some are navigation/noise. For each REAL job posting "
                f"relevant to '{query or 'any role'}', extract title, company (if "
                "present in the text, else \"\"), location (if present, else \"\"). "
                "Return ONLY a JSON array "
                "[{\"i\":<index>,\"title\":\"..\",\"company\":\"..\",\"location\":\"..\"}]. "
                f"Links:\n{lines}",
                system="You output only a JSON array.", max_tokens=800)
            m = re.search(r"\[.*\]", out, re.S)
            if m:
                rows = []
                for s in json.loads(m.group(0)):
                    i = int(s.get("i", -1))
                    if 0 <= i < len(picked) and s.get("title"):
                        rows.append(_rec(s["title"], s.get("company") or f"via {board}",
                                         s.get("location"), picked[i][1], board))
                return rows
    except Exception as exc:
        logger.info("board_scraper llm extract (%s) skipped: %s", board, exc)
    # fallback: anchor text as title (still real links, just less clean)
    return [_rec(t, f"via {board}", "", h, board) for t, h in picked[:20]]


async def _one_board(client, board: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    key = (board["name"], query.lower())
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    q_slug = re.sub(r"\s+", "-", (query or "remote").strip().lower())
    url = board["url"].replace("{q}", q_slug)
    html = await _get(client, url, board["via"])
    if not html:
        _CACHE[key] = (time.time(), [])
        return []
    picked = _heuristic_pick(_anchors(html, url), board["link_pat"])
    rows = await _llm_extract(board["name"], picked, query)
    _CACHE[key] = (time.time(), rows)
    logger.info("board_scraper: %s -> %d jobs (via %s)", board["name"], len(rows), board["via"])
    return rows


async def fetch_all(query: str = "", limit: int = 60) -> List[Dict[str, Any]]:
    """All boards in parallel; fail-soft; per-board cache. Never raises."""
    try:
        async with httpx.AsyncClient(headers=_UA, verify=False,
                                     follow_redirects=True) as client:
            lists = await asyncio.wait_for(
                asyncio.gather(*[_one_board(client, b, query) for b in BOARDS],
                               return_exceptions=True), timeout=45)
        out = []
        for lst in lists:
            if isinstance(lst, list):
                out += lst
        return out[:limit]
    except Exception as exc:
        logger.info("board_scraper fetch_all failed: %s", exc)
        return []

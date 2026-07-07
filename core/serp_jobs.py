"""
SERP Jobs Hunter — searches the web LIKE A HUMAN and reads what it finds.

Flow (mirrors a person googling "software engineer jobs dubai"):
  1. Query DuckDuckGo-HTML + Bing (both serve plain HTML to datacenter IPs —
     no CAPTCHA wall like google.com).
  2. From the results, keep links that LOOK like job pages (/jobs/, /careers/,
     greenhouse.io, lever.co, workable, "apply", ...) on ANY website — this is
     how pages like lazyapply.com/jobs/... get discovered without a per-site
     scraper.
  3. Open the top pages (direct fetch → Jina Reader fallback for JS/blocked
     sites) and extract the actual job: title, company, location, description.
  4. LLM cleans/filters to REAL postings relevant to the query; heuristic
     fallback keeps it working with no key.

Every step is fail-soft and cached (2 h per query).

    records = await fetch("software engineer", "dubai", "")   # normalized jobs
"""

from __future__ import annotations

import asyncio
import html as _htmlmod
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, unquote, urlparse

import httpx

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
       "Accept": "text/html,application/xhtml+xml"}

_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_TTL = 7200          # 2 h per query
_MAX_PAGES = 8       # job pages opened ("clicked") per search
_PAGE_CHARS = 3500   # how much of each page the extractor reads

# a link is job-like if URL or anchor text matches
_JOBLIKE_URL = re.compile(
    r"/jobs?[/-]|/careers?\b|/vacanc|/positions?\b|/openings?\b|/opportunit|"
    r"greenhouse\.io|lever\.co|workable|ashbyhq|smartrecruiters|recruitee|"
    r"jobvite|icims|bamboohr|teamtailor|personio", re.I)
_JOBLIKE_TEXT = re.compile(r"\b(job|vacanc|hiring|career|apply|position)\b", re.I)
# never follow these — search engines, socials, our own covered aggregators
_SKIP_DOMAINS = re.compile(
    r"(google\.|bing\.com|duckduckgo\.com|youtube\.|facebook\.|instagram\.|"
    r"twitter\.com|x\.com|reddit\.com|wikipedia\.org|linkedin\.com|"
    r"indeed\.com|glassdoor\.)", re.I)


def _rec(title, company, location, url, desc="", posted="") -> Dict[str, Any]:
    from core import freshness
    piso = freshness.parse(posted)
    return {"title": (title or "").strip()[:160], "source_url": url or "",
            "location": (location or "").strip()[:100] or "See posting",
            "description": (desc or "").strip()[:600], "price": "",
            "metadata": {"type": "job", "company": (company or "").strip()[:100],
                         "source": "Web Hunter", "remote": None,
                         "date_posted": piso, "posted_ago": freshness.ago(piso)}}


# ── step 1+2: search engines -> candidate job links ──────────────────────────

async def _ddg(client: httpx.AsyncClient, q: str) -> List[Tuple[str, str]]:
    """DuckDuckGo HTML endpoint — (title, url) results."""
    try:
        r = await client.post("https://html.duckduckgo.com/html/",
                              data={"q": q}, timeout=15)
        if r.status_code != 200:
            return []
        out = []
        for m in re.finditer(
                r'(?is)<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                r.text):
            href = m.group(1)
            # ddg wraps targets: //duckduckgo.com/l/?uddg=<encoded>&...
            um = re.search(r"[?&]uddg=([^&]+)", href)
            if um:
                href = unquote(um.group(1))
            title = _htmlmod.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
            title = re.sub(r"\s+", " ", title).strip()
            if href.startswith("http") and title:
                out.append((title, href))
        return out
    except Exception as exc:
        logger.info("serp_jobs ddg failed: %s", exc)
        return []


async def _bing(client: httpx.AsyncClient, q: str) -> List[Tuple[str, str]]:
    try:
        r = await client.get(f"https://www.bing.com/search?q={quote_plus(q)}&count=20",
                             timeout=15)
        if r.status_code != 200:
            return []
        out = []
        for m in re.finditer(
                r'(?is)<h2><a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a></h2>', r.text):
            title = _htmlmod.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
            title = re.sub(r"\s+", " ", title).strip()
            if title:
                out.append((title, m.group(1)))
        return out
    except Exception as exc:
        logger.info("serp_jobs bing failed: %s", exc)
        return []


def _job_links(results: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Keep result links that look like job pages; dedup by URL and domain."""
    seen_urls, seen_domains, out = set(), {}, []
    for title, url in results:
        if _SKIP_DOMAINS.search(url) or url.lower().endswith((".pdf", ".doc", ".docx")):
            continue
        if not (_JOBLIKE_URL.search(url) or _JOBLIKE_TEXT.search(title)):
            continue
        if url in seen_urls:
            continue
        dom = urlparse(url).netloc.lower()
        if seen_domains.get(dom, 0) >= 3:   # max 3 pages per site — spread wide
            continue
        seen_urls.add(url)
        seen_domains[dom] = seen_domains.get(dom, 0) + 1
        out.append((title, url))
    return out


# ── step 3: open the page and read it ────────────────────────────────────────

async def _page_text(client: httpx.AsyncClient, url: str) -> str:
    """Fetch a job page as readable text: direct HTML first, Jina Reader for
    JS-rendered/blocked pages (same trick board_scraper uses)."""
    import os as _o
    try:
        r = await client.get(url, timeout=12)
        if r.status_code == 200 and len(r.content) > 800:
            html = r.content.decode("utf-8", errors="ignore")
            body = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html)
            text = _htmlmod.unescape(re.sub(r"<[^>]+>", " ", body))
            return re.sub(r"\s+", " ", text).strip()
    except Exception:
        pass
    try:
        jheads = {}
        if _o.getenv("JINA_API_KEY"):
            jheads["Authorization"] = f"Bearer {_o.getenv('JINA_API_KEY')}"
        r = await client.get(f"https://r.jina.ai/{url}", headers=jheads, timeout=20)
        if r.status_code == 200:
            return re.sub(r"\s+", " ",
                          r.content.decode("utf-8", errors="ignore")).strip()
    except Exception:
        pass
    return ""


# ── step 4: turn pages into structured jobs ──────────────────────────────────

async def _extract(query: str,
                   pages: List[Tuple[str, str, str]]) -> List[Dict[str, Any]]:
    """pages = [(serp_title, url, page_text)] -> normalized job records.
    LLM path filters noise + pulls company/location/posted; heuristic fallback
    keeps SERP title + domain so results still flow with no key."""
    if not pages:
        return []
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if llm:
            blocks = "\n\n".join(
                f"[{i}] URL: {u}\nTITLE: {t}\nPAGE: {txt[:_PAGE_CHARS]}"
                for i, (t, u, txt) in enumerate(pages))
            out = await llm.complete(
                f"You are reading web pages a job seeker found searching "
                f"'{query} jobs'. For each page that is a REAL job posting (or a "
                f"listing page containing one clear primary job) relevant to "
                f"'{query}', extract: title, company, location, salary (\"\" if "
                f"absent), posted (date/relative like '2 days ago', \"\" if absent), "
                f"summary (<=40 words). Skip pages that are pure link lists, ads or "
                f"unrelated. Return ONLY a JSON array "
                "[{\"i\":<index>,\"title\":\"..\",\"company\":\"..\","
                "\"location\":\"..\",\"salary\":\"..\",\"posted\":\"..\","
                "\"summary\":\"..\"}].\n\n" + blocks,
                system="You output only a JSON array.", max_tokens=1200)
            m = re.search(r"\[.*\]", out, re.S)
            if m:
                rows = []
                for s in json.loads(m.group(0)):
                    i = int(s.get("i", -1))
                    if 0 <= i < len(pages) and s.get("title"):
                        r_ = _rec(s["title"], s.get("company"),
                                  s.get("location"), pages[i][1],
                                  s.get("summary"), s.get("posted"))
                        if s.get("salary"):
                            r_["price"] = str(s["salary"])[:60]
                            r_["metadata"]["salary"] = r_["price"]
                        rows.append(r_)
                return rows
    except Exception as exc:
        logger.info("serp_jobs llm extract skipped: %s", exc)
    # heuristic fallback: SERP title is usually "<role> - <company> - <site>"
    rows = []
    for t, u, txt in pages:
        dom = urlparse(u).netloc.replace("www.", "")
        rows.append(_rec(t, f"via {dom}", "", u, txt[:300]))
    return rows


# ── public entry ─────────────────────────────────────────────────────────────

async def fetch(query: str, location: str = "", job_type: str = "",
                limit: int = 20) -> List[Dict[str, Any]]:
    """Web-wide human-style job hunt. Never raises; [] on any failure."""
    q = " ".join(x for x in (query.strip(), (job_type or "").strip(), "jobs",
                             (location or "").strip()) if x)
    key = q.lower()
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1][:limit]
    try:
        async with httpx.AsyncClient(headers=_UA, verify=False,
                                     follow_redirects=True) as client:
            serps = await asyncio.gather(_ddg(client, q), _bing(client, q))
            links = _job_links([r for lst in serps for r in lst])[:_MAX_PAGES]
            texts = await asyncio.gather(
                *[_page_text(client, u) for _, u in links])
            pages = [(t, u, txt) for (t, u), txt in zip(links, texts) if txt]
            rows = await _extract(query, pages)
        _CACHE[key] = (time.time(), rows)
        logger.info("serp_jobs: '%s' -> %d serp results, %d job pages, %d jobs",
                    q, sum(len(l) for l in serps), len(pages), len(rows))
        return rows[:limit]
    except Exception as exc:
        logger.info("serp_jobs fetch failed: %s", exc)
        return []


async def fetch_serp_jobs(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Registry entry point (crawl_mode='serp_jobs')."""
    p = portal_config.get("serp_params") or {}
    return await fetch(p.get("query", "software engineer"),
                       p.get("location", ""), p.get("job_type", ""),
                       int(p.get("limit", 15)))

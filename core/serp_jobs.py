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
_TTL_HIT = 7200      # 2 h per query with results
_TTL_MISS = 600      # empty results retry after 10 min (transient blocks)
_MAX_PAGES = 25      # job pages opened ("clicked") per search
_PAGE_CHARS = 5000   # how much of each page the extractor reads

# a link is job-like if URL or anchor text matches
_JOBLIKE_URL = re.compile(
    r"/jobs?[/-]|/careers?\b|/vacanc|/positions?\b|/openings?\b|/opportunit|"
    r"greenhouse\.io|lever\.co|workable|ashbyhq|smartrecruiters|recruitee|"
    r"jobvite|icims|bamboohr|teamtailor|personio", re.I)
_JOBLIKE_TEXT = re.compile(r"\b(job|vacanc|hiring|career|apply|position)\b", re.I)
# never follow these — search engines, socials, our own covered aggregators
# NOTE: individual indeed/linkedin job pages are allowed (filtered below by URL shape)
_SKIP_DOMAINS = re.compile(
    r"(google\.|bing\.com|duckduckgo\.com|youtube\.|facebook\.|instagram\.|"
    r"twitter\.com|x\.com|reddit\.com|wikipedia\.org|glassdoor\.)", re.I)


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

def _parse_ddg(html: str) -> List[Tuple[str, str, str]]:
    """Returns list of (title, url, snippet) from DDG HTML."""
    out = []
    # Try structured result blocks: each result has .result__a + .result__snippet
    blocks = re.findall(
        r'(?is)<div[^>]+class="[^"]*result[^"]*"[^>]*>(.*?)</div>\s*</div>',
        html)
    for block in blocks:
        am = re.search(
            r'(?is)<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block)
        if not am:
            continue
        href = am.group(1)
        um = re.search(r"[?&]uddg=([^&]+)", href)
        if um:
            href = unquote(um.group(1))
        title = _htmlmod.unescape(re.sub(r"<[^>]+>", " ", am.group(2)))
        title = re.sub(r"\s+", " ", title).strip()
        snip_m = re.search(r'(?is)class="result__snippet"[^>]*>(.*?)</a>', block)
        snippet = ""
        if snip_m:
            snippet = _htmlmod.unescape(re.sub(r"<[^>]+>", " ", snip_m.group(1)))
            snippet = re.sub(r"\s+", " ", snippet).strip()
        if href.startswith("http") and title:
            out.append((title, href, snippet))
    if out:
        return out
    # fallback: plain link extraction (lite endpoint style)
    pats = (r'(?is)<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            r'(?is)<a[^>]+rel="nofollow"[^>]+href="([^"]+)"[^>]*>(.*?)</a>')
    for pat in pats:
        for m in re.finditer(pat, html):
            href = m.group(1)
            um = re.search(r"[?&]uddg=([^&]+)", href)
            if um:
                href = unquote(um.group(1))
            title = _htmlmod.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
            title = re.sub(r"\s+", " ", title).strip()
            if href.startswith("http") and title:
                out.append((title, href, ""))
        if out:
            break
    return out


async def _brave_search(client: httpx.AsyncClient, q: str) -> List[Tuple[str, str, str]]:
    """Brave Search API — works on Railway/datacenter, free tier 1k/month.
    Set BRAVE_SEARCH_API_KEY env var to enable."""
    import os as _o
    key = _o.getenv("BRAVE_SEARCH_API_KEY") or _o.getenv("BRAVE_API_KEY")
    if not key:
        return []
    try:
        r = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": q, "count": 20, "search_lang": "en"},
            headers={"Accept": "application/json", "X-Subscription-Token": key},
            timeout=15)
        if r.status_code == 200:
            results = r.json().get("web", {}).get("results") or []
            out = []
            for item in results:
                title = (item.get("title") or "").strip()
                url = (item.get("url") or "").strip()
                snippet = (item.get("description") or "").strip()
                if title and url and url.startswith("http"):
                    out.append((title, url, snippet))
            if out:
                logger.info("serp_jobs brave: %d results for '%s'", len(out), q[:40])
            return out
    except Exception as exc:
        logger.info("serp_jobs brave_search failed: %s", exc)
    return []


async def _jina_search(client: httpx.AsyncClient, q: str) -> List[Tuple[str, str, str]]:
    """Jina AI Search (s.jina.ai) — works from Railway/datacenter IPs because
    Jina fetches from their own infrastructure. Primary search source."""
    import os as _o
    try:
        heads = {"Accept": "application/json"}
        jina_key = _o.getenv("JINA_API_KEY")
        if jina_key:
            heads["Authorization"] = f"Bearer {jina_key}"
        r = await client.get(
            f"https://s.jina.ai/{quote_plus(q)}",
            headers=heads, timeout=20)
        if r.status_code == 200:
            # JSON response: {"data": [{"title":..,"url":..,"content":..},...]}
            try:
                data = r.json()
                items = data.get("data") or data.get("results") or []
                if items:
                    out = []
                    for item in items:
                        title = (item.get("title") or "").strip()
                        url = (item.get("url") or "").strip()
                        snippet = (item.get("content") or item.get("description") or "").strip()[:400]
                        if title and url and url.startswith("http"):
                            out.append((title, url, snippet))
                    if out:
                        logger.info("serp_jobs jina_search: %d results for '%s'", len(out), q[:40])
                        return out
            except Exception:
                pass
            # Fallback: parse markdown text response
            text = r.content.decode("utf-8", errors="ignore")
            out = []
            blocks = re.split(r'\n(?=\[\d+\]|\*\*\[)', text)
            for block in blocks:
                tm = re.search(r'\*?\*?\[?([^\]\n]+)\]?\*?\*?\s*\n.*?(?:URL|Source).*?:\s*(https?://[^\s\n]+)', block, re.I)
                if not tm:
                    tm = re.search(r'(?:Title|##)[:\s]+([^\n]+)\n.*?(https?://[^\s\n]+)', block, re.I)
                if tm:
                    title = tm.group(1).strip().strip('*[]')
                    url = tm.group(2).strip()
                    # extract snippet: text between URL and next block
                    snip_m = re.search(r'(?:Description|Content|Snippet)[:\s]+([^\n]+(?:\n[^\n#]+)*)', block, re.I)
                    snippet = snip_m.group(1).strip()[:300] if snip_m else ""
                    if title and url:
                        out.append((title, url, snippet))
            if out:
                logger.info("serp_jobs jina_search markdown: %d results for '%s'", len(out), q[:40])
                return out
    except Exception as exc:
        logger.info("serp_jobs jina_search failed: %s", exc)
    return []


async def _ddg(client: httpx.AsyncClient, q: str) -> List[Tuple[str, str, str]]:
    """DuckDuckGo — works on local/home IPs. Blocked on datacenter/Railway IPs.
    Use _jina_search as primary on Railway."""
    import os as _o
    try:
        r = await client.post("https://html.duckduckgo.com/html/",
                              data={"q": q}, timeout=12)
        if r.status_code == 200:
            hits = _parse_ddg(r.text)
            if hits:
                return hits
    except Exception as exc:
        logger.info("serp_jobs ddg direct failed: %s", exc)
    try:
        r = await client.get(
            f"https://lite.duckduckgo.com/lite/?q={quote_plus(q)}", timeout=12)
        if r.status_code == 200:
            hits = _parse_ddg(r.text)
            if hits:
                return hits
    except Exception as exc:
        logger.info("serp_jobs ddg lite failed: %s", exc)
    return []


async def _bing(client: httpx.AsyncClient, q: str) -> List[Tuple[str, str, str]]:
    """Bing — extracts title, URL, and snippet from result blocks."""
    try:
        r = await client.get(f"https://www.bing.com/search?q={quote_plus(q)}&count=30",
                             timeout=15)
        if r.status_code != 200:
            return []
        out = []
        # Bing result block: <li class="b_algo">...<h2><a>title</a></h2>...<p>snippet</p>...
        blocks = re.findall(r'(?is)<li[^>]+class="b_algo"[^>]*>(.*?)</li>', r.text)
        for block in blocks:
            hm = re.search(r'(?is)<h2><a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a></h2>', block)
            if not hm:
                continue
            title = _htmlmod.unescape(re.sub(r"<[^>]+>", " ", hm.group(2)))
            title = re.sub(r"\s+", " ", title).strip()
            snippet = ""
            pm = re.search(r'(?is)<p[^>]*>(.*?)</p>', block)
            if pm:
                snippet = _htmlmod.unescape(re.sub(r"<[^>]+>", " ", pm.group(1)))
                snippet = re.sub(r"\s+", " ", snippet).strip()
            if title:
                out.append((title, hm.group(1), snippet))
        if not out:
            # fallback: just h2 links
            for m in re.finditer(
                    r'(?is)<h2><a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a></h2>', r.text):
                title = _htmlmod.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
                title = re.sub(r"\s+", " ", title).strip()
                if title:
                    out.append((title, m.group(1), ""))
        return out
    except Exception as exc:
        logger.info("serp_jobs bing failed: %s", exc)
        return []


def _jobs_from_serp(results: List[Tuple[str, str, str]], query: str) -> List[Dict[str, Any]]:
    """Create job records directly from SERP title+URL+snippet without page visits.
    SERP titles are often '<Job Title> - <Company> - <Location> | <Site>' which is
    enough to populate a useful record even with no LLM."""
    out = []
    for title, url, snippet in results:
        if _SKIP_DOMAINS.search(url):
            continue
        if not (_JOBLIKE_URL.search(url) or _JOBLIKE_TEXT.search(title)
                or _JOBLIKE_TEXT.search(snippet)):
            continue
        dom = urlparse(url).netloc.replace("www.", "")
        # parse "Job Title - Company - Location | Site" pattern
        clean = re.sub(r"\s*[|—]\s*.*$", "", title).strip()  # strip "| site" suffix
        parts = re.split(r"\s*[-–]\s*", clean, maxsplit=2)
        job_title = parts[0].strip() if parts else title
        company = parts[1].strip() if len(parts) > 1 else f"via {dom}"
        location = parts[2].strip() if len(parts) > 2 else ""
        # skip if job_title looks generic (just the site name or "jobs")
        if not job_title or len(job_title) < 4:
            continue
        # extract salary from snippet if present
        salary = ""
        sm = re.search(r'(?:£|€|\$|USD|GBP|EUR|AED|PKR)\s*[\d,]+(?:\s*[-–]\s*[\d,k]+)?'
                       r'(?:\s*(?:per|/)\s*(?:year|month|hr|hour|annum|yr))?',
                       snippet, re.I)
        if sm:
            salary = sm.group(0).strip()
        # extract location from snippet if not in title
        if not location:
            lm = re.search(r'\b(?:Remote|Dubai|London|UAE|UK|USA|Pakistan|Germany|'
                           r'Canada|Australia|New York|San Francisco|Singapore)\b',
                           snippet + " " + title, re.I)
            if lm:
                location = lm.group(0)
        desc = snippet[:300] if snippet else ""
        out.append(_rec(job_title, company, location or "See posting", url, desc))
        if salary:
            out[-1]["price"] = salary
            out[-1]["metadata"]["salary"] = salary
    return out


# listing/category pages, NOT individual postings: search/sort/pagination
# params or bare /jobs index paths — linking these as "a job" misleads users
# (e.g. remoterocketship.com/jobs/...?page=1&sort=DateAdded)
_LISTING_URL = re.compile(
    r"[?&](?:page|sort|search|filter|seniority|jobTitle|q)=|"
    r"/(?:jobs?|careers?|vacancies|remote-jobs?)/?$", re.I)


def _job_links(results: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    """Keep result links that look like INDIVIDUAL job pages; dedup by URL
    and domain; drop listing/category pages."""
    seen_urls, seen_domains, out = set(), {}, []
    for item in results:
        title, url = item[0], item[1]
        snippet = item[2] if len(item) > 2 else ""
        if _SKIP_DOMAINS.search(url) or url.lower().endswith((".pdf", ".doc", ".docx")):
            continue
        # allow indeed/linkedin individual job pages (viewjob, jobs/view)
        is_individual = bool(re.search(
            r"indeed\.com/viewjob|indeed\.com/rc/clk|linkedin\.com/jobs/view/|"
            r"linkedin\.com/jobs/collections/", url, re.I))
        if not is_individual and _LISTING_URL.search(url):
            continue
        if not (_JOBLIKE_URL.search(url) or _JOBLIKE_TEXT.search(title)
                or _JOBLIKE_TEXT.search(snippet)):
            continue
        if url in seen_urls:
            continue
        dom = urlparse(url).netloc.lower()
        if seen_domains.get(dom, 0) >= 5:   # max 5 pages per site — spread wide
            continue
        seen_urls.add(url)
        seen_domains[dom] = seen_domains.get(dom, 0) + 1
        out.append((title, url, snippet))
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
    """Web-wide human-style job hunt. Never raises; [] on any failure.

    Three parallel paths:
    1. ATS-targeted search: site:greenhouse.io/lever.co/ashby/workable to get
       CAPTCHA-free individual job postings (best quality)
    2. General SERP page-visit: open top individual job pages found via DDG+Bing
    3. SERP-direct: extract from SERP snippets/titles without page visits (fast fallback)
    All results merged and deduped by URL.
    """
    q_base = query.strip()
    loc = (location or "").strip()
    jt = (job_type or "").strip()
    q = " ".join(x for x in (q_base, jt, "jobs", loc) if x)
    key = q.lower()
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < (_TTL_HIT if hit[1] else _TTL_MISS):
        return hit[1][:limit]
    try:
        async with httpx.AsyncClient(headers=_UA, verify=False,
                                     follow_redirects=True) as client:

            # --- Query variants ---
            q_general = " ".join(x for x in (q_base, "jobs", loc) if x)
            # ATS-targeted: greenhouse/lever/ashby pages — CAPTCHA-free individual job postings
            ats_sites = "site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashby.com OR site:apply.workable.com"
            q_ats = f'"{q_base}" {loc} {ats_sites}'.strip()
            q_ats2 = f'"{q_base}" {loc} (site:teamtailor.com OR site:recruitee.com OR site:jobs.eu.lever.co OR site:boards.eu.greenhouse.io)'.strip()
            q_careers = f'"{q_base}" "apply now" {loc} -site:linkedin.com -site:indeed.com -site:glassdoor.com'.strip()

            # TIER 1 (Railway-safe — use their own infra, not blocked):
            #   Jina Search (s.jina.ai, needs JINA_API_KEY)
            #   Brave Search (api.search.brave.com, needs BRAVE_SEARCH_API_KEY)
            # TIER 2 (local only — blocked on Railway datacenter IPs):
            #   DDG, Bing
            serps_all_raw = await asyncio.gather(
                _jina_search(client, q_ats),      # Jina: ATS individual job pages
                _jina_search(client, q_ats2),     # Jina: more ATS
                _jina_search(client, q_general),  # Jina: general
                _jina_search(client, q_careers),  # Jina: career pages
                _brave_search(client, q_ats),     # Brave: ATS job pages
                _brave_search(client, q_general), # Brave: general
                _ddg(client, q_general),           # DDG (local fallback)
                _bing(client, q_general),          # Bing (local fallback)
                _bing(client, q_ats),              # Bing ATS (local fallback)
            )
            all_results = [r for lst in serps_all_raw for r in lst]

            # PATH 1: SERP-direct extraction (fast, works from snippets)
            serp_direct = _jobs_from_serp(all_results, query)

            # PATH 2: Page-visit extraction (ATS pages first, then general)
            links = _job_links(all_results)[:_MAX_PAGES]
            texts = await asyncio.gather(
                *[_page_text(client, u) for _, u, _ in links])
            pages = [(t, u, txt) for (t, u, _), txt in zip(links, texts) if txt]
            page_jobs = await _extract(query, pages)

        # merge: page-visit results first (higher quality), then SERP-direct
        seen_urls: set = set()
        rows: List[Dict[str, Any]] = []
        for j in page_jobs + serp_direct:
            u = j.get("source_url", "")
            if u and u in seen_urls:
                continue
            if u:
                seen_urls.add(u)
            rows.append(j)

        _CACHE[key] = (time.time(), rows)
        logger.info(
            "serp_jobs: '%s' -> %d serp results, %d page jobs, %d serp-direct, %d total",
            q, len(all_results), len(page_jobs), len(serp_direct), len(rows))
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

"""
Remote Jobs — keyless aggregator APIs (no per-company slugs, no 404s).

Instead of guessing each company's ATS handle (which 404s), we query public
remote-job aggregators that already index thousands of companies worldwide.
All are keyless JSON APIs, global, and NOT blocked on datacenter IPs:

    Remotive · RemoteOK · Jobicy · Arbeitnow · WeWorkRemotely(RSS)

    await fetch("project manager", limit=80)  ->  [normalized job records]

Each source is independent + fail-soft, so one being down never breaks the rest.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)
_UA = {"User-Agent": "Mozilla/5.0 (compatible; WildAutomations/1.0)",
       "Accept": "application/json"}


def _rec(title, company, location, url, desc, salary="", src="Remote Aggregator"):
    loc = location or "Remote"
    return {"title": (title or "").strip(), "source_url": url or "",
            "location": loc, "description": re.sub(r"<[^>]+>", " ", desc or "")[:600],
            "price": salary or "",
            "metadata": {"type": "job", "company": company or "", "source": src,
                         "remote": True, "salary": salary or ""}}


async def _remotive(client, q) -> List[Dict[str, Any]]:
    try:
        u = "https://remotive.com/api/remote-jobs" + (f"?search={q}&limit=60" if q else "?limit=60")
        r = await client.get(u, timeout=15)
        return [_rec(j.get("title"), j.get("company_name"),
                     j.get("candidate_required_location", "Remote"), j.get("url"),
                     j.get("description"), j.get("salary", ""))
                for j in (r.json().get("jobs") or [])] if r.status_code == 200 else []
    except Exception:
        return []


async def _remoteok(client, q) -> List[Dict[str, Any]]:
    try:
        r = await client.get("https://remoteok.com/api", timeout=15)
        if r.status_code != 200:
            return []
        out = []
        for j in r.json():
            if not isinstance(j, dict) or not j.get("position"):
                continue
            out.append(_rec(j.get("position"), j.get("company"),
                            j.get("location") or "Remote", j.get("url") or j.get("apply_url"),
                            j.get("description"), (j.get("salary_min") and
                            f"{j.get('salary_min')}-{j.get('salary_max')} USD") or ""))
        return out
    except Exception:
        return []


async def _jobicy(client, q) -> List[Dict[str, Any]]:
    try:
        u = "https://jobicy.com/api/v2/remote-jobs?count=50" + (f"&tag={q}" if q else "")
        r = await client.get(u, timeout=15)
        return [_rec(j.get("jobTitle"), j.get("companyName"), j.get("jobGeo", "Remote"),
                     j.get("url"), j.get("jobExcerpt"), (j.get("annualSalaryMin") and
                     f"{j.get('annualSalaryMin')}-{j.get('annualSalaryMax')} {j.get('salaryCurrency','USD')}") or "")
                for j in (r.json().get("jobs") or [])] if r.status_code == 200 else []
    except Exception:
        return []


async def _themuse(client, q) -> List[Dict[str, Any]]:
    try:
        out = []
        for page in (0, 1):
            r = await client.get(
                f"https://www.themuse.com/api/public/jobs?page={page}", timeout=15)
            if r.status_code != 200:
                break
            for j in (r.json().get("results") or []):
                locs = ", ".join(l.get("name", "") for l in (j.get("locations") or [])) or "Flexible"
                out.append(_rec(j.get("name"), (j.get("company") or {}).get("name"),
                                locs, (j.get("refs") or {}).get("landing_page"), j.get("contents")))
        return out
    except Exception:
        return []


async def _adzuna(client, q) -> List[Dict[str, Any]]:
    import os as _os
    app_id, app_key = _os.getenv("ADZUNA_APP_ID"), _os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        return []
    out = []
    for cc in ("gb", "us"):
        try:
            r = await client.get(
                f"https://api.adzuna.com/v1/api/jobs/{cc}/search/1",
                params={"app_id": app_id, "app_key": app_key, "what": q or "remote",
                        "results_per_page": 40, "content-type": "application/json"}, timeout=15)
            if r.status_code != 200:
                continue
            for j in (r.json().get("results") or []):
                sal = (f"{int(j['salary_min'])}-{int(j.get('salary_max', j['salary_min']))}"
                       if j.get("salary_min") else "")
                out.append(_rec(j.get("title"), (j.get("company") or {}).get("display_name"),
                                (j.get("location") or {}).get("display_name"),
                                j.get("redirect_url"), j.get("description"), sal,
                                src="Adzuna"))
        except Exception:
            continue
    return out


async def _workingnomads(client, q) -> List[Dict[str, Any]]:
    """Working Nomads — public JSON API (keyless, worldwide remote)."""
    try:
        r = await client.get("https://www.workingnomads.com/api/exposed_jobs/", timeout=15)
        if r.status_code != 200:
            return []
        return [_rec(j.get("title"), j.get("company_name"),
                     j.get("location") or "Remote", j.get("url"),
                     j.get("description"))
                for j in (r.json() or [])[:60]]
    except Exception:
        return []


async def _jobspresso(client, q) -> List[Dict[str, Any]]:
    """Jobspresso — curated remote jobs via public RSS (keyless)."""
    try:
        r = await client.get("https://jobspresso.co/feed/?post_type=job_listing", timeout=15)
        if r.status_code != 200:
            return []
        out = []
        for item in re.findall(r"(?s)<item>(.*?)</item>", r.text)[:40]:
            def _tag(t):
                m = re.search(rf"(?s)<{t}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{t}>", item)
                return (m.group(1) if m else "").strip()
            out.append(_rec(_tag("title"), _tag("job_listing_company") or "via Jobspresso",
                            _tag("job_listing_location") or "Remote",
                            _tag("link"), _tag("description")))
        return out
    except Exception:
        return []


async def _himalayas(client, q) -> List[Dict[str, Any]]:
    """Himalayas — keyless remote-jobs API (100k+ listings, has location
    restrictions per job which feeds our honest-eligibility labels)."""
    try:
        r = await client.get("https://himalayas.app/jobs/api?limit=50", timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        out = []
        for j in (data.get("jobs") or data.get("data") or []):
            locs = j.get("locationRestrictions") or []
            loc = ", ".join(locs) if locs else "Remote (Worldwide)"
            sal = ""
            if j.get("minSalary"):
                sal = f"{j['minSalary']}-{j.get('maxSalary', j['minSalary'])} {j.get('currency','USD')}"
            out.append(_rec(j.get("title"), j.get("companyName"), loc,
                            j.get("applicationLink") or j.get("guid"),
                            j.get("description") or j.get("excerpt"), sal))
        return out
    except Exception:
        return []


async def _jooble(client, q) -> List[Dict[str, Any]]:
    """Jooble — free API key (jooble.org/api/about). Env: JOOBLE_API_KEY."""
    import os as _o
    key = _o.getenv("JOOBLE_API_KEY")
    if not key:
        return []
    try:
        r = await client.post(f"https://jooble.org/api/{key}",
                              json={"keywords": q or "remote", "page": 1}, timeout=15)
        if r.status_code != 200:
            return []
        return [_rec(j.get("title"), j.get("company"), j.get("location", ""),
                     j.get("link"), j.get("snippet"), j.get("salary", ""))
                for j in (r.json().get("jobs") or [])]
    except Exception:
        return []


async def _usajobs(client, q) -> List[Dict[str, Any]]:
    """USAJobs — free US-gov API. Env: USAJOBS_API_KEY + USAJOBS_EMAIL."""
    import os as _o
    key, email = _o.getenv("USAJOBS_API_KEY"), _o.getenv("USAJOBS_EMAIL")
    if not (key and email):
        return []
    try:
        r = await client.get(
            "https://data.usajobs.gov/api/search",
            params={"Keyword": q or "remote", "ResultsPerPage": 25},
            headers={"Authorization-Key": key, "User-Agent": email,
                     "Host": "data.usajobs.gov"}, timeout=15)
        if r.status_code != 200:
            return []
        items = ((r.json().get("SearchResult") or {}).get("SearchResultItems") or [])
        out = []
        for it in items:
            d = it.get("MatchedObjectDescriptor") or {}
            pay = (d.get("PositionRemuneration") or [{}])[0]
            sal = (f"{pay.get('MinimumRange','')}-{pay.get('MaximumRange','')} "
                   f"{pay.get('RateIntervalCode','')}").strip("- ")
            out.append(_rec(d.get("PositionTitle"), d.get("OrganizationName"),
                            d.get("PositionLocationDisplay", "USA"),
                            d.get("PositionURI"),
                            ((d.get("UserArea") or {}).get("Details") or {}).get("JobSummary", ""),
                            sal))
        return out
    except Exception:
        return []


async def _careerjet(client, q) -> List[Dict[str, Any]]:
    """Careerjet — free public API with affiliate id. Env: CAREERJET_AFFID."""
    import os as _o
    affid = _o.getenv("CAREERJET_AFFID")
    if not affid:
        return []
    try:
        r = await client.get(
            "http://public.api.careerjet.net/search",
            params={"keywords": q or "remote", "location": "remote", "affid": affid,
                    "user_ip": "1.1.1.1", "user_agent": "Mozilla/5.0",
                    "locale_code": "en_US", "pagesize": 30}, timeout=15)
        if r.status_code != 200:
            return []
        return [_rec(j.get("title"), j.get("company"), j.get("locations", ""),
                     j.get("url"), j.get("description"), j.get("salary", ""))
                for j in (r.json().get("jobs") or [])]
    except Exception:
        return []


async def _wwr(client, q) -> List[Dict[str, Any]]:
    """WeWorkRemotely — public RSS feed (keyless, global)."""
    try:
        r = await client.get("https://weworkremotely.com/remote-jobs.rss", timeout=15)
        if r.status_code != 200:
            return []
        out = []
        for item in re.findall(r"(?s)<item>(.*?)</item>", r.text)[:60]:
            def _tag(t):
                m = re.search(rf"(?s)<{t}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{t}>", item)
                return (m.group(1) if m else "").strip()
            title = _tag("title")            # "Company: Job Title"
            comp, _, role = title.partition(":")
            out.append(_rec(role.strip() or title, comp.strip(),
                            _tag("region") or "Remote", _tag("link"), _tag("description")))
        return out
    except Exception:
        return []


# ── Company ATS boards (user-curated list — probed ONCE, so no 404 spam) ─────
import json as _json
import os as _os

_LIST_PATH = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)),
                           "data", "remote_companies.txt")
_CACHE_PATH = _os.path.join(_os.path.dirname(_LIST_PATH), "company_boards_cache.json")
_BOARDS: Dict[str, str] = {}          # slug -> "greenhouse" | "lever"
_PROBED = False
_PROBING = False


def _company_names() -> List[str]:
    """All company names from remote_companies.txt + remote_companies.csv."""
    names: List[str] = []
    try:
        with open(_LIST_PATH, encoding="utf-8") as f:
            names += [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except Exception:
        pass
    try:
        import csv as _csv
        with open(_LIST_PATH.replace(".txt", ".csv"), encoding="utf-8") as f:
            names += [row.get("company_name", "").strip()
                      for row in _csv.DictReader(f)]
    except Exception:
        pass
    return sorted({n for n in names if n})


def _slugs() -> List[str]:
    return sorted({re.sub(r"[^a-z0-9]", "", n.lower())
                   for n in _company_names() if n})


async def _ai_guess_slugs(missed: List[str]) -> Dict[str, str]:
    """For companies whose name-slug 404'd, ask the LLM for their REAL public
    ATS board slug (e.g. 'Epic Games' -> greenhouse 'epicgames'). Returns
    {guessed_slug: company} to probe — guesses are still verified, never trusted."""
    if not missed:
        return {}
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return {}
        out = await llm.complete(
            "For each company, give its most likely PUBLIC Greenhouse or Lever job "
            "board slug (the id in boards-api.greenhouse.io/v1/boards/<slug>/jobs or "
            "api.lever.co/v0/postings/<slug>). Lowercase, no spaces. If unsure, guess "
            "the most common convention. Return ONLY a JSON object "
            "{\"company\":\"slug\"}. Companies: " + ", ".join(missed[:40]),
            system="You output only compact valid JSON.", max_tokens=600)
        import json as _j
        m = re.search(r"\{.*\}", out, re.S)
        if not m:
            return {}
        guesses = _j.loads(m.group(0))
        return {re.sub(r"[^a-z0-9-]", "", str(v).lower()): k
                for k, v in guesses.items() if v}
    except Exception as exc:
        logger.info("ai slug guessing skipped: %s", exc)
        return {}


async def _probe_boards() -> None:
    """One-time discovery of which companies expose a public Greenhouse/Lever
    board. Runs in the background on first fetch; cached to disk + memory."""
    global _PROBED, _PROBING
    if _PROBED or _PROBING:
        return
    _PROBING = True
    try:
        try:
            with open(_CACHE_PATH, encoding="utf-8") as f:
                _BOARDS.update(_json.load(f))
            _PROBED = True
            logger.info("company boards: %d loaded from cache", len(_BOARDS))
            return
        except Exception:
            pass
        sem = asyncio.Semaphore(12)
        async with httpx.AsyncClient(headers=_UA, verify=False,
                                     follow_redirects=True) as client:
            async def _one(slug):
                async with sem:
                    try:
                        r = await client.get(
                            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                            timeout=8)
                        if r.status_code == 200 and (r.json().get("jobs") is not None):
                            _BOARDS[slug] = "greenhouse"
                            return
                    except Exception:
                        pass
                    try:
                        r = await client.get(
                            f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=1",
                            timeout=8)
                        if r.status_code == 200 and isinstance(r.json(), list):
                            _BOARDS[slug] = "lever"
                            return
                    except Exception:
                        pass
                    try:
                        r = await client.get(
                            f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                            timeout=8)
                        if r.status_code == 200 and (r.json().get("jobs") is not None):
                            _BOARDS[slug] = "ashby"
                            return
                    except Exception:
                        pass
                    try:
                        r = await client.get(
                            f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=false",
                            timeout=8)
                        # require actual postings — widget may 200 on unknown accounts
                        if r.status_code == 200 and (r.json().get("jobs") or []):
                            _BOARDS[slug] = "workable"
                            return
                    except Exception:
                        pass
                    try:
                        r = await client.get(
                            f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1",
                            timeout=8)
                        # SR returns 200 + totalFound:0 for ANY slug — require real postings
                        if r.status_code == 200 and (r.json().get("totalFound") or 0) > 0:
                            _BOARDS[slug] = "smartrecruiters"
                            return
                    except Exception:
                        pass
                    try:
                        r = await client.get(
                            f"https://{slug}.recruitee.com/api/offers/", timeout=8)
                        if r.status_code == 200 and (r.json().get("offers") is not None):
                            _BOARDS[slug] = "recruitee"
                    except Exception:
                        pass
            slugs = _slugs()
            await asyncio.gather(*[_one(s) for s in slugs])
            # second pass: AI suggests the REAL slug for companies that 404'd
            # (e.g. 'epicgames' vs 'epic-games') — suggestions are re-verified
            missed = [s for s in slugs if s not in _BOARDS]
            for guess in (await _ai_guess_slugs(missed)):
                if guess and guess not in _BOARDS:
                    await _one(guess)
        _PROBED = True
        try:
            with open(_CACHE_PATH, "w", encoding="utf-8") as f:
                _json.dump(_BOARDS, f)
        except Exception:
            pass
        logger.info("company boards: probed — %d valid boards found", len(_BOARDS))
    finally:
        _PROBING = False


async def _company_boards(client, q) -> List[Dict[str, Any]]:
    """Live jobs from the user's companies with CONFIRMED ATS boards only.
    First-ever call kicks the probe off in the background (returns [] once);
    afterwards every search pulls real jobs from valid boards — zero 404s."""
    if not _PROBED:
        asyncio.ensure_future(_probe_boards())
        return []
    out: List[Dict[str, Any]] = []
    sem = asyncio.Semaphore(10)

    async def _gh(slug):
        async with sem:
            try:
                r = await client.get(
                    f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
                    timeout=10)
                for j in (r.json().get("jobs") or [])[:15]:
                    out.append(_rec(j.get("title"), slug.title(),
                                    (j.get("location") or {}).get("name", "Remote"),
                                    j.get("absolute_url"), j.get("content", ""),
                                    src="Company ATS"))
            except Exception:
                pass

    async def _lv(slug):
        async with sem:
            try:
                r = await client.get(
                    f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=15",
                    timeout=10)
                for j in (r.json() or []):
                    out.append(_rec(j.get("text"), slug.title(),
                                    (j.get("categories") or {}).get("location", "Remote"),
                                    j.get("hostedUrl"), j.get("descriptionPlain", ""),
                                    src="Company ATS"))
            except Exception:
                pass

    async def _ab(slug):
        async with sem:
            try:
                r = await client.get(
                    f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=10)
                for j in (r.json().get("jobs") or [])[:15]:
                    out.append(_rec(j.get("title"), slug.title(),
                                    j.get("location") or "Remote",
                                    j.get("jobUrl") or j.get("applyUrl") or "",
                                    j.get("descriptionPlain") or "", src="Company ATS"))
            except Exception:
                pass

    async def _wk(slug):
        async with sem:
            try:
                r = await client.get(
                    f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=false",
                    timeout=10)
                for j in (r.json().get("jobs") or [])[:15]:
                    loc = ", ".join(x for x in (j.get("city"), j.get("country")) if x) or "Remote"
                    out.append(_rec(j.get("title"), slug.title(), loc,
                                    j.get("url") or
                                    f"https://apply.workable.com/{slug}/j/{j.get('shortcode','')}",
                                    j.get("description") or "", src="Company ATS"))
            except Exception:
                pass

    async def _sr(slug):
        async with sem:
            try:
                r = await client.get(
                    f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=15",
                    timeout=10)
                for j in (r.json().get("content") or []):
                    loc = (j.get("location") or {})
                    loc_s = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x) or "Remote"
                    out.append(_rec(j.get("name"), slug.title(), loc_s,
                                    f"https://jobs.smartrecruiters.com/{slug}/{j.get('id','')}",
                                    "", src="Company ATS"))
            except Exception:
                pass

    async def _rt(slug):
        async with sem:
            try:
                r = await client.get(f"https://{slug}.recruitee.com/api/offers/", timeout=10)
                for j in (r.json().get("offers") or [])[:15]:
                    out.append(_rec(j.get("title"), slug.title(),
                                    j.get("location") or "Remote",
                                    j.get("careers_url") or "",
                                    re.sub(r"<[^>]+>", " ", j.get("description") or "")[:400],
                                    src="Company ATS"))
            except Exception:
                pass

    _FETCHERS = {"greenhouse": _gh, "lever": _lv, "ashby": _ab,
                 "workable": _wk, "smartrecruiters": _sr, "recruitee": _rt}
    tasks = [_FETCHERS[src](s) for s, src in _BOARDS.items() if src in _FETCHERS]
    if tasks:
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=25)
        except Exception:
            pass
    return out


async def _arbeitnow(client, q) -> List[Dict[str, Any]]:
    try:
        r = await client.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
        if r.status_code != 200:
            return []
        return [_rec(j.get("title"), j.get("company_name"), j.get("location", "Remote"),
                     j.get("url"), j.get("description"))
                for j in (r.json().get("data") or []) if j.get("remote")]
    except Exception:
        return []


async def fetch(query: str = "", limit: int = 80, companies: List[str] = None) -> List[Dict[str, Any]]:
    """Pull remote jobs from all aggregators, filter by the query keyword, dedup."""
    q = (query or "").strip()
    qtoks = [t for t in re.split(r"\s+", q.lower()) if len(t) > 2]
    out, seen = [], set()
    try:
        async with httpx.AsyncClient(headers=_UA, verify=False, follow_redirects=True) as client:
            # user's curated company boards FIRST — aggregators fill the limit
            # fast, and whatever is first in this list wins the merge slots
            lists = await asyncio.gather(
                _company_boards(client, q),
                _remotive(client, q), _remoteok(client, q), _jobicy(client, q),
                _arbeitnow(client, q), _themuse(client, q), _adzuna(client, q),
                _wwr(client, q),
                _himalayas(client, q), _jooble(client, q),
                _usajobs(client, q), _careerjet(client, q),
                _workingnomads(client, q), _jobspresso(client, q),
                return_exceptions=True)
        for lst in lists:
            if not isinstance(lst, list):
                continue
            for j in lst:
                title = (j.get("title") or "")
                if not title:
                    continue
                blob = f"{title} {j.get('description','')}".lower()
                if qtoks and not any(t in blob for t in qtoks):
                    continue
                key = (title.lower()[:60] + "|" + (j.get("metadata", {}).get("company", "")).lower())
                if key in seen:
                    continue
                seen.add(key)
                out.append(j)
                if len(out) >= limit:
                    return out
    except Exception as exc:
        logger.info("remote aggregators fetch failed: %s", exc)
    return out

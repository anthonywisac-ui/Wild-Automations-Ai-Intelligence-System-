"""
Job Search — one general engine for any query, any job type, any CV.

Handles remote / freelance / full-time / part-time / internship. Pulls from
multiple sources at once (JobSpy across Indeed + Google + LinkedIn, plus the
Remotive/Arbeitnow remote APIs), normalizes, filters by the requested job type,
and ranks by role + skill overlap. Reuses jobspy_client + gulftalent_client +
job_intelligence.normalize — no new scrapers.

    await search(query="senior project manager", location="", job_type="remote",
                 skills=["agile","scrum"])  ->  {role, count, jobs:[structured]}

Never hardcodes a profession — the query drives everything, so it works for a
nurse, a welder, a PM, a developer, or a freelance designer alike.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# job-type → required / excluded phrases (applied to title+location+description)
_TYPE = {
    "remote":    {"need": ["remote", "work from home", "wfh", "anywhere"],
                  "excl": ["onsite", "on-site", "on site", "hybrid"]},
    "freelance": {"need": ["freelance", "contract", "contractor", "self-employed", "gig"], "excl": []},
    "part-time": {"need": ["part-time", "part time", "parttime"], "excl": ["full-time", "full time"]},
    "full-time": {"need": ["full-time", "full time", "permanent"], "excl": ["part-time", "part time"]},
    "internship": {"need": ["intern", "internship", "trainee", "graduate"], "excl": []},
}
# location restrictions that break "international / anywhere" (only excluded when
# the user explicitly wants worldwide-remote, i.e. no location given + remote)
_RESTRICT = ["us only", "usa only", "u.s. only", "must be based", "within the us",
             "within the united", "eu only", "uk only", "eea", "citizens only",
             "work authorization", "authorized to work", "no visa", "sponsorship not available",
             "cannot sponsor", "not able to sponsor", "us-based", "based in the us",
             "select locations", "must reside"]


async def _safe(fn, cfg, timeout: int = 40) -> List[Dict[str, Any]]:
    try:
        return await asyncio.wait_for(fn(cfg), timeout=timeout) or []
    except Exception as exc:
        logger.info("job_search source failed: %s", exc)
        return []


async def expand_terms(query: str) -> List[str]:
    """Use an LLM (Gemini/Perplexity/Groq via OpenRouter or direct) to widen the
    search into related job titles → more coverage. Empty list if no model."""
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return []
        out = await llm.complete(
            f"List 4 closely-related job titles a candidate searching '{query}' would "
            f"also apply to. Comma-separated, titles only, no numbering.",
            system="You output only a short comma-separated list.", max_tokens=60)
        terms = [t.strip() for t in re.split(r"[,\n]", out) if 2 < len(t.strip()) < 40]
        # drop duplicates / the original
        seen, uniq = {query.lower()}, []
        for t in terms:
            if t.lower() not in seen:
                seen.add(t.lower()); uniq.append(t)
        return uniq[:3]
    except Exception as exc:
        logger.info("job_search expand failed: %s", exc)
        return []


async def search(query: str, location: str = "", job_type: str = "",
                 skills: Optional[List[str]] = None, worldwide: bool = False,
                 limit: int = 30, alt_titles: Optional[List[str]] = None) -> Dict[str, Any]:
    query = (query or "").strip() or "jobs"
    skills = skills or []
    alt_titles = alt_titles or []
    jt = (job_type or "").lower().strip()

    from core import jobspy_client, gulftalent_client, job_intelligence

    loc = location or ("Remote" if jt == "remote" else "")
    # Indeed is country-locked; for worldwide-remote (no country given) use a broad
    # market instead of the UAE default so results aren't UAE-only.
    _CC = {"united kingdom": "uk", "uk": "uk", "usa": "usa", "united states": "usa",
           "america": "usa", "canada": "canada", "australia": "australia",
           "germany": "germany", "india": "india", "uae": "united arab emirates",
           "dubai": "united arab emirates", "pakistan": "pakistan"}
    country_indeed = _CC.get(location.lower(), "usa" if (worldwide or jt == "remote") else "usa")
    jcfg = {"portal_name": "search", "crawl_mode": "jobspy", "jobspy_params": {
        "site_names": ["indeed", "google", "linkedin"], "search_term": query,
        "google_search_term": f"{query} {jt} jobs {location or 'worldwide'}".strip(),
        "country_indeed": country_indeed,
        "location": loc, "results_wanted": 30, "is_remote": jt == "remote"}}
    gcfg = {"portal_name": "remote", "crawl_mode": "gulftalent",
            "gulftalent_params": {"category": query, "results_wanted": 40}}

    tasks = [_safe(jobspy_client.fetch_jobspy, jcfg),
             _safe(gulftalent_client.fetch_gulftalent, gcfg)]
    # remote-first companies' own ATS (Greenhouse/Lever/Ashby) — global, unblocked
    async def _rc():
        try:
            from core import remote_companies_client
            return await asyncio.wait_for(remote_companies_client.fetch(query, limit=120), timeout=40)
        except Exception as exc:
            logger.info("remote_companies source failed: %s", exc)
            return []
    tasks.append(_rc())
    # universal board scraper: HTML-only boards (NoDesk/JustRemote/DailyRemote/
    # Remote.co/Remoters) + IP-blocked boards routed via Jina Reader (Bayt/
    # NaukriGulf/Wellfound) — adaptive LLM extraction, 2h cache, fail-soft
    async def _bs():
        try:
            from core import board_scraper
            return await asyncio.wait_for(board_scraper.fetch_all(query, limit=50), timeout=48)
        except Exception as exc:
            logger.info("board_scraper source failed: %s", exc)
            return []
    tasks.append(_bs())
    # multi-model coverage: also search related titles the LLM suggests
    for alt in await expand_terms(query):
        ac = {"portal_name": "search", "crawl_mode": "jobspy", "jobspy_params": {
            "site_names": ["indeed", "google"], "search_term": alt,
            "google_search_term": f"{alt} {jt} jobs {location}".strip(),
            "location": loc, "results_wanted": 20, "is_remote": jt == "remote"}}
        tasks.append(_safe(jobspy_client.fetch_jobspy, ac))
    lists = await asyncio.gather(*tasks)
    raw = [r for lst in lists for r in (lst or [])]

    want = set(re.findall(r"[a-z]{3,}", (query + " " + " ".join(skills)).lower()))
    # title-gate tokens: the query PLUS known-equivalent titles (e.g. a PM's
    # "Delivery Lead" / "Programme Manager") so synonym roles aren't dropped
    # before the semantic re-ranker ever sees them
    _gate_src = query + " " + " ".join(alt_titles)
    qtoks = [t for t in re.findall(r"[a-z]{3,}", _gate_src.lower()) if len(t) > 2]
    # generic browse ("jobs") = no meaningful tokens → don't title-gate at all
    if set(qtoks) <= {"jobs", "job", "remote"}:
        qtoks = []
    spec = _TYPE.get(jt)

    out: List[Dict[str, Any]] = []
    for rec in raw:
        md = rec.get("metadata") or {}
        title = (rec.get("title") or "")
        if not title or md.get("type") == "uk_sponsor" or "Licensed Sponsor" in title:
            continue
        loc_s = (rec.get("location") or "")
        blob = f"{title} {loc_s} {rec.get('description','')}".lower()

        # job-type gate
        if spec:
            if spec["need"] and not any(n in blob for n in spec["need"]):
                continue
            if any(x in blob for x in spec["excl"]):
                continue
        # worldwide-remote: drop country-restricted / visa-required listings
        if worldwide and any(x in blob for x in _RESTRICT):
            continue
        # relevance: query token in the TITLE, or (looser) ≥2 distinct query
        # tokens anywhere in the blob — so a "Delivery Lead (project management)"
        # style post still reaches the semantic ranker instead of dying here
        if qtoks:
            tl = title.lower()
            if not any(t in tl for t in qtoks) and \
               sum(1 for t in set(qtoks) if t in blob) < 2:
                continue

        toks = set(re.findall(r"[a-z]{3,}", blob))
        overlap = want & toks
        score = round(min(1.0, 0.35 + len(overlap) / (len(want) or 1)), 2)
        nj = job_intelligence.normalize(rec)
        out.append({
            "title": title, "company": nj["employer"]["name"], "location": loc_s or "Remote",
            "job_type": jt.title() or (nj.get("remote") and "Remote" or "—"),
            "remote": nj.get("remote"), "salary": nj["salary"]["display"],
            "salary_usd": nj["salary"].get("usd_annual"),
            "url": rec.get("source_url") or "", "posted": nj.get("posted") or "",
            "skills": nj.get("skills"), "source": md.get("source") or rec.get("_source") or "",
            "why_match": ("Matches on: " + ", ".join(sorted(overlap)[:6])) if overlap else "Relevant to your query",
            "match": score, "description": (rec.get("description") or "")[:400],
        })

    # dedup by title+company, keep best score
    seen: Dict[str, Dict[str, Any]] = {}
    for j in out:
        k = (j["title"].lower()[:60] + "|" + j["company"].lower())
        if k not in seen or j["match"] > seen[k]["match"]:
            seen[k] = j
    jobs = sorted(seen.values(), key=lambda x: x["match"], reverse=True)[:limit]
    return {"query": query, "job_type": jt, "location": location,
            "count": len(jobs), "jobs": jobs}

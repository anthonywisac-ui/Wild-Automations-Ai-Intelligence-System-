"""
LinkedIn Continuous Collector — self-running background lead engine.

Runs forever inside the CRM. Every little while (human-like, randomized), it:
  1. asks the AI Intent Planner for the NEXT rotating decision-maker query
     (dentist owner -> dental clinic owner -> restaurant owner -> ...),
  2. finds LinkedIn profiles via Google SERP (site:linkedin.com/in),
  3. qualifies each through the Qualification Engine (buyers only, competitors
     rejected),
  4. persists QUALIFIED leads (deduped by profile URL) into the CRM store.

Human-like & polite so Google/LinkedIn don't block:
  - randomized 90-240s gap between queries, with occasional longer "coffee breaks"
  - small result count per query
  - exponential backoff when Google shows a CAPTCHA / returns nothing repeatedly

Run:  python -m scripts.linkedin_collector
Stop: Ctrl-C (or kill the process). State persists — restart resumes safely.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import signal
import sys
from datetime import datetime, timezone
from uuid import uuid4

# ensure project root importable when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import intent_planner, qualification_engine as qe, lead_explanation
from core import intent_analyzer
from core import linkedin_collector_store as store
from plugins.repo_integrated_scraper import GoogleSocialScraper

# buying-intent phrases OR'd into the post search — where leads hide in comments/posts
_INTENT_PHRASES = ('"looking for" OR "need a" OR "recommendations for" OR '
                   '"anyone recommend" OR "can someone help"')

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [linkedin-collector] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("linkedin_collector")

GOAL = os.getenv("LINKEDIN_COLLECTOR_GOAL",
                 "clients for my social media marketing agency")
SERVICE = os.getenv("LINKEDIN_COLLECTOR_SERVICE", "social media marketing agency")
LOCATION = os.getenv("LINKEDIN_COLLECTOR_LOCATION", "Dubai")
PER_QUERY = int(os.getenv("LINKEDIN_COLLECTOR_LIMIT", "5"))

# human-like pacing (seconds)
MIN_GAP, MAX_GAP = 90, 240
BREAK_EVERY = (5, 8)          # after this many cycles, take a longer break
BREAK_MIN, BREAK_MAX = 600, 1200
MAX_BACKOFF = 1800

_running = True


def _stop(*_a):
    global _running
    _running = False
    log.info("stop requested — finishing current cycle then exiting")


def _category_from_query(q: str) -> str:
    """Extract the buyer category the rotating query was built around."""
    import re
    m = re.match(r'"([^"]+)"', q or "")
    return m.group(1) if m else ""


def _to_record(lead, category: str, query: str) -> dict:
    return {
        "title": lead.name,
        "description": lead.title or "",
        "metadata": {
            "type": "lead", "category": category, "location": LOCATION,
            "_service": SERVICE, "website": lead.source_url,
            "source": "linkedin_collector", "post_text": lead.title or "",
        },
    }


async def _one_cycle(plan, mode: str) -> int:
    """Run one query, qualify, analyze intent, persist.
    mode='profiles'     -> decision-makers via site:linkedin.com/in
    mode='intent_posts' -> buying-intent POSTS/COMMENTS via site:linkedin.com/posts
    Returns count of NEW qualified leads, or -1 if Google returned nothing."""
    q = intent_planner.linkedin_queries(GOAL, plan, location=LOCATION, count=1)
    if not q:
        return 0
    base = q[0]
    category = _category_from_query(base)

    if mode == "intent_posts":
        # people posting/commenting that they NEED a service = hottest leads
        query = f"({_INTENT_PHRASES}) {category} {LOCATION}"
        scraper = GoogleSocialScraper({"headless": True, "site": "linkedin.com/posts",
                                       "source": "linkedin", "open_posts": True})
    else:
        query = base
        scraper = GoogleSocialScraper({"headless": True, "site": "linkedin.com/in",
                                       "source": "linkedin", "open_posts": False})
    log.info("[%s] query -> %s", mode, query)

    leads = await scraper.fetch_leads(uuid4(), limit=PER_QUERY, query=query)
    if not leads:
        log.info("  0 results (Google may be throttling) - will back off")
        return -1

    new_qualified = 0
    for lead in leads:
        text = lead.title or ""
        # analyze the profile headline + comment/post text for buying intent
        intent = intent_analyzer.analyze(lead.company or lead.name, text)
        if intent["is_seller"]:
            log.info("  x skip seller: %s (%s)", lead.name, intent["basis"][:60])
            continue

        rec = _to_record(lead, category, query)
        result = qe.qualify(rec, service=SERVICE)
        rec["metadata"]["qualification"] = result.as_dict()
        expl = lead_explanation.explain(rec) if result.qualified else {}
        if expl:
            expl["intent"] = intent          # attach transparent intent + basis
        row = {
            "profile_url": lead.source_url, "name": lead.name,
            "headline": text, "company": lead.company or "",
            "location": LOCATION, "category": category, "query": query,
            "qualified": 1 if result.qualified else 0,
            "qualification_score": result.overall, "decision": result.decision,
            "dimensions": result.dimensions, "explanation": expl,
        }
        is_new = store.upsert(row)
        if result.qualified and is_new:
            new_qualified += 1
            tag = f"[{intent['temperature'].upper()}]" if intent["is_lead"] else ""
            log.info("  + QUALIFIED %s %s | %s (score %.0f)%s", lead.name, tag,
                     text[:45], result.overall,
                     f" | intent: {intent['signals']}" if intent["signals"] else "")
    return new_qualified


async def main():
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    log.info("starting — goal=%r service=%r location=%r", GOAL, SERVICE, LOCATION)
    plan = await intent_planner.plan(GOAL)

    cycles = 0
    empties = 0
    next_break = random.randint(*BREAK_EVERY)
    while _running:
        # alternate: decision-maker profiles, then buying-intent posts/comments
        mode = "intent_posts" if cycles % 2 else "profiles"
        try:
            new_q = await _one_cycle(plan, mode)
        except Exception as exc:
            log.warning("cycle error: %s", exc)
            new_q = 0

        st = store.stats()
        log.info("cycle %d done | +%s new | total qualified in CRM: %s",
                 cycles + 1, max(new_q, 0), st.get("qualified"))

        # pacing
        if new_q == -1:  # empty → exponential backoff to respect throttling
            empties += 1
            gap = min(MAX_BACKOFF, MIN_GAP * (2 ** empties)) + random.randint(0, 60)
            log.info("backing off %ds (empty streak %d)", gap, empties)
        else:
            empties = 0
            cycles += 1
            if cycles >= next_break:
                gap = random.randint(BREAK_MIN, BREAK_MAX)
                next_break = cycles + random.randint(*BREAK_EVERY)
                log.info("coffee break %ds (human-like)", gap)
            else:
                gap = random.randint(MIN_GAP, MAX_GAP)
                log.info("next query in %ds", gap)

        # sleep in short slices so stop is responsive
        slept = 0
        while _running and slept < gap:
            await asyncio.sleep(min(5, gap - slept))
            slept += 5

    log.info("stopped. final stats: %s", store.stats())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

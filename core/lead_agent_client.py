"""
Lead Agent client — bridges the social lead scrapers (plugins/scrapers_analyzer.py)
into the standard CRM scraper contract used by test_ui.py + core/pipeline.py.

It exposes the mandated `fetch_leads(portal_config) -> list[dict]` entry point:
runs the social scraping pipeline, maps each LeadRecord to the standard record
schema, and (per the HARD RULES) never raises — on any failure it returns a
small static fallback so the dashboard stays populated.

Sources that actually produce data depend on which keys exist in .env:
  - instagram / google_maps  → Apify (APIFY_API_KEY)          ← works today
  - linkedin                 → Playwright (free) or BrightData/Proxycurl
  - facebook                 → Graph API token or BrightData
Missing keys degrade gracefully to empty for that source.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

logger = logging.getLogger(__name__)

# Fixed demo tenant (single-tenant dashboard). Replace when multi-tenant lands.
_DEMO_TENANT = UUID("00000000-0000-0000-0000-000000000001")

# Apify-backed sources work with the existing APIFY_API_KEY; others need keys.
_DEFAULT_SOURCES = ["instagram", "google_maps"]


def _lead_to_record(lead: Any) -> Dict[str, Any]:
    """Map a LeadRecord (pydantic) to the standard scraper record dict."""
    enr = lead.enrichment_data or {}
    analysis = enr.get("analysis") or {}
    post = enr.get("post") or {}
    role = lead.title or ""
    company = lead.company or ""

    # Post text + comments (Google-search social leads) feed analysis + scoring.
    post_msg = post.get("message") or ""
    comments = post.get("comments") or []

    # Build a human description from role/company/post + analysis summary
    bits = [b for b in (role, company) if b]
    desc = " · ".join(bits) or post_msg
    if analysis.get("summary"):
        desc = f"{desc} — {analysis['summary']}" if desc else analysis["summary"]
    if not desc:
        desc = f"{lead.source} lead"

    # Location best-effort
    place = enr.get("place") or {}
    location = place.get("formatted_address") or place.get("address") or place.get("location") or ""

    title = f"{lead.name}" + (f" — {role}" if role else "")

    return {
        "title": title,
        "source_url": lead.source_url,
        "description": desc[:400],
        "location": location,
        "price": "",
        "metadata": {
            "type": "lead",
            "source": f"{lead.source}_live",
            "platform": lead.source,
            "company": company,
            "role": role,
            "email": lead.email,
            "phone": lead.phone,
            "followers": enr.get("followers"),
            "rating": place.get("rating"),
            "review_count": place.get("review_count"),
            "category": place.get("category"),
            "post_text": (post_msg or desc)[:600],
            "comments": comments,
            "lead_score": lead.score,
            "status": lead.status,
            "buying_signals": analysis.get("buying_signals", []),
            "sentiment": analysis.get("sentiment"),
            "intent": analysis.get("intent"),
            "actionable": analysis.get("actionable"),
            "scraped_at": (lead.crawled_at or datetime.utcnow()).isoformat()
                          if hasattr(lead, "crawled_at") else datetime.utcnow().isoformat(),
        },
    }


async def _plan_targets(params: Dict[str, Any]) -> Dict[str, Any]:
    """Think-first: if a business `goal` is set, generate buyer-intent queries via the
    Intent Planner and rotate them into the scraper targets. Manual targets override."""
    targets = dict(params.get("targets") or {})
    goal = params.get("goal")
    if not goal:
        return targets
    try:
        from core import intent_planner
        plan = await intent_planner.plan(goal)
        rotated = intent_planner.next_queries(goal, plan, count=1)
        if rotated and not targets.get("social_query"):
            targets["social_query"] = rotated[0]
        gk = plan.get("gmaps_keywords") or []
        if gk and not targets.get("gmaps_keyword"):
            targets["gmaps_keyword"] = gk[0]
        targets["_plan"] = {
            "origin": plan.get("_origin"),
            "query_used": targets.get("social_query"),
            "personas": (plan.get("buyer_personas") or [])[:5],
            "pool_size": len(intent_planner.pooled_queries(plan)),
        }
        logger.info("lead_agent_client: intent plan (%s) query='%s'",
                    plan.get("_origin"), targets.get("social_query"))
    except Exception as exc:
        logger.warning("lead_agent_client: intent planning failed: %s", exc)
    return targets


async def fetch_leads(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Standard scraper entry point. Never raises — returns records or fallback."""
    params = portal_config.get("lead_params") or {}
    sources = params.get("sources") or _DEFAULT_SOURCES
    limit = int(params.get("results_wanted", 5))
    analyze = bool(params.get("analyze", True))
    use_stealth = bool(params.get("use_stealth", True))

    # Think-first: plan buyer-intent queries from the goal (with rotation).
    planned_targets = await _plan_targets(params)
    goal = params.get("goal")
    query_used = planned_targets.get("social_query")

    def _tag(recs):
        # Attribute each lead to the goal + query for self-learning (signal memory).
        for r in recs:
            md = r.setdefault("metadata", {})
            md["_goal"], md["_query"] = goal, query_used
        return recs

    # 1. Stealth repo-integrated scrapers (agentic-stealth-browser / linkedin-spider
    #    / custom Playwright). Returns [] gracefully if no backend installed.
    if use_stealth:
        try:
            from plugins.repo_integrated_scraper import run_pipeline as run_stealth, stealth_available
            if stealth_available():
                targets = dict(planned_targets)
                targets.setdefault("headless", True)
                leads = await asyncio.wait_for(
                    run_stealth(_DEMO_TENANT, sources=sources, limit_per_source=limit, targets=targets),
                    timeout=85,
                )
                records = _tag([_lead_to_record(l) for l in leads if getattr(l, "source_url", None)])
                if records:
                    logger.info("lead_agent_client: STEALTH fetched=%d leads", len(records))
                    return records
                logger.info("lead_agent_client: stealth returned 0 -> trying Apify")
        except asyncio.TimeoutError:
            logger.warning("lead_agent_client: stealth timed out -> trying Apify")
        except Exception as exc:
            logger.warning("lead_agent_client: stealth error (%s) -> trying Apify", exc)

    # 2. Provider-based scrapers (Apify / BrightData / Proxycurl) + GROQ analysis.
    try:
        from plugins.scrapers_analyzer import run_scraping_pipeline
        leads = await asyncio.wait_for(
            run_scraping_pipeline(_DEMO_TENANT, sources=sources,
                                  limit_per_source=limit, analyze=analyze),
            timeout=40,
        )
        records = _tag([_lead_to_record(l) for l in leads if getattr(l, "source_url", None)])
        if records:
            logger.info("lead_agent_client: LIVE(Apify) fetched=%d leads from %s", len(records), sources)
            return records
        logger.warning("lead_agent_client: 0 live leads (missing keys?) -> fallback")
    except asyncio.TimeoutError:
        logger.warning("lead_agent_client: Apify pipeline timed out -> fallback")
    except Exception as exc:
        logger.warning("lead_agent_client: Apify pipeline error (%s) -> fallback", exc)

    # 3. Static fallback so the dashboard never shows an empty Leads card.
    return _tag(_lead_fallback(sources))


def _lead_fallback(sources: List[str]) -> List[Dict[str, Any]]:
    """Static sample leads so the dashboard never shows an empty Leads card."""
    now = datetime.utcnow().isoformat()
    samples = [
        ("Ava Thompson — Marketing Director", "instagram",
         "https://instagram.com/ava.growth", "Marketing Director · GrowthLabs — mentions 'looking for a better CRM'",
         {"intent": "interested", "sentiment": "positive", "actionable": True, "buying_signals": ["looking for"]}),
        ("Bright Bites Cafe", "google_maps",
         "https://maps.google.com/?cid=brightbites", "Cafe · Dubai — high-rated local business",
         {"intent": "undecided", "sentiment": "neutral", "actionable": False, "buying_signals": []}),
        ("Omar Farooq — Founder", "linkedin",
         "https://linkedin.com/in/omar-founder", "Founder · FinEdge — hiring + scaling ops",
         {"intent": "interested", "sentiment": "positive", "actionable": True, "buying_signals": ["scaling", "need"]}),
    ]
    out = []
    for name, src, url, desc, an in samples:
        if src not in sources and sources:
            continue
        out.append({
            "title": name, "source_url": url, "description": desc,
            "location": "", "price": "",
            "metadata": {"type": "lead", "source": f"{src}_fallback", "platform": src,
                         "buying_signals": an["buying_signals"], "sentiment": an["sentiment"],
                         "intent": an["intent"], "actionable": an["actionable"],
                         "lead_score": 0, "status": "new", "scraped_at": now},
        })
    return out or [{
        "title": "Sample Lead", "source_url": "https://example.com/lead/1",
        "description": "Configure APIFY/LinkedIn keys for live leads.",
        "location": "", "price": "",
        "metadata": {"type": "lead", "source": "lead_fallback", "platform": "demo",
                     "scraped_at": now, "status": "new", "lead_score": 0},
    }]

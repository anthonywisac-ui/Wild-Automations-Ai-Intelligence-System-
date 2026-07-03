"""
WildAutomations — Premium Scraper CRM Dashboard v2
Run:  python test_ui.py
Open: http://localhost:8001
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, AsyncGenerator

sys.path.insert(0, str(Path(__file__).resolve().parent))

logger = logging.getLogger("wildcrm")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
    import uvicorn
except ImportError:
    print("ERROR: pip install fastapi uvicorn")
    sys.exit(1)


# ── Scraper Registry ─────────────────────────────────────────────────────────

SCRAPERS = [
    # ── JOBS ─────────────────────────────────────────────────────────────────
    {
        "name": "Indeed UAE (JobSpy)",
        "bot": "JobSpy Engine",
        "emoji": "💼",
        "category": "Jobs",
        "mode": "API Gateway",
        "module": "core.jobspy_client",
        "fn": "fetch_jobspy",
        "config": {
            "portal_name": "Indeed UAE", "crawl_mode": "jobspy",
            "jobspy_params": {
                "site_names": ["indeed"],
                "search_term": "software engineer",
                "location": "Dubai",
                "country_indeed": "united arab emirates",
                "results_wanted": 5,
            }
        },
    },
    {
        "name": "GulfTalent · Remotive",
        "bot": "Remotive API",
        "emoji": "🎯",
        "category": "Jobs",
        "mode": "API Gateway",
        "module": "core.gulftalent_client",
        "fn": "fetch_gulftalent",
        "config": {
            "portal_name": "GulfTalent", "crawl_mode": "gulftalent",
            "gulftalent_params": {"category": "software-dev", "results_wanted": 5},
        },
    },
    {
        "name": "Greenhouse · WWR · RemoteOK",
        "bot": "ATS Aggregator",
        "emoji": "🏢",
        "category": "Jobs",
        "mode": "ATS APIs",
        "module": "core.ats_client",
        "fn": "fetch_ats_jobs",
        "config": {
            "portal_name": "ATS Jobs", "crawl_mode": "ats_jobs",
            "ats_params": {
                "source": "all",
                "companies": ["airbnb", "stripe", "shopify", "figma", "notion"],
                "limit": 20,
            },
        },
    },
    {
        "name": "UK Sponsored Jobs",
        "bot": "Gov.UK CSV",
        "emoji": "🇬🇧",
        "category": "Jobs",
        "mode": "Gov CSV",
        "module": "core.uk_jobs_client",
        "fn": "fetch_uk_sponsored_jobs",
        "config": {
            "portal_name": "UK Jobs", "crawl_mode": "uk_sponsored_jobs",
            "uk_jobs_params": {"keywords": "software engineer", "max_pages": 1, "results_wanted": 5},
        },
    },

    # ── UNIVERSITY ────────────────────────────────────────────────────────────
    {
        "name": "HIPO Labs · UAE Universities",
        "bot": "HIPO API",
        "emoji": "🎓",
        "category": "University",
        "mode": "API Gateway",
        "module": "core.university_client",
        "fn": "fetch_university_data",
        "config": {
            "portal_name": "HIPO Labs", "crawl_mode": "university_api",
            "university_params": {"source": "hipo", "country": "United Arab Emirates", "limit": 5},
        },
    },
    {
        "name": "THE World Rankings",
        "bot": "Wikipedia Mirror",
        "emoji": "🏆",
        "category": "University",
        "mode": "Static Data",
        "module": "core.university_client",
        "fn": "fetch_university_data",
        "config": {
            "portal_name": "THE Rankings", "crawl_mode": "university_api",
            "university_params": {"source": "the_rankings", "limit": 5},
        },
    },
    {
        "name": "QS World Rankings",
        "bot": "QS Static",
        "emoji": "📊",
        "category": "University",
        "mode": "Static Data",
        "module": "core.qs_client",
        "fn": "fetch_qs_data",
        "config": {
            "portal_name": "QS Rankings", "crawl_mode": "qs_rankings",
            "qs_params": {"source": "world", "limit": 5},
        },
    },
    {
        "name": "College Scorecard · US",
        "bot": "data.gov API",
        "emoji": "🏫",
        "category": "University",
        "mode": "API Gateway",
        "module": "core.university_client",
        "fn": "fetch_university_data",
        "config": {
            "portal_name": "College Scorecard", "crawl_mode": "university_api",
            "university_params": {
                "source": "scorecard",
                "keyword": "engineering",
                "limit": 5,
            },
        },
    },
    {
        "name": "University Admissions",
        "bot": "Scorecard API",
        "emoji": "📚",
        "category": "University",
        "mode": "API Gateway",
        "module": "core.admissions_client",
        "fn": "fetch_admissions_data",
        "config": {
            "portal_name": "Admissions", "crawl_mode": "admissions_data",
            "admissions_params": {"source": "all", "universities": ["MIT", "Harvard", "Oxford"], "limit": 5},
        },
    },
    {
        "name": "Admissions News · PIE · ICEF",
        "bot": "RSS Aggregator",
        "emoji": "📰",
        "category": "University",
        "mode": "RSS Feed",
        "module": "core.admissions_news_client",
        "fn": "fetch_admissions_news",
        "config": {
            "portal_name": "Admissions News", "crawl_mode": "admissions_news",
            "news_params": {"sources": ["pie", "icef", "study_intl"], "limit": 15},
        },
    },
    {
        "name": "Global Admissions · UK / US / Canada",
        "bot": "HIPO + Static DB",
        "emoji": "🌐",
        "category": "University",
        "mode": "Static DB",
        "module": "core.global_admissions_client",
        "fn": "fetch_global_admissions",
        "config": {
            "portal_name": "Global Admissions", "crawl_mode": "global_admissions",
            "global_admissions_params": {"regions": ["uk", "us", "canada"], "limit": 20},
        },
    },
    {
        "name": "Global Admissions · EU / AU / GCC",
        "bot": "HIPO + Static DB",
        "emoji": "🌍",
        "category": "University",
        "mode": "Static DB",
        "module": "core.global_admissions_client",
        "fn": "fetch_global_admissions",
        "config": {
            "portal_name": "Global Admissions", "crawl_mode": "global_admissions",
            "global_admissions_params": {"regions": ["europe", "ireland", "australia", "gcc"], "limit": 20},
        },
    },

    # ── VISA ──────────────────────────────────────────────────────────────────
    {
        "name": "US Visa Bulletin",
        "bot": "DOS Website",
        "emoji": "🇺🇸",
        "category": "Visa",
        "mode": "HTML Parse",
        "module": "core.visa_client",
        "fn": "fetch_visa_data",
        "config": {
            "portal_name": "US Visa Bulletin", "crawl_mode": "visa_bulletin",
            "visa_params": {"source": "us_bulletin"},
        },
    },
    {
        "name": "Canada PR Processing",
        "bot": "IRCC Website",
        "emoji": "🇨🇦",
        "category": "Visa",
        "mode": "HTML Parse",
        "module": "core.visa_client",
        "fn": "fetch_visa_data",
        "config": {
            "portal_name": "Canada PR", "crawl_mode": "visa_bulletin",
            "visa_params": {"source": "canada_pr"},
        },
    },
    {
        "name": "Visa Requirements Index",
        "bot": "Passport Index CSV",
        "emoji": "📋",
        "category": "Visa",
        "mode": "CSV + Fallback",
        "module": "core.visa_client",
        "fn": "fetch_visa_data",
        "config": {
            "portal_name": "Wiki Visa", "crawl_mode": "visa_wiki",
            "visa_params": {"passports": ["pakistani", "indian"]},
        },
    },
    {
        "name": "Passport Index · Henley",
        "bot": "GitHub CSV",
        "emoji": "🛂",
        "category": "Visa",
        "mode": "GitHub CSV",
        "module": "core.passport_index_client",
        "fn": "fetch_passport_index",
        "config": {
            "portal_name": "Passport Index", "crawl_mode": "passport_index",
            "passport_params": {"passports": ["Pakistan", "India", "United Arab Emirates"], "limit": 5},
        },
    },
    {
        "name": "EU Schengen Visa",
        "bot": "EU Stats API",
        "emoji": "🇪🇺",
        "category": "Visa",
        "mode": "API Gateway",
        "module": "core.eu_visa_client",
        "fn": "fetch_eu_visa_data",
        "config": {
            "portal_name": "EU Visa", "crawl_mode": "eu_visa_policy",
            "eu_visa_params": {"source": "stats"},
        },
    },

    # ── AUTOMOBILES ───────────────────────────────────────────────────────────
    {
        "name": "NHTSA Vehicle DB · Toyota",
        "bot": "NHTSA API",
        "emoji": "🚗",
        "category": "Automobiles",
        "mode": "API Gateway",
        "module": "core.car_auction_client",
        "fn": "fetch_car_auction_data",
        "config": {
            "portal_name": "NHTSA Vehicles", "crawl_mode": "car_auction",
            "car_auction_params": {"source": "nhtsa", "make": "Toyota", "results_wanted": 5},
        },
    },
    {
        "name": "NHTSA Vehicle DB · BMW",
        "bot": "NHTSA API",
        "emoji": "🚙",
        "category": "Automobiles",
        "mode": "API Gateway",
        "module": "core.car_auction_client",
        "fn": "fetch_car_auction_data",
        "config": {
            "portal_name": "NHTSA Vehicles", "crawl_mode": "car_auction",
            "car_auction_params": {"source": "nhtsa", "make": "BMW", "results_wanted": 5},
        },
    },

    # ── LEADS (AI Lead Agent) ────────────────────────────────────────────────
    {
        "name": "AI Lead Agent · Social",
        "bot": "Social Lead Engine",
        "emoji": "🧲",
        "category": "Leads",
        "mode": "AI Agent",
        "module": "core.lead_agent_client",
        "fn": "fetch_leads",
        "config": {
            "portal_name": "Social Leads", "crawl_mode": "lead_agent",
            "lead_params": {
                "sources": ["google_maps", "instagram", "linkedin"],
                "results_wanted": 4, "analyze": True, "use_stealth": True,
                # THINK-FIRST: set a business goal → Intent Planner auto-generates
                # rotating buyer-intent queries (no manual social_query needed).
                "goal": "clients for my social media marketing agency",
                "targets": {
                    # gmaps_keyword intentionally omitted → the buyer-first Intent
                    # Planner fills it with a concrete TARGET BUSINESS category
                    # (dentist/restaurant/…), never the service (marketing agency).
                    "gmaps_location": "Dubai",
                    # linkedin_keyword intentionally omitted → the Intent Planner
                    # builds a DYNAMIC, rotating decision-maker query from the plan's
                    # buyer categories (e.g. "dental clinic" ("owner" OR "founder")
                    # Dubai), different each run → more unique LinkedIn leads.
                    "open_posts": False,   # snippets already carry post text; True=comments (slower)
                    "headless": True,
                    # social_query is auto-filled by the Intent Planner (rotated each run)
                },
            },
        },
    },
]

CATEGORIES = ["Jobs", "University", "Visa", "Automobiles", "Leads"]
CAT_ICONS  = {"Jobs": "💼", "University": "🎓", "Visa": "🛂", "Automobiles": "🚗", "Leads": "🧲"}


# ── Runner ────────────────────────────────────────────────────────────────────

async def _run_one(s: Dict) -> Dict:
    t0 = time.time()
    try:
        mod = __import__(s["module"], fromlist=[s["fn"]])
        fn  = getattr(mod, s["fn"])
        # Browser-based agents (Leads) need a longer budget than API scrapers,
        # especially under concurrent load in the full analyze run.
        _timeout = 95 if s.get("category") == "Leads" else 45
        results = await asyncio.wait_for(fn(s["config"]), timeout=_timeout)
        # Wave 1: normalize + validate at the ingestion boundary (additive,
        # non-breaking — cleans strings, attaches entity_type/reliability/
        # confidence, drops junk). Failure here never breaks a working scraper.
        try:
            from core.validate import clean_and_validate
            results, _dropped = clean_and_validate(
                results, source=s.get("name", ""), category=s.get("category", ""))
            if _dropped:
                logger.info("_run_one[%s]: dropped %d junk record(s)", s.get("name"), _dropped)
        except Exception as exc:
            logger.warning("_run_one[%s]: normalize/validate skipped: %s", s.get("name"), exc)
        return {
            "name": s["name"], "bot": s["bot"], "emoji": s["emoji"],
            "category": s.get("category", ""), "mode": s.get("mode", ""),
            "status": "ok", "count": len(results), "elapsed": round(time.time() - t0, 1),
            "results": results[:8], "error": None,
        }
    except asyncio.TimeoutError:
        return {
            "name": s["name"], "bot": s["bot"], "emoji": s["emoji"],
            "category": s.get("category", ""), "mode": s.get("mode", ""),
            "status": "error", "count": 0, "elapsed": 45,
            "results": [], "error": "TimeoutError: scraper took >45s",
        }
    except Exception as exc:
        return {
            "name": s["name"], "bot": s["bot"], "emoji": s["emoji"],
            "category": s.get("category", ""), "mode": s.get("mode", ""),
            "status": "error", "count": 0, "elapsed": round(time.time() - t0, 1),
            "results": [], "error": f"{type(exc).__name__}: {exc}",
        }


# ── FastAPI ───────────────────────────────────────────────────────────────────

app = FastAPI(title="WildAutomations CRM", docs_url=None, redoc_url=None)

_images_dir = Path(__file__).resolve().parent / "images"
if _images_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(_html())


async def _stream_scrapers(indexed_scrapers) -> AsyncGenerator[str, None]:
    """Yield SSE events: result (per row), done (per scraper), stream_end."""
    async def run_and_tag(idx, s):
        return idx, await _run_one(s)

    tasks = [asyncio.create_task(run_and_tag(i, s)) for i, s in indexed_scrapers]
    for coro in asyncio.as_completed(tasks):
        idx, res = await coro
        for r in res.get("results", []):
            yield f"data: {json.dumps({'type':'result','index':idx,'result':r})}\n\n"
        yield f"data: {json.dumps({'type':'done','index':idx,'source':{'status':res['status'],'elapsed_ms':int(res['elapsed']*1000),'count':res['count'],'error':res['error']}})}\n\n"
    yield 'data: {"type":"stream_end"}\n\n'


@app.get("/api/stream")
async def stream_all():
    return StreamingResponse(
        _stream_scrapers(list(enumerate(SCRAPERS))),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/stream/category/{cat}")
async def stream_category(cat: str):
    indexed = [(i, s) for i, s in enumerate(SCRAPERS) if s.get("category") == cat]
    return StreamingResponse(
        _stream_scrapers(indexed),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/run/{idx}")
async def run_single(idx: int):
    if idx < 0 or idx >= len(SCRAPERS):
        return JSONResponse({"error": "bad index"}, status_code=404)
    res = await _run_one(SCRAPERS[idx])
    return JSONResponse({
        "status": res["status"], "count": res["count"],
        "elapsed": int(res["elapsed"] * 1000),
        "results": res["results"], "error": res["error"],
    })

# -- AI Analyzer (post-processing value-scoring layer) --

_ANALYSIS_CACHE = Path(__file__).resolve().parent / "data" / "ai_analysis.json"
_ANALYSIS_TTL_HOURS = 24


async def _collect_all_records() -> list:
    """Run every scraper once and flatten results, tagging category + source."""
    tasks = [asyncio.create_task(_run_one(s)) for s in SCRAPERS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    records = []
    for s, res in zip(SCRAPERS, results):
        if isinstance(res, Exception) or res.get("status") != "ok":
            continue
        for r in res.get("results", []):
            r = dict(r)
            r["_category"] = s.get("category", "")
            r["_source"] = s.get("name", "")
            records.append(r)
    return records


@app.get("/api/analyze")
async def analyze(refresh: bool = False):
    """Score & rank all scraped records by Universal Appeal. Cached 24h."""
    from core import ai_analyzer

    if not refresh and _ANALYSIS_CACHE.exists():
        try:
            cached = json.loads(_ANALYSIS_CACHE.read_text(encoding="utf-8"))
            gen = cached.get("summary", {}).get("generated_at", "")
            if gen:
                age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(gen)).total_seconds() / 3600
                if age_h < _ANALYSIS_TTL_HOURS:
                    cached["cached"] = True
                    return JSONResponse(cached)
        except (ValueError, KeyError, json.JSONDecodeError):
            pass

    records = await _collect_all_records()

    # Run through the full CRM pipeline: dedupe → persist → score(history) →
    # AI enrich → match/deliver. Falls back to plain scoring if pipeline fails.
    try:
        from core.pipeline import get_pipeline
        result = await get_pipeline().process(records, do_match=True, do_deliver=False)
        payload = {"summary": result["summary"], "records": result["records"],
                   "stages": result["stages"]}
    except Exception as exc:
        logger.warning("analyze: pipeline failed (%s), using direct scoring", exc)
        scored = ai_analyzer.analyze_records(records)
        payload = {"summary": ai_analyzer.summarize(scored), "records": scored,
                   "stages": {"pipeline": {"active": False, "error": str(exc)}}}

    try:
        _ANALYSIS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _ANALYSIS_CACHE.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass

    payload["cached"] = False
    return JSONResponse(payload)


# ── Wave 2: Search Planner (think-first) — read-only, traceable ───────────────

@app.get("/api/search-plan")
async def search_plan(service: str, campaign: str = "lead_generation", location: str = ""):
    """Return a traceable SearchPlan: personas → pains → platform-specific
    queries (with provenance) → ranked sources. Does not execute any scrape."""
    try:
        from core.search_planner import plan_campaign
        plan = await plan_campaign(service, campaign, location=location)
        return JSONResponse(plan.model_dump())
    except Exception as exc:
        logger.warning("search-plan failed: %s", exc)
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


# ── Wave 5: Feedback loop — CRM events → Learning Engine ──────────────────────

@app.post("/api/crm/event")
async def crm_event(canonical_id: str = "", event_type: str = "", value: float = None):
    """Record a CRM outcome (contact/reply/booking/sale/won/lost/...) and feed the
    Learning Engine (closes the loop: CRM → learning → adaptive weights)."""
    try:
        from core.event_timeline import EventType
        from core.learning_engine import record_outcome
        try:
            et = EventType(event_type)
        except ValueError:
            return JSONResponse({"error": f"unknown event_type '{event_type}'"}, status_code=400)
        result = record_outcome(canonical_id, et, value=value)
        return JSONResponse({"status": "recorded", **result})
    except Exception as exc:
        logger.warning("crm_event failed: %s", exc)
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.get("/api/crm/insights")
async def crm_insights():
    """Learning transparency: outcome attribution + event/registry/feature stats."""
    try:
        from core import (learning_engine, event_timeline, canonical_store,
                          enrichment_cache, feature_store, rejection_store)
        return JSONResponse({
            "attribution": learning_engine.attribution_summary(),
            "events": event_timeline.stats(),
            "canonical_registry": canonical_store.stats(),
            "enrichment_cache": enrichment_cache.stats(),
            "feature_store": feature_store.stats(),
            "rejections": rejection_store.stats(),
        })
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.post("/api/qualification/audit")
async def qualification_audit(request: Request):
    """Qualification Audit — deterministically explain the qualify/reject decision
    for one business. Body: {name/title, category, location, rating, review_count,
    website, phone, service}. Returns every dimension (score/confidence/evidence/
    explanation), the overall score, and the enrichment decision."""
    try:
        from core import qualification_engine as qe
        body = await request.json()
        service = body.get("service", "")
        record = {
            "title": body.get("name") or body.get("title", ""),
            "description": body.get("description", ""),
            "metadata": {
                "type": "lead",
                "category": body.get("category", ""),
                "location": body.get("location", ""),
                "rating": body.get("rating"),
                "review_count": body.get("review_count"),
                "website": body.get("website"),
                "phone": body.get("phone"),
                "email": body.get("email"),
                "post_text": body.get("post_text", ""),
            },
        }
        result = qe.qualify(record, service=service)
        return JSONResponse(result.as_dict())
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.get("/api/qualification/rejected")
async def qualification_rejected(limit: int = 50, decision: str = ""):
    """List persisted rejected/blacklisted businesses with structured reasons."""
    try:
        from core import rejection_store
        return JSONResponse({"rejected": rejection_store.recent(limit=limit, decision=decision),
                             "stats": rejection_store.stats()})
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.get("/api/linkedin/collected")
async def linkedin_collected(limit: int = 100):
    """Qualified LinkedIn leads accumulated by the continuous background collector."""
    try:
        from core import linkedin_collector_store
        try:
            from core import proxy_pool
            proxies = proxy_pool.stats()
        except Exception:
            proxies = {}
        return JSONResponse({"stats": linkedin_collector_store.stats(),
                             "proxies": proxies,
                             "leads": linkedin_collector_store.qualified(limit=limit)})
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.get("/api/leads/export")
async def leads_export(format: str = "json"):
    """Export the latest run's qualified leads as CRM/automation-ready rows.
    Every row carries scores, answer set, evidence, and trace context — no manual
    cleaning required. format=json (default) or csv."""
    try:
        from core import lead_export
        if not _ANALYSIS_CACHE.exists():
            return JSONResponse({"error": "no analysis run yet — call /api/analyze first"},
                                status_code=404)
        payload = json.loads(_ANALYSIS_CACHE.read_text(encoding="utf-8"))
        scored = payload.get("records", [])
        if format.lower() == "csv":
            return StreamingResponse(
                iter([lead_export.to_csv(scored)]), media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=leads.csv"})
        rowset = lead_export.rows(scored)
        return JSONResponse({"count": len(rowset), "leads": rowset})
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


# ── AI Concierge (persona intake → targeted run → match) ──────────────────────
@app.get("/concierge", response_class=HTMLResponse)
async def concierge_page():
    """Mobile-first AI Concierge chat UI (persona tap → intake → results → send)."""
    from concierge_page import CONCIERGE_HTML
    return HTMLResponse(CONCIERGE_HTML)


@app.get("/api/concierge/personas")
async def concierge_personas():
    """List the user personas + the info the assistant must collect for each."""
    from core import concierge
    return JSONResponse({"personas": concierge.personas()})


@app.post("/api/concierge/analyze-cv")
async def concierge_analyze_cv(request: Request):
    """Extract role/skills/location/seniority from CV text (auto-fills job intake)."""
    try:
        from core import concierge
        body = await request.json()
        return JSONResponse(await concierge.analyze_cv(body.get("cv_text", "")))
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.post("/api/concierge/chat")
async def concierge_chat(request: Request):
    """General assistant chat (GROQ; safe fallback without a key)."""
    try:
        from core import concierge
        body = await request.json()
        reply = await concierge.chat(body.get("message", ""), body.get("history"))
        return JSONResponse({"reply": reply})
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.post("/api/concierge/run")
async def concierge_run(request: Request):
    """The core flow: for a persona + answers, patch the relevant scrapers' params,
    run them, and return requirement-ranked matches."""
    try:
        from core import concierge
        body = await request.json()
        persona = body.get("persona", "")
        answers = body.get("answers", {}) or {}
        category = concierge.category_for(persona)
        if not category:
            return JSONResponse({"error": f"unknown persona '{persona}'"}, status_code=400)

        # job seekers: if a CV was pasted, auto-fill missing role/location
        if persona == "job_seeker" and answers.get("cv_text") and not answers.get("role"):
            cv = await concierge.analyze_cv(answers["cv_text"])
            answers.setdefault("role", cv.get("role", ""))
            if not answers.get("location"):
                answers["location"] = cv.get("location", "")

        targets = [{**s, "config": concierge.patch_config(s.get("config", {}), persona, answers)}
                   for s in SCRAPERS if s.get("category") == category]
        results = await asyncio.gather(*[_run_one(t) for t in targets], return_exceptions=True)
        records: list = []
        sources = []
        for t, r in zip(targets, results):
            if isinstance(r, dict):
                sources.append({"name": t.get("name"), "count": r.get("count", 0),
                                "status": r.get("status")})
                records.extend(r.get("results") or [])
        ranked = concierge.rank(records, persona, answers)
        top = ranked[:20]

        delivery = None
        if body.get("deliver"):
            from core import concierge_delivery
            delivery = await concierge_delivery.deliver_matches(
                persona, answers, top, to=body.get("to"))

        return JSONResponse({
            "persona": persona, "category": category,
            "requirement": answers, "sources": sources,
            "total": len(ranked), "matches": top, "delivery": delivery,
        })
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.post("/api/concierge/deliver")
async def concierge_deliver(request: Request):
    """Send an already-computed match set to WhatsApp (WHAPI/Meta)."""
    try:
        from core import concierge_delivery
        body = await request.json()
        result = await concierge_delivery.deliver_matches(
            body.get("persona", ""), body.get("requirement", {}) or {},
            body.get("matches", []) or [], to=body.get("to"))
        return JSONResponse({"channels": concierge_delivery.channels_available(), **result})
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.post("/api/concierge/my-data")
async def concierge_my_data(request: Request):
    """"Tell me about my data" — summarize what's stored (records + qualified leads)."""
    try:
        from core import concierge
        from core.pipeline import get_pipeline
        body = await request.json()
        question = body.get("question", "Summarize my data")
        store = get_pipeline().store
        total = await store.count()
        try:
            from core import linkedin_collector_store, rejection_store, feature_store
            extra = {"linkedin_collected": linkedin_collector_store.stats(),
                     "rejections": rejection_store.stats(),
                     "features": feature_store.stats()}
        except Exception:
            extra = {}
        facts = {"backend": store.backend_name(), "records_stored": total, **extra}
        reply = await concierge.chat(
            f"My CRM data facts: {facts}. Question: {question}. Answer briefly using only these facts.")
        return JSONResponse({"facts": facts, "answer": reply})
    except Exception as exc:
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)


# ── HTML ─────────────────────────────────────────────────────────────────────

def _html() -> str:
    scrapers_js   = json.dumps([{
        "name": s["name"], "bot": s["bot"], "emoji": s["emoji"],
        "category": s.get("category",""), "mode": s.get("mode",""),
    } for s in SCRAPERS])
    categories_js = json.dumps(CATEGORIES)
    cat_icons_js  = json.dumps(CAT_ICONS)
    n = len(SCRAPERS)
    return _PAGE(scrapers_js, categories_js, cat_icons_js, n)


def _PAGE(scrapers_js, categories_js, cat_icons_js, n) -> str:  # noqa: E501
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wild Automations CRM</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#050505;
  --card:#0C0C0C;
  --gold:#E2B404;
  --gold-border:rgba(226,180,4,.25);
  --gold-dim:rgba(226,180,4,.10);
  --gold-glow:rgba(226,180,4,.12);
  --white:#F5F5F5;
  --secondary:#8E8E8E;
  --muted-border:rgba(255,255,255,.08);
  --sb-bg:#080808;
  --font:'Noto Sans',sans-serif;
}}
html,body{{height:100%;overflow:hidden;background:var(--bg);color:var(--white);font-family:var(--font);-webkit-font-smoothing:antialiased;font-size:13px}}
::-webkit-scrollbar{{width:3px;height:3px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:rgba(226,180,4,.18);border-radius:4px}}

/* LAYOUT */
.layout{{display:flex;height:100vh;overflow:hidden}}

/* SIDEBAR */
.sidebar{{width:178px;min-width:178px;background:#010000;display:flex;flex-direction:column;border-right:1px solid var(--muted-border);overflow:hidden;flex-shrink:0}}
.sb-brand{{padding:26px 20px 18px;display:flex;flex-direction:column;align-items:center;gap:10px;border-bottom:1px solid var(--muted-border)}}
.sb-logo-img{{width:52px;height:52px;object-fit:contain}}
.sb-logo-fallback{{width:52px;height:52px;border-radius:12px;background:linear-gradient(135deg,#E2B404,#8a6c00);display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:900;color:#050505;font-family:var(--font)}}
.sb-brand-name{{font-size:11px;font-weight:700;color:var(--white);letter-spacing:2.5px;text-align:center;line-height:1.3}}
.sb-nav{{padding:14px 10px;display:flex;flex-direction:column;gap:2px;overflow:visible}}
.sb-item{{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:10px;cursor:pointer;color:var(--secondary);font-size:13px;font-weight:500;border:none;background:transparent;width:100%;text-align:left;font-family:var(--font);transition:background .15s,color .15s;position:relative;letter-spacing:0.1px}}
.sb-item svg{{flex-shrink:0;width:16px;height:16px;stroke:currentColor;transition:stroke .15s;opacity:.7}}
.sb-item:hover{{color:var(--white);background:rgba(255,255,255,.04)}}
.sb-item:hover svg{{opacity:1}}
.sb-item.active{{background:rgba(226,180,4,.14);color:var(--white);box-shadow:0 0 18px rgba(226,180,4,.08)}}
.sb-item.active svg{{stroke:var(--gold);opacity:1}}
.sb-item-label{{font-size:13px;font-weight:500}}
.sb-spacer{{flex:1}}
.sb-divider{{height:1px;background:var(--muted-border);margin:6px 10px}}
.sb-artwork{{padding:0 0 0;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.sb-artwork-img{{width:100%;object-fit:contain;display:block}}
.sb-artwork-fallback{{width:140px;height:140px;margin:10px auto;position:relative;display:flex;align-items:center;justify-content:center}}
.sb-profile{{display:flex;align-items:center;gap:10px;padding:12px 14px 16px;border-top:1px solid var(--muted-border);flex-shrink:0}}
.sb-avatar{{width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#E2B404,#7a5800);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#050505;flex-shrink:0;font-family:var(--font)}}
.sb-user-info .uname{{font-size:12px;font-weight:600;color:var(--white);line-height:1.3}}
.sb-user-info .uemail{{font-size:10px;color:var(--secondary);margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100px}}
.sb-profile-chevron{{margin-left:auto;color:var(--secondary);flex-shrink:0}}

/* MAIN */
.main{{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}}

/* HEADER */
.header{{background:var(--sb-bg);border-bottom:1px solid var(--muted-border);padding:20px 28px 16px;flex-shrink:0}}
.header-row{{display:flex;align-items:center;justify-content:space-between;gap:20px}}
.header-left{{display:flex;align-items:center;gap:12px}}
.h-sdot{{width:8px;height:8px;border-radius:50%;background:#2a2a2a;flex-shrink:0;transition:all .3s}}
.h-sdot.gold{{background:var(--gold);box-shadow:0 0 10px rgba(226,180,4,.7)}}
.h-sdot.green{{background:#22c55e;box-shadow:0 0 10px rgba(34,197,94,.6)}}
.h-sdot.red{{background:#ef4444}}
.h-title{{font-size:20px;font-weight:700;color:var(--white);letter-spacing:-.3px;line-height:1.2}}
.h-sub{{font-size:12px;font-weight:400;color:var(--secondary);margin-top:3px}}
.header-right{{display:flex;align-items:center;gap:10px}}
.h-cat-pill{{padding:6px 16px;border:1px solid var(--muted-border);border-radius:999px;font-size:12px;font-weight:500;color:var(--secondary);background:transparent;white-space:nowrap}}
.h-run-btn{{display:inline-flex;align-items:center;gap:7px;padding:8px 20px;background:linear-gradient(135deg,#E2B404 0%,#c9a000 100%);color:#050505;border:none;border-radius:12px;font-size:13px;font-weight:600;cursor:pointer;font-family:var(--font);letter-spacing:.2px;box-shadow:0 4px 18px rgba(226,180,4,.28),0 0 0 1px rgba(226,180,4,.15);transition:all .15s ease;white-space:nowrap}}
.h-run-btn:hover{{background:linear-gradient(135deg,#f0c500 0%,#d4ab00 100%);box-shadow:0 6px 24px rgba(226,180,4,.38);transform:translateY(-1px)}}
.h-run-btn svg{{width:12px;height:12px;fill:#050505;stroke:none;flex-shrink:0}}
.h-last-run{{font-size:11px;font-weight:400;color:var(--secondary);white-space:nowrap}}

/* FILTER BAR */
.filter-bar{{background:var(--sb-bg);border-bottom:1px solid var(--muted-border);padding:9px 28px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;flex-shrink:0}}
.f-label{{font-size:10px;font-weight:500;color:#555;text-transform:uppercase;letter-spacing:1px;white-space:nowrap}}
.f-inp{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);color:var(--white);border-radius:10px;padding:5px 10px;font-size:11px;font-weight:400;outline:none;font-family:var(--font);height:28px;transition:border .15s}}
.f-inp:focus{{border-color:rgba(226,180,4,.4);background:rgba(226,180,4,.04)}}
.f-inp option{{background:#111;color:var(--white)}}
.f-sep{{width:1px;height:14px;background:rgba(255,255,255,.07);flex-shrink:0}}
.f-clear{{font-size:11px;color:#444;background:none;border:none;cursor:pointer;font-family:var(--font);padding:3px 7px;transition:color .15s}}
.f-clear:hover{{color:var(--gold)}}
.f-active{{font-size:11px;color:var(--gold);margin-left:auto}}

/* KPI STRIP */
.kpi-strip{{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--muted-border);background:var(--card);flex-shrink:0}}
.kpi-card{{display:flex;align-items:center;gap:18px;padding:20px 24px;border-right:1px solid var(--muted-border)}}
.kpi-card:last-child{{border-right:none}}
.kpi-ring{{width:52px;height:52px;border-radius:50%;border:1px solid var(--gold-border);display:flex;align-items:center;justify-content:center;flex-shrink:0;background:rgba(226,180,4,.04)}}
.kpi-ring svg{{width:20px;height:20px;stroke:var(--gold);stroke-width:1.5;fill:none;stroke-linecap:round;stroke-linejoin:round}}
.kpi-content{{min-width:0}}
.kpi-num{{font-size:36px;font-weight:700;color:var(--white);letter-spacing:-1.5px;line-height:1;font-family:var(--font)}}
.kpi-lbl{{font-size:10px;font-weight:500;color:var(--secondary);text-transform:uppercase;letter-spacing:1.5px;margin-top:5px}}

/* CHIP BAR */
.chip-bar{{background:var(--sb-bg);border-bottom:1px solid var(--muted-border);padding:10px 28px;display:flex;align-items:center;gap:6px;flex-shrink:0;overflow-x:auto;min-height:42px}}
.chip-info{{display:flex;align-items:center;gap:6px;font-size:11px;font-weight:400;color:var(--secondary);white-space:nowrap;flex-shrink:0;margin-right:6px}}
.chip-info svg{{width:12px;height:12px;stroke:var(--secondary);stroke-width:2;fill:none}}
.chip{{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:999px;font-size:11px;font-weight:500;background:#0f0f0f;border:1px solid rgba(255,255,255,.09);color:var(--secondary);white-space:nowrap;transition:all .15s;flex-shrink:0}}
.chip svg{{width:11px;height:11px;stroke:currentColor;stroke-width:2.5;fill:none;flex-shrink:0}}
.chip.ok{{border-color:rgba(226,180,4,.3);background:rgba(226,180,4,.07);color:var(--gold)}}
.chip.err{{border-color:rgba(239,68,68,.25);background:rgba(239,68,68,.06);color:#f87171}}
.chip.running{{border-color:rgba(226,180,4,.3);background:rgba(226,180,4,.07);color:var(--gold)}}

/* CARD AREA */
.card-area{{flex:1;overflow-y:auto;padding:22px 24px;background:var(--bg)}}
.empty-state{{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;text-align:center;gap:16px}}
.empty-icon{{font-size:36px;opacity:.07}}
.empty-msg{{font-size:14px;font-weight:600;color:#333}}
.empty-msg span{{color:var(--gold)}}
.empty-sub{{font-size:12px;color:#2a2a2a}}

/* CATEGORY SECTION */
.cat-section{{margin-bottom:28px}}
.cat-hdr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;padding:0 2px}}
.cat-hdr-left{{display:flex;align-items:center;gap:9px}}
.cat-emoji{{font-size:14px;line-height:1}}
.cat-name{{font-size:10px;font-weight:600;color:var(--secondary);text-transform:uppercase;letter-spacing:3px}}
.cat-count{{font-size:10px;font-weight:500;color:var(--gold);padding:2px 8px;border:1px solid var(--gold-border);border-radius:999px;background:var(--gold-dim)}}
.run-cat-btn{{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;background:transparent;border:1px solid rgba(255,255,255,.1);border-radius:12px;font-size:11px;font-weight:600;color:var(--secondary);cursor:pointer;font-family:var(--font);transition:all .15s}}
.run-cat-btn:hover{{border-color:var(--gold-border);color:var(--gold);background:var(--gold-dim)}}
.run-cat-btn svg{{width:10px;height:10px;fill:currentColor;stroke:none}}
.card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px}}

/* CARD */
.card{{background:var(--card);border:1px solid var(--gold-border);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 2px 20px rgba(0,0,0,.5),0 0 24px rgba(226,180,4,.04);transition:border-color .15s,box-shadow .15s}}
.card:hover{{border-color:rgba(226,180,4,.42);box-shadow:0 4px 28px rgba(0,0,0,.6),0 0 24px rgba(226,180,4,.08)}}

/* CARD HEADER */
.card-hdr{{padding:14px 16px 0;flex-shrink:0}}
.card-hdr-row1{{display:flex;align-items:center;gap:9px;margin-bottom:10px}}
.card-emoji{{font-size:19px;flex-shrink:0;line-height:1}}
.card-name{{font-size:14px;font-weight:600;color:var(--white);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.card-sdot{{width:7px;height:7px;border-radius:50%;background:#2a2a2a;flex-shrink:0;transition:all .25s}}
.card-sdot.ok{{background:var(--gold);box-shadow:0 0 8px rgba(226,180,4,.6)}}
.card-sdot.error{{background:#ef4444}}
.card-sdot.running{{background:var(--gold);box-shadow:0 0 8px rgba(226,180,4,.6)}}
.card-hdr-row2{{display:flex;align-items:center;justify-content:space-between;gap:8px;padding-bottom:12px;border-bottom:1px solid var(--muted-border)}}
.mode-pill{{display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;border:1px solid rgba(226,180,4,.3);background:rgba(226,180,4,.07);color:var(--gold);font-size:10px;font-weight:500;white-space:nowrap;letter-spacing:.2px}}
.bot-name{{font-size:11px;font-weight:400;color:var(--secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:right}}

/* CARD BODY */
.card-body{{flex:1;overflow-y:auto;max-height:280px}}
.no-results{{padding:28px 16px;text-align:center;font-size:11px;color:#333}}

/* RESULT ROW */
.res-row{{padding:10px 16px;cursor:pointer;border-bottom:1px solid rgba(255,255,255,.035);transition:background .12s}}
.res-row:hover{{background:rgba(226,180,4,.03)}}
.res-row:last-child{{border-bottom:none}}
.res-title{{font-size:12.5px;font-weight:500;color:var(--white);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.35;margin-bottom:3px}}
.res-desc{{font-size:11px;font-weight:400;color:var(--secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.35;margin-bottom:6px}}
.res-meta{{display:flex;align-items:center;gap:5px;flex-wrap:nowrap}}
.loc-badge{{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:999px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);color:var(--secondary);font-size:10px;font-weight:400;white-space:nowrap;max-width:160px;overflow:hidden;text-overflow:ellipsis}}
.loc-badge svg{{width:10px;height:10px;stroke:var(--secondary);stroke-width:2;fill:none;flex-shrink:0}}
.badge-sal{{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.2);color:#4ade80;font-size:10px;font-weight:400}}
.badge-gold{{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;background:var(--gold-dim);border:1px solid var(--gold-border);color:var(--gold);font-size:10px;font-weight:400}}
.badge-new{{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.2);color:#4ade80;font-size:10px;font-weight:400}}
.badge-used{{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;background:rgba(251,191,36,.07);border:1px solid rgba(251,191,36,.2);color:#fbbf24;font-size:10px;font-weight:400}}
.open-link{{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:500;color:var(--gold);text-decoration:none;margin-left:auto;flex-shrink:0;transition:opacity .15s}}
.open-link:hover{{opacity:.75}}
.open-link svg{{width:10px;height:10px;stroke:var(--gold);stroke-width:2.5;fill:none}}

/* CARD FOOTER */
.card-ftr{{display:flex;align-items:center;gap:8px;padding:9px 14px;border-top:1px solid var(--muted-border);background:rgba(0,0,0,.2);flex-shrink:0}}
.ftr-items{{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:500;color:var(--secondary)}}
.ftr-items svg{{width:11px;height:11px;stroke:var(--secondary);stroke-width:2;fill:none}}
.ftr-time{{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:400;color:var(--secondary)}}
.ftr-time svg{{width:11px;height:11px;stroke:var(--secondary);stroke-width:2;fill:none}}
.ftr-err{{font-size:10px;color:rgba(239,68,68,.55);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:110px}}
.rerun-btn{{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;background:transparent;color:var(--secondary);border:1px solid rgba(255,255,255,.1);border-radius:8px;font-size:11px;font-weight:600;cursor:pointer;font-family:var(--font);transition:all .15s;margin-left:auto}}
.rerun-btn:hover{{border-color:var(--gold-border);color:var(--gold);background:var(--gold-dim)}}
.rerun-btn svg{{width:11px;height:11px;stroke:currentColor;stroke-width:2;fill:none}}

/* MODAL */
#modal{{position:fixed;inset:0;background:rgba(5,5,5,.88);backdrop-filter:blur(14px);z-index:100;display:none;align-items:center;justify-content:center;padding:24px}}
#modal.show{{display:flex}}
.mbox{{background:var(--card);border:1px solid var(--gold-border);border-radius:20px;width:100%;max-width:640px;max-height:88vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 40px 80px rgba(0,0,0,.8),0 0 40px rgba(226,180,4,.06)}}
.mhdr{{padding:24px 26px 20px;border-bottom:1px solid var(--muted-border);flex-shrink:0}}
.mhdr-top{{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}}
.m-cat-lbl{{display:block;font-size:9.5px;font-weight:600;color:var(--gold);text-transform:uppercase;letter-spacing:2px;margin-bottom:8px}}
.m-title{{font-size:17px;font-weight:700;color:var(--white);line-height:1.3}}
.m-desc{{font-size:12px;font-weight:400;color:var(--secondary);margin-top:8px;line-height:1.65}}
.mclose{{background:rgba(255,255,255,.06);border:1px solid var(--muted-border);border-radius:8px;cursor:pointer;color:var(--secondary);padding:6px;display:flex;line-height:0;flex-shrink:0;transition:all .15s}}
.mclose:hover{{background:var(--gold-dim);border-color:var(--gold-border);color:var(--gold)}}
.mclose svg{{width:15px;height:15px;stroke:currentColor;stroke-width:2.5;fill:none}}
.car-preview{{height:116px;background:#0a0a0a;border-bottom:1px solid var(--muted-border);display:flex;align-items:center;justify-content:center;position:relative;margin-top:16px;border-radius:10px;overflow:hidden}}
.car-preview::before{{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at 40%,rgba(226,180,4,.05),transparent 65%)}}
.car-price-tag{{position:absolute;top:10px;right:12px;font-size:18px;font-weight:700;color:var(--gold)}}
.car-cond-tag{{position:absolute;top:10px;left:12px}}
.car-label{{font-size:12px;font-weight:500;color:#444;position:relative;z-index:2;text-align:center}}
.mbody{{flex:1;overflow-y:auto}}
.mrow{{display:grid;grid-template-columns:148px 1fr;gap:8px;padding:10px 26px;border-bottom:1px solid rgba(255,255,255,.04)}}
.mrow:last-child{{border-bottom:none}}
.mkey{{font-size:9.5px;font-weight:600;color:#444;text-transform:uppercase;letter-spacing:.8px;padding-top:1px}}
.mval{{font-size:12px;font-weight:400;color:#ccc;word-break:break-word;line-height:1.55}}
.mftr{{padding:14px 26px;border-top:1px solid var(--muted-border);display:flex;align-items:center;gap:10px;background:rgba(0,0,0,.25);flex-shrink:0}}
.m-open{{display:inline-flex;align-items:center;gap:7px;padding:9px 22px;background:linear-gradient(135deg,#E2B404,#c49400);color:#050505;border-radius:12px;font-size:12px;font-weight:600;text-decoration:none;box-shadow:0 4px 18px rgba(226,180,4,.22);transition:all .15s}}
.m-open:hover{{box-shadow:0 6px 26px rgba(226,180,4,.35);transform:translateY(-1px)}}
.m-open svg{{width:11px;height:11px;stroke:#050505;stroke-width:2.5;fill:none}}
.m-copy{{display:inline-flex;align-items:center;gap:7px;padding:9px 16px;background:transparent;color:var(--secondary);border:1px solid var(--muted-border);border-radius:12px;font-size:12px;font-weight:500;cursor:pointer;font-family:var(--font);transition:all .15s}}
.m-copy:hover{{border-color:var(--gold-border);color:var(--gold);background:var(--gold-dim)}}
.m-copy svg{{width:11px;height:11px;stroke:currentColor;stroke-width:2.5;fill:none}}
.m-loc{{margin-left:auto;font-size:11px;color:#444}}

/* ANIMATIONS */
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.spin{{animation:spin .75s linear infinite;display:inline-block}}
@keyframes pulse-dot{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.pulse-dot{{animation:pulse-dot 1.5s ease infinite}}

/* ── AI ANALYZER VIEW ─────────────────────────────────────── */
.sb-ai svg{{stroke:var(--gold);opacity:.85}}
.sb-ai.active{{background:rgba(226,180,4,.14);color:var(--white);box-shadow:0 0 18px rgba(226,180,4,.10)}}
.az-kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:22px}}
.az-kpi{{background:var(--card);border:1px solid var(--gold-border);border-radius:14px;padding:16px 18px;position:relative;overflow:hidden}}
.az-kpi.gem{{border-color:rgba(226,180,4,.5);box-shadow:0 0 24px rgba(226,180,4,.08)}}
.az-kpi-num{{font-size:30px;font-weight:700;color:var(--white);letter-spacing:-1px;line-height:1}}
.az-kpi.gem .az-kpi-num{{color:var(--gold)}}
.az-kpi-lbl{{font-size:10px;font-weight:500;color:var(--secondary);text-transform:uppercase;letter-spacing:1.2px;margin-top:8px}}
.az-toolbar{{display:flex;align-items:center;gap:10px;margin-bottom:18px;flex-wrap:wrap}}
.az-seg{{display:inline-flex;gap:2px;background:#0f0f0f;border:1px solid var(--muted-border);border-radius:10px;padding:3px}}
.az-seg button{{padding:6px 14px;border:none;background:transparent;color:var(--secondary);font-size:12px;font-weight:500;cursor:pointer;font-family:var(--font);border-radius:7px;transition:all .15s}}
.az-seg button.on{{background:var(--gold-dim);color:var(--gold)}}
.az-refresh{{margin-left:auto;display:inline-flex;align-items:center;gap:7px;padding:8px 16px;background:linear-gradient(135deg,#E2B404,#c9a000);color:#050505;border:none;border-radius:11px;font-size:12px;font-weight:600;cursor:pointer;font-family:var(--font);box-shadow:0 4px 16px rgba(226,180,4,.25);transition:all .15s}}
.az-refresh:hover{{transform:translateY(-1px);box-shadow:0 6px 22px rgba(226,180,4,.35)}}
.az-refresh svg{{width:12px;height:12px;stroke:#050505;stroke-width:2.5;fill:none}}
.az-cache{{font-size:11px;color:var(--secondary)}}
.az-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}}
.az-card{{background:var(--card);border:1px solid var(--gold-border);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 2px 20px rgba(0,0,0,.5);transition:all .15s;position:relative}}
.az-card:hover{{border-color:rgba(226,180,4,.5);transform:translateY(-2px);box-shadow:0 8px 32px rgba(0,0,0,.6),0 0 24px rgba(226,180,4,.08)}}
.az-card.gem{{border-color:rgba(226,180,4,.55)}}
.az-card.gem::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--gold),transparent)}}
.az-rank{{position:absolute;top:12px;left:12px;width:26px;height:26px;border-radius:50%;background:rgba(0,0,0,.55);border:1px solid var(--gold-border);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--gold);z-index:2}}
.az-c-hdr{{padding:16px 16px 12px 46px;display:flex;align-items:flex-start;gap:10px}}
.az-c-emoji{{font-size:20px;line-height:1;flex-shrink:0}}
.az-c-title{{flex:1;min-width:0}}
.az-c-name{{font-size:13.5px;font-weight:600;color:var(--white);line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.az-c-src{{font-size:10px;color:var(--secondary);margin-top:3px;text-transform:uppercase;letter-spacing:.5px}}
.az-rating{{display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;font-size:10px;font-weight:600;white-space:nowrap;letter-spacing:.3px;flex-shrink:0}}
.az-rating.gem{{background:rgba(226,180,4,.14);border:1px solid var(--gold-border);color:var(--gold)}}
.az-rating.good{{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);color:#4ade80}}
.az-rating.avg{{background:rgba(255,255,255,.05);border:1px solid var(--muted-border);color:var(--secondary)}}
.az-rating.over{{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);color:#f87171}}
.az-score{{padding:0 16px 12px 46px}}
.az-score-row{{display:flex;align-items:center;justify-content:space-between;margin-bottom:5px}}
.az-score-lbl{{font-size:10px;color:var(--secondary);text-transform:uppercase;letter-spacing:1px}}
.az-score-val{{font-size:13px;font-weight:700;color:var(--gold)}}
.az-bar{{height:5px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden}}
.az-bar-fill{{height:100%;background:linear-gradient(90deg,#c9a000,var(--gold));border-radius:3px;transition:width .5s ease}}
.az-flags{{display:flex;flex-wrap:wrap;gap:5px;padding:0 16px 12px}}
.az-flag{{display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:10px;font-weight:500;background:var(--gold-dim);border:1px solid var(--gold-border);color:var(--gold)}}
.az-why{{padding:12px 16px;border-top:1px solid var(--muted-border);background:rgba(0,0,0,.2);font-size:11px;color:var(--secondary);line-height:1.5}}
.az-why b{{color:var(--white);font-weight:600}}
.az-metrics{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--muted-border);border-top:1px solid var(--muted-border)}}
.az-metric{{background:var(--card);padding:9px 14px}}
.az-metric-k{{font-size:9px;color:#555;text-transform:uppercase;letter-spacing:.6px}}
.az-metric-v{{font-size:12px;font-weight:600;color:#ccc;margin-top:2px}}
.az-loading{{display:flex;flex-direction:column;align-items:center;justify-content:center;height:60vh;gap:16px}}
.az-load-ring{{width:44px;height:44px;border:3px solid rgba(226,180,4,.15);border-top-color:var(--gold);border-radius:50%;animation:spin .8s linear infinite}}
.az-load-txt{{font-size:13px;color:var(--secondary)}}
.az-load-sub{{font-size:11px;color:#444}}
.az-pipe{{display:flex;align-items:stretch;gap:0;margin-bottom:20px;background:var(--card);border:1px solid var(--muted-border);border-radius:12px;overflow:hidden;flex-wrap:wrap}}
.az-stage{{flex:1;min-width:130px;padding:11px 14px;border-right:1px solid var(--muted-border);display:flex;flex-direction:column;gap:3px;position:relative}}
.az-stage:last-child{{border-right:none}}
.az-stage-top{{display:flex;align-items:center;gap:6px}}
.az-stage-dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.az-stage-dot.on{{background:#22c55e;box-shadow:0 0 8px rgba(34,197,94,.5)}}
.az-stage-dot.off{{background:#3a3a3a}}
.az-stage-name{{font-size:10px;font-weight:600;color:var(--white);text-transform:uppercase;letter-spacing:.7px}}
.az-stage-val{{font-size:11px;color:var(--secondary);line-height:1.35}}
.az-stage-val b{{color:var(--gold);font-weight:600}}

/* ── Floating AI Concierge chat (all screens; desktop layout untouched) ── */
#wc-fab{{position:fixed;right:20px;bottom:24px;width:58px;height:58px;border-radius:50%;
  background:linear-gradient(135deg,#E2B404,#8a6c00);color:#050505;font-size:26px;border:none;
  display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:150;
  box-shadow:0 8px 26px rgba(226,180,4,.4),0 0 0 1px rgba(226,180,4,.45)}}
#wc-fab:active{{transform:scale(.94)}}
#wc-overlay{{position:fixed;inset:0;background:rgba(5,5,5,.85);backdrop-filter:blur(10px);
  z-index:250;display:none;align-items:center;justify-content:center}}
#wc-panel{{background:var(--card);width:100%;max-width:520px;height:100%;display:flex;
  flex-direction:column;border:1px solid var(--gold-border)}}
#wc-bar{{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;
  border-bottom:1px solid var(--gold-border);color:var(--gold);font-weight:700;font-size:14px}}
#wc-bar button{{background:none;border:none;color:var(--gold);font-size:22px;cursor:pointer;line-height:1}}
#wc-frame{{flex:1;border:none;width:100%;background:#0a0a0b}}
@media(min-width:560px){{
  #wc-overlay{{padding:22px}}
  #wc-panel{{height:86vh;max-height:780px;border-radius:18px;overflow:hidden}}
}}

/* ── Mobile-first overrides (<=768px). Desktop (>768px) is fully unchanged. ── */
@media (max-width:768px){{
  .layout{{flex-direction:column;height:100vh;height:100dvh}}
  .sidebar{{order:2;position:fixed;bottom:0;left:0;width:100%;min-width:0;height:60px;
    flex-direction:row;border-right:none;border-top:1px solid var(--muted-border);
    background:#010000;z-index:120}}
  .sb-brand,.sb-artwork,.sb-artwork-fallback,.sb-profile,.sb-brand-name{{display:none!important}}
  .sb-nav{{flex-direction:row;justify-content:space-around;align-items:center;width:100%;
    padding:6px 2px;gap:0;overflow-x:auto}}
  .sb-item{{flex-direction:column;gap:3px;padding:6px 6px;font-size:9px;justify-content:center;
    text-align:center;min-width:52px}}
  .sb-item-label{{font-size:9px}}
  .main{{order:1;flex:1;min-height:0;padding-bottom:64px}}
  .kpi-strip{{grid-template-columns:repeat(2,1fr)}}
  .kpi-card{{padding:14px 16px;gap:12px}}
  .filter-bar{{padding:9px 14px}}
  .chip-bar{{padding:10px 14px}}
  .header-row{{gap:10px}}
  .card-grid{{grid-template-columns:1fr}}
  #wc-fab{{bottom:76px}}
}}
</style>
</head>
<body>
<div class="layout">

<!-- SIDEBAR -->
<aside class="sidebar">
  <div class="sb-brand">
    <img src="/images/W-only.png" class="sb-logo-img" alt="W" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
    <div class="sb-logo-fallback" style="display:none">W</div>
    <div class="sb-brand-name">WILD AUTOMATIONS</div>
  </div>

  <nav class="sb-nav">
    <button class="sb-item active" data-cat="all" onclick="setView('all',this)">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>
      <span class="sb-item-label">All</span>
    </button>
    <button class="sb-item" data-cat="Jobs" onclick="setView('Jobs',this)">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 12h.01"/><path d="M16 6V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><path d="M22 13a18.15 18.15 0 0 1-20 0"/><rect width="20" height="14" x="2" y="6" rx="2"/></svg>
      <span class="sb-item-label">Jobs</span>
    </button>
    <button class="sb-item" data-cat="University" onclick="setView('University',this)">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/></svg>
      <span class="sb-item-label">Edu</span>
    </button>
    <button class="sb-item" data-cat="Visa" onclick="setView('Visa',this)">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/><line x1="6" x2="6.01" y1="14" y2="14"/><line x1="10" x2="14" y1="14" y2="14"/></svg>
      <span class="sb-item-label">Visa</span>
    </button>
    <button class="sb-item" data-cat="Automobiles" onclick="setView('Automobiles',this)">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 8-2 2-1.5-3.7A2 2 0 0 0 15.646 5H8.4a2 2 0 0 0-1.903 1.257L5 10 3 8"/><path d="M7 15h0.01"/><path d="M17 15h0.01"/><path d="M5 10H2a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h20a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1h-3"/><path d="M6 19v2"/><path d="M18 19v2"/></svg>
      <span class="sb-item-label">Cars</span>
    </button>
    <button class="sb-item" data-cat="Leads" onclick="setView('Leads',this)">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 6.1H3"/><path d="M21 12.1H3"/><path d="M15.1 18H3"/></svg>
      <span class="sb-item-label">Leads</span>
    </button>

    <div class="sb-divider"></div>
    <button class="sb-item sb-ai" data-cat="AI" onclick="openAnalyzer(this)">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/><path d="M12 8v0"/><circle cx="12" cy="12" r="1"/></svg>
      <span class="sb-item-label">AI Analyzer</span>
    </button>

    <div style="flex:1;min-height:8px"></div>

    <button class="sb-item" onclick="void 0">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg>
      <span class="sb-item-label">Health</span>
    </button>
    <button class="sb-item" onclick="void 0">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
      <span class="sb-item-label">Config</span>
    </button>
  </nav>

  <div class="sb-artwork">
    <img src="/images/w-bottom.png" class="sb-artwork-img" alt="" onerror="this.style.display='none';document.getElementById('sb-art-fallback').style.display='flex'">
    <div id="sb-art-fallback" style="display:none;width:100%;padding:16px;align-items:center;justify-content:center">
      <svg width="130" height="130" viewBox="0 0 130 130" fill="none">
        <circle cx="65" cy="65" r="60" stroke="rgba(226,180,4,.2)" stroke-width="1"/>
        <circle cx="65" cy="65" r="50" stroke="rgba(226,180,4,.15)" stroke-width="1"/>
        <circle cx="65" cy="65" r="40" stroke="rgba(226,180,4,.1)" stroke-width="1"/>
        <text x="65" y="70" text-anchor="middle" font-size="32" font-weight="900" fill="rgba(226,180,4,.6)" font-family="Noto Sans,sans-serif">W</text>
      </svg>
    </div>
  </div>

  <div class="sb-profile">
    <div class="sb-avatar">WA</div>
    <div class="sb-user-info">
      <div class="uname">Wild Admin</div>
      <div class="uemail">admin@wild.com</div>
    </div>
    <div class="sb-profile-chevron">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m18 15-6-6-6 6"/></svg>
    </div>
  </div>
</aside>

<!-- MAIN -->
<div class="main">

  <!-- HEADER -->
  <header class="header">
    <div class="header-row">
      <div class="header-left">
        <span class="h-sdot" id="sdot"></span>
        <div>
          <div class="h-title" id="pg-title">Scraper CRM &mdash; Live Engine Monitor</div>
          <div class="h-sub">Wild Automations &middot; {n} agents registered across 4 categories</div>
        </div>
      </div>
      <div class="header-right">
        <span class="h-cat-pill" id="cat-pill">All Categories</span>
        <button class="h-run-btn" id="run-btn" onclick="runView()">
          <svg viewBox="0 0 24 24"><polygon points="6 3 20 12 6 21 6 3"/></svg>
          Run All
        </button>
        <span class="h-last-run" id="last-run">Ready to run</span>
      </div>
    </div>
  </header>

  <!-- FILTER BAR -->
  <div class="filter-bar">
    <span class="f-label">Country</span>
    <select id="f-country" class="f-inp" onchange="onFilter()">
      <option value="">All</option>
      <option value="UAE">UAE</option>
      <option value="USA">USA</option>
      <option value="UK">UK</option>
      <option value="Canada">Canada</option>
      <option value="Germany">Germany</option>
      <option value="Singapore">Singapore</option>
      <option value="Australia">Australia</option>
    </select>
    <span class="f-sep"></span>
    <span class="f-label">Role / Model</span>
    <input id="f-desig" type="text" placeholder="e.g. Engineer, BMW M4..." class="f-inp" style="width:155px" oninput="onFilter()">
    <span class="f-sep"></span>
    <span class="f-label">Min $</span>
    <input id="f-price" type="number" placeholder="0" class="f-inp" style="width:80px" oninput="onFilter()">
    <span class="f-sep"></span>
    <span class="f-label">Condition</span>
    <select id="f-cond" class="f-inp" onchange="onFilter()">
      <option value="all">All</option>
      <option value="new">New</option>
      <option value="used">Used</option>
    </select>
    <button class="f-clear" onclick="clearF()">&times; Clear</button>
    <span class="f-active" id="finfo"></span>
  </div>

  <!-- KPI STRIP -->
  <div class="kpi-strip">
    <div class="kpi-card">
      <div class="kpi-ring">
        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>
      </div>
      <div class="kpi-content">
        <div class="kpi-num" id="kpi-rows">0</div>
        <div class="kpi-lbl">Rows Extracted</div>
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-ring">
        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><path d="M21.801 10A10 10 0 1 1 17 3.335"/><path d="m9 11 3 3L22 4"/></svg>
      </div>
      <div class="kpi-content">
        <div class="kpi-num" id="kpi-ok">0</div>
        <div class="kpi-lbl">Sources Passed</div>
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-ring">
        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>
      </div>
      <div class="kpi-content">
        <div class="kpi-num" id="kpi-err">0</div>
        <div class="kpi-lbl">Sources Failed</div>
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-ring">
        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/></svg>
      </div>
      <div class="kpi-content">
        <div class="kpi-num" id="kpi-lat">&mdash;</div>
        <div class="kpi-lbl">Avg Latency</div>
      </div>
    </div>
  </div>

  <!-- CHIP BAR -->
  <div class="chip-bar" id="chip-bar">
    <div class="chip-info">
      <svg viewBox="0 0 24 24" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
      All {n} scraper sources.
    </div>
  </div>

  <!-- CARD AREA -->
  <main class="card-area" id="card-area">
    <div class="empty-state" id="empty">
      <div class="empty-icon">&#9889;</div>
      <div class="empty-msg">Click <span>Run All</span> to begin extraction</div>
      <div class="empty-sub">{n} intelligence sources across 4 categories</div>
    </div>
  </main>

</div><!-- /main -->
</div><!-- /layout -->

<!-- MODAL -->
<div id="modal" onclick="if(event.target===this)closeModal()">
  <div class="mbox">
    <div class="mhdr">
      <div class="mhdr-top">
        <div style="flex:1;min-width:0">
          <span class="m-cat-lbl" id="m-cat"></span>
          <div class="m-title" id="m-title"></div>
          <div class="m-desc" id="m-desc"></div>
        </div>
        <button class="mclose" onclick="closeModal()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div id="m-car" class="car-preview" style="display:none">
        <div style="position:relative;z-index:2;text-align:center">
          <div style="font-size:28px;opacity:.06">&#128664;</div>
          <div class="car-label" id="m-carname"></div>
          <div style="font-size:10px;color:#333;margin-top:2px" id="m-carcolor"></div>
        </div>
        <div class="car-price-tag" id="m-price"></div>
        <div class="car-cond-tag" id="m-cbadge"></div>
      </div>
    </div>
    <div class="mbody" id="m-body"></div>
    <div class="mftr">
      <a class="m-open" id="m-url" href="#" target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        Open Source
      </a>
      <button class="m-copy" onclick="copyJSON()">
        <svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        Copy JSON
      </button>
      <span class="m-loc" id="m-loc"></span>
    </div>
  </div>
</div>

<script>
const SCRAPERS={scrapers_js};
const CATEGORIES={categories_js};
const N={n};
const CAT_ICONS={cat_icons_js};
const F={{country:'',designation:'',minPrice:0,condition:'all'}};
const ST={{}};
SCRAPERS.forEach((_,i)=>{{ST[i]={{status:'pending',count:0,elapsed:0,results:[],error:null}};}});
let _view='all',_ok=0,_err=0,_items=0,_sumT=0,_done=0,_running=false,_mdata=null;
const $=id=>document.getElementById(id);
function esc(s){{return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}
function fT(ms){{return ms<1000?ms+'ms':(ms/1000).toFixed(1)+'s';}}
function nowStr(){{return new Date().toLocaleTimeString('en-US',{{hour:'2-digit',minute:'2-digit',second:'2-digit'}});}}

function onFilter(){{
  F.country=$('f-country').value;F.designation=$('f-desig').value.trim();
  F.minPrice=parseFloat($('f-price').value)||0;F.condition=$('f-cond').value;
  const on=F.country||F.designation||F.minPrice||F.condition!=='all';
  $('finfo').textContent=on?'Filters active':'';
  if(_done>0||_running)renderAll();
}}
function clearF(){{
  $('f-country').value='';$('f-desig').value='';$('f-price').value='';$('f-cond').value='all';
  F.country='';F.designation='';F.minPrice=0;F.condition='all';$('finfo').textContent='';
  if(_done>0||_running)renderAll();
}}
function applyF(results,cat){{
  if(!F.country&&!F.designation&&!F.minPrice&&F.condition==='all')return results;
  return results.filter(r=>{{
    const m=r.metadata||{{}};
    const loc=(r.location||m.location||m.country||'').toLowerCase();
    const txt=((r.title||'')+(r.description||'')).toLowerCase();
    const make=(m.make||'').toLowerCase(),mdl=(m.model||'').toLowerCase();
    if(F.country){{const q=F.country.toLowerCase();if(!loc.includes(q)&&!txt.includes(q)&&!make.includes(q))return false;}}
    if(F.designation){{const q=F.designation.toLowerCase();if(!txt.includes(q)&&!make.includes(q)&&!mdl.includes(q))return false;}}
    if(F.minPrice>0){{const p=parseFloat(String(r.price||'0').replace(/[^0-9.]/g,''));if(p>0&&p<F.minPrice)return false;}}
    if(F.condition!=='all'&&cat==='Automobiles'){{const c=(m.condition||'').toLowerCase();if(c&&c!==F.condition)return false;}}
    return true;
  }});
}}

function locBadge(r,cat){{
  const m=r.metadata||{{}};
  const loc=r.location||m.location||'';
  if(!loc)return'';
  return`<span class="loc-badge"><svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>${{esc(loc.substring(0,30))}}</span>`;
}}
function extraBadges(r,cat){{
  const m=r.metadata||{{}};const t=[];
  if(cat==='Jobs'){{
    if(r.price&&String(r.price)!=='0')t.push(`<span class="badge-sal">${{esc(String(r.price).substring(0,22))}}</span>`);
  }}else if(cat==='University'){{
    if(m.gpa_minimum)t.push(`<span class="badge-gold">GPA &ge;${{m.gpa_minimum}}</span>`);
    if(m.ielts_minimum)t.push(`<span class="badge-gold">IELTS ${{m.ielts_minimum}}</span>`);
    if(m.application_deadline)t.push(`<span class="badge-gold">Due ${{esc(m.application_deadline)}}</span>`);
  }}else if(cat==='Visa'){{
    if(m.processing_time)t.push(`<span class="badge-gold">${{esc(m.processing_time)}}</span>`);
  }}else if(cat==='Automobiles'){{
    const cond=(m.condition||'').toLowerCase();
    if(cond)t.push(`<span class="badge-${{cond==='new'?'new':'used'}}">${{cond.toUpperCase()}}</span>`);
    if(m.price_usd)t.push(`<span class="badge-sal">$${{parseInt(m.price_usd).toLocaleString()}}</span>`);
  }}
  return t.join('');
}}
function buildRow(r,cat){{
  const url=r.source_url||'';
  const data=JSON.stringify(r).replace(/'/g,"&#39;");
  return`<div class="res-row" onclick='openModal(${{data}},"${{cat}}")'>
    <div class="res-title">${{esc((r.title||'').substring(0,100))}}</div>
    <div class="res-desc">${{esc((r.description||'').substring(0,130))}}</div>
    <div class="res-meta">
      ${{locBadge(r,cat)}}
      ${{extraBadges(r,cat)}}
      ${{url?`<a href="${{esc(url)}}" target="_blank" rel="noopener" class="open-link" onclick="event.stopPropagation()"><svg viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>Open</a>`:''}}
    </div>
  </div>`;
}}
function cardDot(s){{
  return`<span class="card-sdot ${{s==='running'?'ok pulse-dot':s}}"></span>`;
}}
function buildCard(i){{
  const s=SCRAPERS[i],st=ST[i],cat=s.category||'';
  const filt=applyF(st.results||[],cat);
  const rows=filt.slice(0,10).map(r=>buildRow(r,cat)).join('');
  const more=filt.length-10;
  return`<div class="card" id="card-${{i}}">
    <div class="card-hdr">
      <div class="card-hdr-row1">
        <span class="card-emoji">${{s.emoji||'&#9889;'}}</span>
        <span class="card-name">${{esc(s.name)}}</span>
        ${{cardDot(st.status)}}
      </div>
      <div class="card-hdr-row2">
        <span class="mode-pill">${{esc(s.mode||'API')}}</span>
        <span class="bot-name">${{esc(s.bot||'')}}</span>
      </div>
    </div>
    <div class="card-body">
      ${{rows||'<div class="no-results">No results yet</div>'}}
      ${{more>0?`<div style="padding:6px 16px;font-size:10px;color:#333;text-align:center">+${{more}} more</div>`:''}}
    </div>
    <div class="card-ftr">
      ${{st.count>0?`<span class="ftr-items"><svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>${{st.count}} items</span>`:''}}
      ${{st.elapsed?`<span class="ftr-time"><svg viewBox="0 0 24 24" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>${{fT(st.elapsed)}}</span>`:''}}
      ${{st.error?`<span class="ftr-err">${{esc((st.error||'').substring(0,28))}}</span>`:''}}
      <button class="rerun-btn" onclick="runOne(${{i}})">
        <svg viewBox="0 0 24 24" stroke-linecap="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
        Re-run
      </button>
    </div>
  </div>`;
}}
function updateChips(){{
  const vis=SCRAPERS.filter(s=>_view==='all'||s.category===_view);
  const lbl=_view==='all'?`All ${{N}} scraper sources.`:`${{vis.length}} sources in ${{_view}}.`;
  const infoSvg=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="12" height="12"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`;
  let html=`<div class="chip-info">${{infoSvg}} ${{lbl}}</div>`;
  const checkSvg=`<svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg>`;
  const xSvg=`<svg viewBox="0 0 24 24"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`;
  const dotSvg=`<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4" fill="currentColor" stroke="none"/></svg>`;
  vis.forEach(s=>{{
    const i=SCRAPERS.indexOf(s),st=ST[i];
    const cls=st.status==='ok'?'ok':st.status==='error'?'err':st.status==='running'?'running':'';
    const ico=st.status==='ok'?checkSvg:st.status==='error'?xSvg:st.status==='running'?dotSvg:'';
    html+=`<span class="chip ${{cls}}">${{ico}}${{esc(s.name.split('·')[0].trim().substring(0,18))}}</span>`;
  }});
  $('chip-bar').innerHTML=html;
}}
function renderAll(){{
  const area=$('card-area');
  const empty=$('empty');if(empty)empty.style.display='none';
  const scrapers=SCRAPERS.filter(s=>_view==='all'||s.category===_view);
  if(!scrapers.length){{area.innerHTML='<p style="text-align:center;color:#333;padding:60px;font-size:13px">No scrapers.</p>';return;}}
  const bycat={{}};
  scrapers.forEach(s=>{{if(!bycat[s.category])bycat[s.category]=[];bycat[s.category].push(s);}});
  let html='';
  for(const[cat,sl]of Object.entries(bycat)){{
    const ico=CAT_ICONS[cat]||'';
    const playSvg=`<svg width="9" height="9" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 3 20 12 6 21 6 3"/></svg>`;
    html+=`<div class="cat-section">
      <div class="cat-hdr">
        <div class="cat-hdr-left">
          <span class="cat-emoji">${{ico}}</span>
          <span class="cat-name">${{cat}}</span>
          <span class="cat-count">${{sl.length}} sources</span>
        </div>
        <button class="run-cat-btn" onclick="runCat('${{cat}}')">
          ${{playSvg}} Run ${{cat}}
        </button>
      </div>
      <div class="card-grid">
        ${{sl.map(s=>buildCard(SCRAPERS.indexOf(s))).join('')}}
      </div>
    </div>`;
  }}
  area.innerHTML=html;
}}
function patchCard(i){{
  const el=$('card-'+i);
  if(el){{const d=document.createElement('div');d.innerHTML=buildCard(i);el.replaceWith(d.firstElementChild);}}
}}
function updateKPIs(){{
  $('kpi-rows').textContent=_items;
  $('kpi-ok').textContent=_ok;
  $('kpi-err').textContent=_err;
  $('kpi-lat').textContent=_done?fT(Math.round(_sumT/_done)):'&mdash;';
}}
function setSdot(s){{
  const el=$('sdot');
  el.className='h-sdot'+(s&&s!=='gray'?' '+s:'');
}}
function setView(cat,el){{
  _view=cat;_azMode=false;
  document.querySelectorAll('.sb-item[data-cat]').forEach(b=>b.classList.remove('active'));
  const t=el||document.querySelector(`.sb-item[data-cat="${{cat}}"]`);
  if(t)t.classList.add('active');
  const rl=cat==='all'?'Run All':'Run '+cat;
  $('cat-pill').textContent=cat==='all'?'All Categories':cat;
  $('run-btn').style.display='';
  $('run-btn').innerHTML=`<svg viewBox="0 0 24 24" style="width:12px;height:12px;fill:#050505;stroke:none"><polygon points="6 3 20 12 6 21 6 3"/></svg> ${{rl}}`;
  $('pg-title').textContent=cat==='all'?'Scraper CRM — Live Engine Monitor':cat+' Scrapers';
  updateChips();
  if(_done>0||_running){{renderAll();}}
  else{{$('card-area').innerHTML='<div class="empty-state" id="empty"><div class="empty-icon">&#9889;</div><div class="empty-msg">Click <span>Run All</span> to begin extraction</div><div class="empty-sub">'+N+' intelligence sources across 4 categories</div></div>';}}
}}

// ── AI ANALYZER ─────────────────────────────────────────────
let _azMode=false,_azData=null,_azFilter='all';
function openAnalyzer(el){{
  _azMode=true;
  document.querySelectorAll('.sb-item[data-cat]').forEach(b=>b.classList.remove('active'));
  if(el)el.classList.add('active');
  $('pg-title').textContent='AI Analyzer — Universal Value Ranking';
  $('cat-pill').textContent='Value Arbitrage';
  $('run-btn').style.display='none';
  loadAnalyzer(false);
}}
async function loadAnalyzer(refresh){{
  $('card-area').innerHTML='<div class="az-loading"><div class="az-load-ring"></div><div class="az-load-txt">'+(refresh?'Re-scoring all sources…':'Loading value analysis…')+'</div><div class="az-load-sub">Computing appeal scores, deal Z-scores & leniency index</div></div>';
  try{{
    const r=await fetch('/api/analyze'+(refresh?'?refresh=true':''));
    _azData=await r.json();
    renderAnalyzer();
  }}catch(e){{
    $('card-area').innerHTML='<div class="empty-state"><div class="empty-icon">&#9889;</div><div class="empty-msg">Analysis failed</div><div class="empty-sub">'+esc(e.message)+'</div></div>';
  }}
}}
function azFilterSet(f,el){{
  _azFilter=f;
  document.querySelectorAll('.az-seg button').forEach(b=>b.classList.remove('on'));
  if(el)el.classList.add('on');
  renderAnalyzer();
}}
function renderAnalyzer(){{
  if(!_azData){{return;}}
  const s=_azData.summary||{{}};
  let recs=_azData.records||[];
  if(_azFilter!=='all')recs=recs.filter(x=>x.ai_scores.category===_azFilter);
  const cacheTag=_azData.cached?'cached ':'fresh ';
  const kpis=`<div class="az-kpis">
    <div class="az-kpi gem"><div class="az-kpi-num">${{s.hidden_gems||0}}</div><div class="az-kpi-lbl">Hidden Gems</div></div>
    <div class="az-kpi"><div class="az-kpi-num">${{s.good_deals||0}}</div><div class="az-kpi-lbl">Good Deals</div></div>
    <div class="az-kpi"><div class="az-kpi-num">${{s.average||0}}</div><div class="az-kpi-lbl">Average</div></div>
    <div class="az-kpi"><div class="az-kpi-num">${{s.overpriced||0}}</div><div class="az-kpi-lbl">Overpriced</div></div>
    <div class="az-kpi"><div class="az-kpi-num">${{Math.round((s.avg_appeal||0)*100)}}</div><div class="az-kpi-lbl">Avg Appeal</div></div>
  </div>`;
  const pipe=azPipeline(_azData.stages||{{}});
  const seg=`<div class="az-toolbar">
    <div class="az-seg">
      <button class="${{_azFilter==='all'?'on':''}}" onclick="azFilterSet('all',this)">All ${{(_azData.records||[]).length}}</button>
      <button class="${{_azFilter==='Jobs'?'on':''}}" onclick="azFilterSet('Jobs',this)">Jobs</button>
      <button class="${{_azFilter==='University'?'on':''}}" onclick="azFilterSet('University',this)">University</button>
      <button class="${{_azFilter==='Automobiles'?'on':''}}" onclick="azFilterSet('Automobiles',this)">Cars</button>
      <button class="${{_azFilter==='Visa'?'on':''}}" onclick="azFilterSet('Visa',this)">Visa</button>
      <button class="${{_azFilter==='Leads'?'on':''}}" onclick="azFilterSet('Leads',this)">Leads</button>
    </div>
    <span class="az-cache">${{cacheTag}}· ${{recs.length}} shown</span>
    <button class="az-refresh" onclick="loadAnalyzer(true)"><svg viewBox="0 0 24 24" stroke-linecap="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Re-Analyze</button>
  </div>`;
  const cards=recs.map((rec,i)=>azCard(rec,i+1)).join('');
  $('card-area').innerHTML=kpis+pipe+seg+`<div class="az-grid">${{cards||'<p style="color:#333;padding:40px;text-align:center">No records in this category.</p>'}}</div>`;
}}
function azStage(on,name,val){{
  return`<div class="az-stage"><div class="az-stage-top"><span class="az-stage-dot ${{on?'on':'off'}}"></span><span class="az-stage-name">${{name}}</span></div><div class="az-stage-val">${{val}}</div></div>`;
}}
function azPipeline(st){{
  const d=st.dedupe||{{}},p=st.persist||{{}},sc=st.score||{{}},ai=st.ai_enrich||{{}},md=st.match_deliver||{{}};
  return`<div class="az-pipe">
    ${{azStage(d.active,'Dedupe',d.active?`<b>${{d.removed||0}}</b> dupes removed · ${{d.out||0}} unique`:'skipped')}}
    ${{azStage(p.active,'Persist',p.active?`${{p.backend||'store'}} · <b>${{p.total_stored||0}}</b> stored · ${{p.history_records||0}} history`:'off')}}
    ${{azStage(sc.active,'Score',sc.active?`<b>${{sc.scored||0}}</b> scored · baseline ${{sc.baseline_population||0}}`:'off')}}
    ${{azStage(ai.active,'AI Enrich',ai.active?`<b>${{ai.provider||'LLM'}}</b> · ${{ai.enriched||0}} enriched`:(ai.reason||'heuristic'))}}
    ${{azStage(md.active,'Match',md.active?`<b>${{md.matched||0}}</b> matched · ${{md.delivered||0}} delivered`:'off')}}
  </div>`;
}}
function azRatingClass(r){{
  return r==='Hidden Gem'?'gem':r==='Good Deal'?'good':r==='Overpriced'?'over':'avg';
}}
function azCard(rec,rank){{
  const o=rec.original_data||{{}},a=rec.ai_scores||{{}},d=a.deal_breakdown||{{}};
  const rc=azRatingClass(a.value_rating);
  const pct=Math.round((a.universal_appeal_score||0)*100);
  const emoji=o.emoji||CAT_ICONS[a.category]||'&#9889;';
  const flags=(d.flags||[]).map(f=>`<span class="az-flag">${{esc(f)}}</span>`).join('');
  // category-specific metric tiles
  let metrics='';
  if(a.category==='Jobs'){{
    metrics=azMetric('Salary/yr',d.annual_salary_usd?'$'+Number(d.annual_salary_usd).toLocaleString():'—')+
            azMetric('Visa Prob',(d.visa_probability!=null?d.visa_probability+'%':'—'));
  }}else if(a.category==='University'){{
    metrics=azMetric('ROI',d.roi_score!=null?d.roi_score+'x':'—')+
            azMetric('Leniency',d.leniency_index!=null?Math.round(d.leniency_index*100)+'%':'—');
  }}else if(a.category==='Automobiles'){{
    metrics=azMetric('Deal Z-Score',d.deal_z_score!=null?d.deal_z_score:'—')+
            azMetric('vs Market',d.pct_below_market!=null?d.pct_below_market+'%':'—');
  }}
  const link=o.source_url?`onclick="window.open('${{esc(o.source_url)}}','_blank')" style="cursor:pointer"`:'';
  return`<div class="az-card ${{rc==='gem'?'gem':''}}" ${{link}}>
    <div class="az-rank">${{rank}}</div>
    <div class="az-c-hdr">
      <span class="az-c-emoji">${{emoji}}</span>
      <div class="az-c-title">
        <div class="az-c-name">${{esc((o.title||'Untitled').substring(0,90))}}</div>
        <div class="az-c-src">${{esc(a.source||a.category)}}</div>
      </div>
      <span class="az-rating ${{rc}}">${{esc(a.value_rating||'')}}</span>
    </div>
    <div class="az-score">
      <div class="az-score-row"><span class="az-score-lbl">Universal Appeal</span><span class="az-score-val">${{pct}}%</span></div>
      <div class="az-bar"><div class="az-bar-fill" style="width:${{pct}}%"></div></div>
    </div>
    ${{flags?`<div class="az-flags">${{flags}}</div>`:''}}
    ${{metrics?`<div class="az-metrics">${{metrics}}</div>`:''}}
    <div class="az-why"><b>Why:</b> ${{esc(d.why||'—')}}${{d.llm_summary?`<div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,.06);color:var(--gold)"><b style="color:var(--gold)">✦ AI:</b> ${{esc(d.llm_summary)}}</div>`:''}}</div>
  </div>`;
}}
function azMetric(k,v){{
  return`<div class="az-metric"><div class="az-metric-k">${{esc(k)}}</div><div class="az-metric-v">${{esc(String(v))}}</div></div>`;
}}
async function runView(){{
  if(_running)return;
  _running=true;_ok=0;_err=0;_items=0;_sumT=0;_done=0;
  SCRAPERS.forEach((_,i)=>{{ST[i]={{status:'pending',count:0,elapsed:0,results:[],error:null}};}});
  setSdot('gold');$('last-run').textContent='Running…';
  const rl=_view==='all'?'Run All':'Run '+_view;
  $('run-btn').innerHTML=`<span class="spin">↻</span> ${{rl}}…`;
  renderAll();updateChips();
  const url=_view==='all'?'/api/stream':'/api/stream/category/'+_view;
  const es=new EventSource(url);
  es.onmessage=e=>{{
    try{{
      const d=JSON.parse(e.data);
      if(d.type==='result'){{ST[d.index].results.push(d.result);ST[d.index].count++;_items++;patchCard(d.index);updateKPIs();}}
      else if(d.type==='done'){{
        const i=d.index,src=d.source;
        Object.assign(ST[i],{{status:src.status,elapsed:src.elapsed_ms||0,count:src.count||0,error:src.error||null}});
        if(src.status==='ok')_ok++;else _err++;_sumT+=src.elapsed_ms||0;_done++;
        patchCard(i);updateKPIs();updateChips();
      }}else if(d.type==='stream_end'){{
        es.close();_running=false;setSdot('green');
        $('last-run').textContent='Last run '+nowStr();
        $('run-btn').innerHTML=`<svg viewBox="0 0 24 24" style="width:12px;height:12px;fill:#050505;stroke:none"><polygon points="6 3 20 12 6 21 6 3"/></svg> ${{rl}}`;
      }}
    }}catch(ex){{console.warn('SSE',ex);}}
  }};
  es.onerror=()=>{{
    es.close();_running=false;setSdot('red');
    $('run-btn').innerHTML=`<svg viewBox="0 0 24 24" style="width:12px;height:12px;fill:#050505;stroke:none"><polygon points="6 3 20 12 6 21 6 3"/></svg> ${{_view==='all'?'Run All':'Run '+_view}}`;
  }};
}}
async function runCat(cat){{
  SCRAPERS.forEach((s,i)=>{{if(s.category===cat){{ST[i]={{status:'running',count:0,elapsed:0,results:[],error:null}};patchCard(i);}}}});
  const es=new EventSource('/api/stream/category/'+cat);
  es.onmessage=e=>{{
    try{{
      const d=JSON.parse(e.data);
      if(d.type==='result'){{ST[d.index].results.push(d.result);ST[d.index].count++;_items++;patchCard(d.index);updateKPIs();}}
      else if(d.type==='done'){{
        const i=d.index,src=d.source;
        Object.assign(ST[i],{{status:src.status,elapsed:src.elapsed_ms||0,count:src.count||0,error:src.error||null}});
        if(src.status==='ok')_ok++;else _err++;_sumT+=src.elapsed_ms||0;_done++;
        patchCard(i);updateKPIs();updateChips();
      }}else if(d.type==='stream_end'){{es.close();}}
    }}catch(_){{}}
  }};
  es.onerror=()=>es.close();
}}
async function runOne(i){{
  if(ST[i]&&ST[i].status==='running')return;
  ST[i]={{status:'running',count:0,elapsed:0,results:[],error:null}};patchCard(i);
  try{{
    const r=await fetch('/api/run/'+i),d=await r.json();
    ST[i]=d;if(d.status==='ok'){{_ok++;_items+=d.count;}}else _err++;
    _sumT+=(d.elapsed||0);_done++;patchCard(i);updateKPIs();updateChips();
  }}catch(e){{ST[i]={{status:'error',count:0,elapsed:0,results:[],error:e.message}};_err++;_done++;patchCard(i);updateKPIs();}}
}}
function openModal(r,cat){{
  _mdata=r;const m=r.metadata||{{}};
  $('m-cat').textContent=cat||m.type||'';
  $('m-title').textContent=r.title||'Detail';
  $('m-desc').textContent=(r.description||'').substring(0,280);
  $('m-url').href=r.source_url||'#';
  $('m-loc').textContent=r.location||m.location||'';
  const isCar=cat==='Automobiles'||m.type==='vehicle';
  const carEl=$('m-car');
  if(isCar){{
    carEl.style.display='flex';
    $('m-carname').textContent=(m.make||'')+' '+(m.model||'')+(m.year?' ('+m.year+')':'');
    $('m-carcolor').textContent=m.color||'';
    $('m-price').textContent=m.price_usd?'$'+parseInt(m.price_usd).toLocaleString():'';
    const c=(m.condition||'').toLowerCase();
    $('m-cbadge').innerHTML=c?`<span class="badge-${{c==='new'?'new':'used'}}">${{c.toUpperCase()}}</span>`:'';
  }}else{{carEl.style.display='none';}}
  const skip=new Set(['scraped_at','source','source_key','is_relevant','type']);
  let bhtml='';
  if(r.price&&!isCar)bhtml+=`<div class="mrow"><div class="mkey">Price/Salary</div><div class="mval" style="color:#4ade80;font-weight:600">${{esc(String(r.price))}}</div></div>`;
  Object.entries(m).filter(([k,v])=>!skip.has(k)&&v!=null).forEach(([k,v])=>{{
    const lbl=k.replace(/_/g,' ').replace(/\\b\\w/g,c=>c.toUpperCase());
    let val=typeof v==='number'&&k.includes('rate')?Math.round(v*100)+'%':typeof v==='number'&&(k.includes('tuition')||k.includes('price_usd'))?'$'+parseInt(v).toLocaleString():String(v).substring(0,250);
    bhtml+=`<div class="mrow"><div class="mkey">${{esc(lbl)}}</div><div class="mval">${{esc(val)}}</div></div>`;
  }});
  $('m-body').innerHTML=bhtml||'<div class="mrow"><div class="mkey">Info</div><div class="mval">No metadata.</div></div>';
  $('modal').classList.add('show');
}}
function closeModal(){{$('modal').classList.remove('show');_mdata=null;}}
function copyJSON(){{if(_mdata)navigator.clipboard.writeText(JSON.stringify(_mdata,null,2)).catch(()=>{{}});}}
document.addEventListener('keydown',e=>{{if(e.key==='Escape')closeModal();}});
setView('all',document.querySelector('.sb-item[data-cat="all"]'));
function wcOpen(){{var o=$('wc-overlay');var f=$('wc-frame');if(!f.getAttribute('src'))f.setAttribute('src','/concierge');o.style.display='flex';}}
function wcClose(){{$('wc-overlay').style.display='none';}}
</script>
<button id="wc-fab" onclick="wcOpen()" title="AI Concierge">💬</button>
<div id="wc-overlay" onclick="if(event.target===this)wcClose()">
  <div id="wc-panel">
    <div id="wc-bar"><span>🤖 AI Concierge</span><button onclick="wcClose()">✕</button></div>
    <iframe id="wc-frame" title="AI Concierge"></iframe>
  </div>
</div>
</body>
</html>"""


if __name__ == "__main__":
    # Railway/hosts inject the port via $PORT; fall back to 8001 locally.
    port = int(os.getenv("PORT", "8001"))
    print(f"\n  Wild Automations — Premium Scraper CRM v2")
    print(f"  {len(SCRAPERS)} scrapers · {len(CATEGORIES)} categories")
    print(f"  http://0.0.0.0:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

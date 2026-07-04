"""
AI Concierge — persona-driven intake → targeted run → match.

Four user personas each declare the info the assistant must collect; from those
answers the Concierge patches the relevant scrapers' params, and (after the run)
ranks results against the user's stated requirement. AI (GROQ via llm_client) is
used for CV analysis, conversational replies, and a "tell me about my data" Q&A —
but the run + ranking are DETERMINISTIC so results are reliable even if the LLM
is unavailable.

The endpoints (in test_ui.py) own the actual scraper execution (they hold the
SCRAPERS registry + _run_one); this module provides the brains:

    personas()                      -> persona list + intake questions
    category_for(persona)           -> which scraper category to run
    patch_config(cfg, persona, ans) -> override a scraper config's query params
    rank(records, persona, answers) -> relevance-scored, sorted records
    analyze_cv(text)                -> {role, skills[], location, seniority}  (async)
    chat(message, history)          -> assistant reply (async)
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Persona intake definitions ────────────────────────────────────────────────
PERSONAS: List[Dict[str, Any]] = [
    {
        "id": "student", "label": "Student / Admission", "icon": "🎓",
        "category": "University",
        "intro": "Tell me what you want to study and where — I'll find matching programs.",
        "questions": [
            {"key": "country", "label": "Which country?", "type": "text", "example": "United Kingdom"},
            {"key": "field", "label": "Field of study", "type": "text", "example": "Computer Science"},
            {"key": "level", "label": "Level", "type": "select",
             "options": ["Undergraduate", "Postgraduate", "PhD"]},
            {"key": "budget", "label": "Yearly budget (USD, optional)", "type": "text", "required": False},
        ],
    },
    {
        "id": "job_seeker", "label": "Job Seeker", "icon": "💼",
        "category": "Jobs",
        "intro": "Upload your CV or tell me your role and location — I'll find jobs (and visa-sponsored ones).",
        "questions": [
            {"key": "role", "label": "Role / title", "type": "text", "example": "Software Engineer"},
            {"key": "location", "label": "Preferred location", "type": "text", "example": "Dubai"},
            {"key": "cv_text", "label": "Paste your CV (optional — I'll auto-fill)",
             "type": "textarea", "required": False},
        ],
    },
    {
        "id": "travel_agent", "label": "Travel Agent", "icon": "✈️",
        "category": "Visa",
        "intro": "Tell me the traveller's nationality and destination — I'll pull visa routes & ease.",
        "questions": [
            {"key": "nationality", "label": "Nationality / passport", "type": "text", "example": "India"},
            {"key": "destination", "label": "Destination country", "type": "text", "example": "Canada"},
        ],
    },
    {
        "id": "car_dealer", "label": "Car Dealer", "icon": "🚗",
        "category": "Automobiles",
        "intro": "Tell me the make/model/year you're sourcing — I'll find matching listings.",
        "questions": [
            {"key": "make", "label": "Make", "type": "text", "example": "Toyota"},
            {"key": "model", "label": "Model", "type": "text", "example": "Camry"},
            {"key": "year", "label": "Year (optional)", "type": "text", "required": False},
        ],
    },
]

_BY_ID = {p["id"]: p for p in PERSONAS}


def personas() -> List[Dict[str, Any]]:
    return PERSONAS


def category_for(persona: str) -> Optional[str]:
    p = _BY_ID.get(persona)
    return p["category"] if p else None


# ── Config patching: set the user's requirement into a scraper config ─────────
def patch_config(cfg: Dict[str, Any], persona: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy of a scraper config with the persona's query params
    overridden by the user's answers. Only patches keys that already exist, so
    a config is never corrupted."""
    c = copy.deepcopy(cfg)
    a = {k: (v or "").strip() if isinstance(v, str) else v for k, v in (answers or {}).items()}

    def _set(d: Dict[str, Any], key: str, val: Any):
        if val and key in d:
            d[key] = val

    if persona == "job_seeker":
        role, loc = a.get("role"), a.get("location")
        jp = c.get("config", c).get("jobspy_params") if isinstance(c.get("config"), dict) else c.get("jobspy_params")
        for params_key in ("jobspy_params",):
            p = _nested(c, params_key)
            if p:
                _set(p, "search_term", role)
                _set(p, "location", loc)
        gp = _nested(c, "gulftalent_params")
        if gp:
            _set(gp, "category", (role or "").lower().replace(" ", "-"))
        up = _nested(c, "uk_jobs_params")
        if up:
            _set(up, "keywords", role)

    elif persona == "student":
        for params_key in ("university_params", "admissions_params", "qs_params"):
            p = _nested(c, params_key)
            if p:
                _set(p, "country", a.get("country"))
                _set(p, "keyword", a.get("field"))

    elif persona == "travel_agent":
        for params_key in ("visa_params", "passport_params", "eu_visa_params"):
            p = _nested(c, params_key)
            if p:
                _set(p, "nationality", a.get("nationality"))
                _set(p, "destination", a.get("destination"))
                _set(p, "country", a.get("destination"))

    elif persona == "car_dealer":
        for params_key in ("car_params", "car_auction_params", "vehicle_params"):
            p = _nested(c, params_key)
            if p:
                _set(p, "make", a.get("make"))
                _set(p, "model", a.get("model"))
                _set(p, "year", a.get("year"))
    return c


def _nested(cfg: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    """Find a params dict `key` at cfg[key] or cfg['config'][key]."""
    if isinstance(cfg.get(key), dict):
        return cfg[key]
    inner = cfg.get("config")
    if isinstance(inner, dict) and isinstance(inner.get(key), dict):
        return inner[key]
    return None


# ── Deterministic relevance ranking ───────────────────────────────────────────
_STOP = {"the", "and", "for", "with", "a", "an", "of", "in", "to", "my", "i"}


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if t not in _STOP and len(t) > 1]


def rank(records: List[Dict[str, Any]], persona: str, answers: Dict[str, Any]
         ) -> List[Dict[str, Any]]:
    """Score each record by keyword overlap with the user's requirement + light
    persona bonuses (visa-sponsorship for job seekers, etc.). Returns sorted."""
    want = " ".join(str(v) for v in (answers or {}).values() if v)
    want_tokens = set(_tokens(want))
    scored = []
    for r in records:
        md = r.get("metadata") or {}
        hay = f"{r.get('title','')} {r.get('description','')} {r.get('location','')} " \
              f"{md.get('make','')} {md.get('model','')} {md.get('country','')}"
        hay_tokens = set(_tokens(hay))
        overlap = len(want_tokens & hay_tokens)
        score = overlap / (len(want_tokens) or 1)
        # persona bonuses
        if persona == "job_seeker" and any(k in hay.lower() for k in ("visa", "sponsor", "relocation")):
            score += 0.25
        if persona == "student" and md.get("academic_flags", {}).get("is_late_intake"):
            score += 0.15
        r = dict(r)
        r["_match_score"] = round(min(1.0, score), 3)
        scored.append(r)
    scored.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
    return scored


# ── AI: CV analysis, chat, your-data (GROQ via llm_client; safe fallback) ──────
async def analyze_cv(cv_text: str) -> Dict[str, Any]:
    """Extract {role, skills, location, seniority} from CV text. LLM-first with a
    deterministic keyword fallback so it always returns something usable."""
    text = (cv_text or "").strip()
    if not text:
        return {"role": "", "skills": [], "location": "", "seniority": ""}
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if llm:
            prompt = ("Extract JSON from this CV with keys role (best-fit job title), "
                      "skills (array of <=8), location (city/country if present), "
                      "seniority (junior/mid/senior). CV:\n" + text[:4000])
            out = await llm.complete(prompt, system="You output only compact JSON.")
            import json
            m = re.search(r"\{.*\}", out, re.S)
            if m:
                data = json.loads(m.group(0))
                data.setdefault("skills", [])
                return data
    except Exception as exc:
        logger.info("concierge.analyze_cv LLM fallback: %s", exc)
    # deterministic fallback (title phrases first — most specific wins)
    low = text.lower()
    known = ["python", "javascript", "react", "node", "java", "sql", "aws", "docker",
             "agile", "scrum", "jira", "pmp", "prince2", "stakeholder", "delivery",
             "digital transformation", "saas", "fintech", "kanban", "waterfall",
             "marketing", "sales", "accounting", "design", "seo", "flutter", "php",
             "budget", "roadmap", "sdlc", "devops"]
    skills = [s for s in known if s in low][:8]
    _TITLES = ["senior project manager", "program manager", "programme manager",
               "digital transformation manager", "technical project manager",
               "delivery manager", "product delivery manager", "pmo manager",
               "project manager", "product manager", "scrum master", "software engineer",
               "data scientist", "data analyst", "devops engineer", "solutions architect",
               "business analyst", "care assistant", "registered nurse", "accountant"]
    role = next((t.title() for t in _TITLES if t in low), "")
    if not role:
        m = re.search(r"(engineer|developer|manager|designer|analyst|consultant|"
                      r"specialist|nurse|teacher|architect)", low)
        role = m.group(1).title() if m else ""
    return {"role": role, "skills": skills, "location": "", "seniority": ""}


_INTENT_KW = {
    "job_seeker": ["job", "jobs", "work", "hiring", "vacancy", "vacancies", "employment",
                   "career", "careers", "naukri", "position", "roles", "recruit"],
    "student": ["study", "studies", "admission", "admissions", "university", "universities",
                "college", "student", "course", "degree", "scholarship", "masters", "phd", "bachelor"],
    "travel_agent": ["visa", "visas", "immigration", "passport", "sponsorship", "relocate", "migrate", "travel"],
    "car_dealer": ["car ", "cars", "auto", "autos", "vehicle", "vehicles", "dealer", "dealership"],
}
_COUNTRIES = ["united states", "usa", "america", "united kingdom", "uk", "england", "canada",
              "germany", "australia", "uae", "dubai", "abu dhabi", "sharjah", "ireland", "france",
              "netherlands", "singapore", "qatar", "saudi", "pakistan", "india"]
_KNOWN_ROLES = ["senior project manager", "project manager", "program manager",
                "programme manager", "delivery manager", "product manager", "scrum master",
                "software engineer", "web developer", "developer", "data scientist",
                "data analyst", "devops engineer", "solutions architect", "business analyst",
                "graphic designer", "ui designer", "ux designer", "designer",
                "customer support", "customer service", "virtual assistant", "recruiter",
                "digital marketer", "content writer", "copywriter", "seo specialist",
                "nurse", "accountant", "bookkeeper", "driver", "chef", "care assistant", "care",
                "teacher", "marketing", "sales", "welder", "electrician", "engineer", "manager"]


_JOBTYPE = {"remote": ["remote", "work from home", "wfh", "anywhere", "worldwide"],
            "freelance": ["freelance", "freelancing", "contract", "gig", "self employed"],
            "part-time": ["part time", "part-time", "parttime"],
            "full-time": ["full time", "full-time", "permanent"],
            "internship": ["internship", "intern ", "trainee"]}


def _slots(history: Optional[List[Dict[str, str]]], message: str) -> Dict[str, str]:
    """Read the WHOLE conversation and fill intent/location/role/job_type — so a
    filled slot is never asked again (this is what kills the old loop)."""
    text = " ".join([h.get("content", "") for h in (history or [])] + [message]).lower()
    intent = next((k for k, kws in _INTENT_KW.items()
                   if any(w in text for w in kws)), "")
    job_type = next((k for k, kws in _JOBTYPE.items() if any(w in text for w in kws)), "")
    location = next((c for c in _COUNTRIES if re.search(r"\b" + re.escape(c) + r"\b", text)), "")
    role = ""
    stop = {"i", "want", "a", "an", "the", "looking", "for", "need", "find", "get",
            "some", "me", "my", "please", "searching", "search", "would", "like", "to",
            "any", "good", "best", "new", "remote", "worldwide", "anywhere", "freelance",
            "freelancing", "part", "time", "full", "contract", "work", "internship", "intern", "gig"}
    # known multi-word titles first (most specific), else the "<role> job" pattern
    role = next((r for r in _KNOWN_ROLES if r in text), "")
    if not role:
        m = re.search(r"([a-z][a-z ]{2,40}?)\s+(?:job|jobs|role|roles|position)\b", text)
        if m:
            role = " ".join(w for w in m.group(1).split() if w not in stop).strip()
    # any job signal (role, job-type, or job keyword) implies a job search
    if not intent and (role or job_type):
        intent = "job_seeker"
    return {"intent": intent, "location": location.title(), "role": role.title(),
            "job_type": job_type}


async def chat(message: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Human-like, stateful assistant. Returns {reply, action?}. Deterministic
    slot-filling (no LLM loop): once intent + location are known it ACTS."""
    s = _slots(history, message)
    intent, loc, role, jt = s["intent"], s["location"], s["role"], s.get("job_type", "")
    label = {"job_seeker": ((jt + " jobs").strip() if jt else "jobs"), "student": "admissions",
             "travel_agent": "visa options", "car_dealer": "cars"}.get(intent, "")

    if not intent:
        return {"reply": "Sure — tell me what you're after: a **job** (remote, freelance, "
                         "full-time or part-time), **study / admission**, **visa / travel**, "
                         "or **cars**? Just say it in your own words."}

    # remote/freelance jobs are worldwide → location not required; else ask once
    worldwide = jt in ("remote", "freelance")
    if not loc and not worldwide and intent != "car_dealer":
        what = f"{role} {label}".strip() if role else label
        return {"reply": f"Got it — {what}. Which **country or city**? (or say **remote** for worldwide)"}

    if intent == "job_seeker":
        answers = {"role": role, "location": loc, "job_type": jt, "worldwide": worldwide}
    elif intent == "student":
        answers = {"country": loc, "field": role, "level": "Undergraduate"}
    elif intent == "travel_agent":
        answers = {"destination": loc, "nationality": ""}
    else:  # car_dealer
        answers = {"make": role, "model": "", "year": ""}

    pretty = " ".join(x for x in [role, label, ("in " + loc) if loc else ""] if x).strip()
    return {"reply": f"Perfect — searching **{pretty}** now. One moment…",
            "action": {"persona": intent, "answers": answers}}

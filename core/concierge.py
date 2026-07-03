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
    # deterministic fallback
    low = text.lower()
    known = ["python", "javascript", "react", "node", "java", "sql", "aws", "docker",
             "marketing", "sales", "accounting", "design", "seo", "flutter", "php"]
    skills = [s for s in known if s in low][:8]
    role_m = re.search(r"(engineer|developer|manager|designer|analyst|accountant|"
                       r"consultant|specialist|marketer|nurse|teacher)", low)
    return {"role": (role_m.group(1).title() + "" if role_m else ""),
            "skills": skills, "location": "", "seniority": ""}


async def chat(message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """General assistant chat. Falls back to a helpful canned reply without an LLM."""
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if llm:
            sys = ("You are Wild Automations' sales & discovery assistant. Be concise. "
                   "Help users find jobs, admissions, visas, cars, or B2B leads. If they "
                   "state a need, ask only the missing detail, then tell them to run it.")
            convo = ""
            for h in (history or [])[-6:]:
                convo += f"{h.get('role','user')}: {h.get('content','')}\n"
            return await llm.complete(convo + f"user: {message}", system=sys)
    except Exception as exc:
        logger.info("concierge.chat fallback: %s", exc)
    return ("I can find jobs, admissions, visas, cars, or B2B leads for you. "
            "Pick a persona (Student, Job Seeker, Travel Agent, Car Dealer) and I'll "
            "ask what I need, then run a targeted search.")

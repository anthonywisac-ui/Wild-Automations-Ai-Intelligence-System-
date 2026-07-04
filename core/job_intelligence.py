"""
Job Intelligence — normalize → resolve employer → sponsor join → score.

One engine that turns raw scraper output (any source) into a unified,
deduplicated, sponsor-verified, scored job. Reuses:
  - ai_analyzer._extract_salary_usd / _tax_for / _score_job  (salary + appeal)
  - sponsor_index.lookup                                     (gov visa verification)

Public:
    normalize(record)              -> unified job dict            (Step 1 + 2)
    score(job, sponsor)            -> intelligence block          (Step 4)
    async process(records)         -> deduped, verified, scored jobs  (ties it together)
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── light lexicons (deterministic; AI optional later) ─────────────────────────
_SKILLS = ["python", "javascript", "typescript", "react", "node", "java", "sql",
           "aws", "azure", "docker", "kubernetes", "php", "flutter", "go", "rust",
           "nursing", "care", "healthcare", "carer", "hgv", "driver", "chef",
           "welder", "electrician", "accounting", "marketing", "sales", "design",
           "data", "machine learning", "devops", "security", "support"]
_SENIORITY = [("lead", ["lead", "principal", "head of", "director", "vp", "chief"]),
              ("senior", ["senior", "sr.", "sr ", "staff"]),
              ("junior", ["junior", "jr.", "graduate", "entry", "trainee", "intern"]),
              ("mid", [])]
_SUFFIX = re.compile(r"\b(ltd|limited|llc|inc|plc|llp|co|company|group|holdings|"
                     r"services|solutions|international|the)\b", re.I)
_UK = ("uk", "united kingdom", "london", "england", "scotland", "wales", "manchester",
       "birmingham", "leeds", "glasgow", "liverpool")


def _canon(name: str) -> str:
    n = re.sub(r"[^a-z0-9&\s]", " ", (name or "").lower())
    return re.sub(r"\s+", " ", _SUFFIX.sub(" ", n)).strip()


def _seniority(title: str) -> str:
    t = (title or "").lower()
    for label, kws in _SENIORITY:
        if any(k in t for k in kws):
            return label
    return "mid"


def _skills(text: str) -> List[str]:
    t = (text or "").lower()
    return [s for s in _SKILLS if s in t][:10]


def _country_city(location: str) -> tuple:
    loc = (location or "").strip()
    low = loc.lower()
    if any(k in low for k in _UK):
        iso = "GB"
    elif any(k in low for k in ("uae", "dubai", "abu dhabi", "sharjah")):
        iso = "AE"
    elif "usa" in low or "united states" in low or ", us" in low:
        iso = "US"
    elif "canada" in low:
        iso = "CA"
    elif "germany" in low:
        iso = "DE"
    else:
        iso = ""
    city = loc.split(",")[0].strip() if loc else ""
    return iso, city


def normalize(record: Dict[str, Any]) -> Dict[str, Any]:
    """Any scraper record -> one unified job structure (Steps 1 & 2)."""
    md = record.get("metadata") or {}
    title = (record.get("title") or "").strip()
    company = (md.get("company") or "").strip()
    location = record.get("location") or md.get("location") or ""
    desc = record.get("description") or ""
    iso, city = _country_city(location)
    remote = bool(md.get("remote")) or "remote" in (location + " " + title).lower()

    # salary via existing analyzer (reuse)
    usd = take = None
    try:
        from core.ai_analyzer import _extract_salary_usd, _tax_for
        usd = _extract_salary_usd(record.get("price"), desc)
        if usd:
            take = round(usd * (1 - _tax_for(location)))
    except Exception:
        pass

    norm_title = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ",
                        re.sub(r"\b(senior|junior|lead|sr|jr|principal|staff|intern|graduate)\b",
                               "", (title or "").lower()))).strip()
    dedup = hashlib.md5(f"{_canon(company)}|{norm_title}|{city.lower()}".encode()).hexdigest()[:16]

    return {
        "job_id": dedup,
        "title": title, "norm_title": norm_title, "seniority": _seniority(title),
        "employer": {"name": company or "—", "canonical": _canon(company)},
        "country_iso": iso, "city": city, "location": location, "remote": remote,
        "salary": {"raw": md.get("salary") or record.get("price") or "",
                   "usd_annual": usd, "take_home_usd": take,
                   "display": (md.get("salary") or record.get("price") or "").strip() or "—"},
        "skills": _skills(f"{title} {desc}"),
        "visa_flag": bool(md.get("visa_sponsorship")) or ("visa" in desc.lower() or "sponsor" in desc.lower()),
        "source": md.get("source") or record.get("_source") or "",
        "url": record.get("source_url") or "",
        "posted": md.get("created_at") or record.get("created_at") or md.get("date_posted") or "",
        "employees": md.get("employees") or md.get("company_size") or "",
        "description": desc,
    }


def score(job: Dict[str, Any], sponsor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compute the intelligence block (Step 4) — evidence-backed, no hallucination."""
    evidence: List[Dict[str, Any]] = []
    usd = (job.get("salary") or {}).get("usd_annual")

    # reuse the existing appeal scorer defensively
    ai_score = 0.5
    try:
        from core.ai_analyzer import _score_job
        s = _score_job({"title": job.get("title"), "price": (job.get("salary") or {}).get("raw"),
                        "location": job.get("location"), "description": job.get("description"),
                        "metadata": {}})
        ai_score = float(s.get("universal_appeal_score", s.get("appeal", 0.5)) or 0.5)
    except Exception:
        pass

    salary_score = round(min(1.0, (usd or 0) / 200000), 3)
    remote_score = 1.0 if job.get("remote") else 0.35
    demand_score = round(min(1.0, 0.4 + 0.1 * len(job.get("skills") or [])), 3)

    # visa score strictly from gov evidence
    visa_score = 0.0
    if sponsor and sponsor.get("matched"):
        visa_score = round(0.85 + 0.15 * (sponsor.get("confidence", 1.0)), 3)
        evidence.append({"type": "sponsor_register", "source": sponsor["evidence"]["source"],
                         "detail": f"Licensed sponsor '{sponsor['name']}' · routes: "
                                   f"{', '.join(sponsor.get('routes', [])) or 'n/a'}"})
    elif job.get("visa_flag"):
        visa_score = 0.5
        evidence.append({"type": "listing_flag", "source": job.get("source"),
                         "detail": "Listing indicates visa sponsorship (unverified)"})

    if usd:
        evidence.append({"type": "salary", "source": "normalizer",
                         "detail": f"~${usd:,.0f}/yr USD" + (f" (~${job['salary']['take_home_usd']:,.0f} take-home)"
                                                             if job['salary'].get('take_home_usd') else "")})

    completeness = sum(bool(x) for x in [usd, job.get("employer", {}).get("name") != "—",
                                         job.get("city"), job.get("skills")]) / 4
    confidence = round(0.4 + 0.5 * completeness + (0.1 if sponsor and sponsor.get("matched") else 0), 3)
    risk = round(1 - confidence, 3)

    verified = bool(sponsor and sponsor.get("matched"))
    summary = (f"{job.get('title','role')} at "
               f"{job['employer']['name']}"
               + (f" · Visa Sponsor VERIFIED ({', '.join(sponsor.get('routes', [])[:2]) or 'Skilled Worker'})"
                  if verified else (" · sponsorship indicated (unverified)" if job.get("visa_flag") else ""))
               + (f" · ~${usd:,.0f}" if usd else ""))

    return {
        "ai_score": round(ai_score, 3), "salary_score": salary_score,
        "demand_score": demand_score, "remote_score": remote_score,
        "visa_score": visa_score, "experience": job.get("seniority"),
        "sponsor_verified": verified, "confidence": min(1.0, confidence), "risk": risk,
        "summary": summary, "evidence": evidence,
    }


async def process(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize + dedup + sponsor-join + score a batch (ties Steps 1-4)."""
    from core import sponsor_index
    await sponsor_index.ensure_loaded()

    seen: Dict[str, Dict[str, Any]] = {}
    for r in records:
        job = normalize(r)
        sponsor = sponsor_index.lookup(job["employer"]["name"])
        job["sponsor"] = sponsor
        job["intelligence"] = score(job, sponsor)
        key = job["job_id"]
        # dedup: keep the richer / verified one
        prev = seen.get(key)
        if prev is None or (job["intelligence"]["confidence"] > prev["intelligence"]["confidence"]):
            if prev:
                job["_merged_sources"] = list(set(prev.get("_merged_sources", [prev["source"]]) + [job["source"]]))
            seen[key] = job

    jobs = sorted(seen.values(), key=lambda j: (j["intelligence"]["sponsor_verified"],
                                                j["intelligence"]["ai_score"]), reverse=True)
    verified = sum(1 for j in jobs if j["intelligence"]["sponsor_verified"])
    return {"jobs": jobs, "total": len(jobs), "verified_sponsors": verified,
            "sponsor_index": sponsor_index.stats()}

"""
AI Analyzer — post-processing value-scoring layer.

Runs OVER already-scraped records (does NOT touch scrapers). For every record
it computes "Universal Human Appeal" heuristics and attaches an `ai_scores`
block, then ranks the whole batch. Pure-deterministic NLP + statistics — no
external LLM call required, so it is fast and free to run daily.

Public API:
    analyze_records(records) -> list[dict]   # each: {original_data, ai_scores}

Each input record is expected to carry `_category` ("Jobs"|"University"|
"Visa"|"Automobiles") and `_source` (scraper name). If absent, category is
inferred from metadata.type.
"""

from __future__ import annotations

import math
import re
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ── Hardcoded reference tables (Numbeo-style cost of living, NYC = 100) ────────

COST_OF_LIVING = {
    "dubai": 62, "abu dhabi": 58, "sharjah": 50, "uae": 60,
    "london": 88, "manchester": 62, "united kingdom": 70, "uk": 70,
    "new york": 100, "san francisco": 96, "seattle": 84, "austin": 70,
    "usa": 78, "united states": 78,
    "toronto": 72, "vancouver": 74, "canada": 70,
    "berlin": 65, "munich": 72, "germany": 68,
    "singapore": 82, "sydney": 80, "melbourne": 74, "australia": 76,
    "remote": 55, "global": 60,
}

# Effective take-home tax burden (fraction withheld) by country keyword
TAX_RATES = {
    "uae": 0.0, "dubai": 0.0, "abu dhabi": 0.0, "sharjah": 0.0,
    "uk": 0.20, "united kingdom": 0.20, "london": 0.20, "manchester": 0.20,
    "usa": 0.24, "united states": 0.24, "new york": 0.28, "san francisco": 0.30,
    "canada": 0.22, "toronto": 0.22, "vancouver": 0.22,
    "germany": 0.30, "berlin": 0.30, "munich": 0.30,
    "singapore": 0.15, "australia": 0.25, "sydney": 0.25,
}

_DEFAULT_COL = 65
_DEFAULT_TAX = 0.15

# Keyword banks for NLP-style flag detection
_LENIENT_KEYWORDS = (
    "holistic review", "holistic", "work experience", "professional experience",
    "no minimum", "conditional admission", "foundation", "pathway",
    "flexible entry", "portfolio", "personal statement", "waiver", "test-optional",
)
_STRICT_CGPA = re.compile(r"(minimum|min\.?|require[sd]?)\s*(c?gpa|grade)\s*(of\s*)?([3-4]\.\d)", re.I)
_VISA_POSITIVE = ("sponsor", "visa", "relocation", "relocate", "work permit", "tier 2", "skilled worker")
_VISA_NEGATIVE = ("must have right to work", "right to work", "no sponsorship", "citizens only", "must be authorized")
_SERVICE_HISTORY = ("full service history", "service history", "fsh", "dealer maintained", "one owner", "single owner")

# ── Category inference ────────────────────────────────────────────────────────

def _category_of(r: Dict[str, Any]) -> str:
    if r.get("_category"):
        return r["_category"]
    t = (r.get("metadata") or {}).get("type", "").lower()
    if t == "lead":
        return "Leads"
    if t in ("job", "uk_sponsor"):
        return "Jobs"
    if t.startswith("admission") or t in ("university", "admissions_guide", "admissions_data"):
        return "University"
    if t == "vehicle":
        return "Automobiles"
    if "visa" in t or "passport" in t:
        return "Visa"
    return "Other"


# ── Numeric extraction helpers ────────────────────────────────────────────────

def _extract_salary_usd(price: Any, description: str = "") -> Optional[float]:
    """Parse salary strings to an annual USD midpoint. Handles ranges & /month."""
    text = f"{price} {description}"
    nums = [float(n.replace(",", "")) for n in re.findall(r"[\d,]+(?:\.\d+)?", text) if n.replace(",", "").isdigit()]
    nums = [n for n in nums if n >= 1000]  # ignore stray small numbers
    if not nums:
        return None
    val = statistics.median(sorted(nums)[:2]) if len(nums) >= 2 else nums[0]
    low = f"{price} {description}".lower()
    if "month" in low or "/mo" in low or "aed" in low and val < 60000:
        val *= 12
    return round(val, 2)


def _col_for(location: str) -> float:
    loc = (location or "").lower()
    for key, idx in COST_OF_LIVING.items():
        if key in loc:
            return idx
    return _DEFAULT_COL


def _tax_for(location: str) -> float:
    loc = (location or "").lower()
    for key, rate in TAX_RATES.items():
        if key in loc:
            return rate
    return _DEFAULT_TAX


def _days_since(iso_str: str) -> Optional[int]:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError):
        return None


def _deadline_within_days(text: str, window: int = 30) -> Optional[int]:
    """Best-effort: find a 'DD Month' or ISO date and return days remaining."""
    now = datetime.now(timezone.utc)
    months = {m.lower(): i for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"], 1)}
    best = None
    for d, mon in re.findall(r"(\d{1,2})\s+([A-Za-z]+)", text or ""):
        mi = months.get(mon.lower())
        if not mi:
            continue
        for yr in (now.year, now.year + 1):
            try:
                target = datetime(yr, mi, int(d), tzinfo=timezone.utc)
            except ValueError:
                continue
            delta = (target - now).days
            if 0 <= delta <= 365 and (best is None or delta < best):
                best = delta
    return best if (best is not None and best <= window) else None


# ── Value rating bucketing ────────────────────────────────────────────────────

def _value_rating(score: float) -> str:
    if score >= 0.80:
        return "Hidden Gem"
    if score >= 0.62:
        return "Good Deal"
    if score >= 0.42:
        return "Average"
    return "Overpriced"


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


# ── Category scorers ──────────────────────────────────────────────────────────

def _score_job(r: Dict[str, Any]) -> Dict[str, Any]:
    desc = (r.get("description") or "").lower()
    loc = r.get("location") or ""
    salary = _extract_salary_usd(r.get("price"), r.get("description", ""))

    # Net purchasing power
    npp_score, npp_val = 0.4, None
    if salary:
        take_home = salary * (1 - _tax_for(loc))
        npp_val = round(take_home / _col_for(loc), 0)
        npp_score = _clamp(npp_val / 3000)  # ~$3000/COL-unit ≈ excellent

    # Visa probability
    visa = 50
    if any(k in desc for k in _VISA_NEGATIVE):
        visa = 0
    elif any(k in desc for k in _VISA_POSITIVE) or "sponsor" in (r.get("metadata") or {}).get("type", ""):
        visa = 100
    visa_score = visa / 100

    # Job age anomaly
    age = _days_since((r.get("metadata") or {}).get("scraped_at", "") or r.get("created_at", ""))
    fresh = age is not None and age <= 3
    stale = age is not None and age >= 30
    hot_lead = bool(fresh and salary and salary >= 100000)

    appeal = _clamp(0.45 * npp_score + 0.35 * visa_score + (0.20 if not stale else 0.0))
    if hot_lead:
        appeal = _clamp(appeal + 0.12)

    return {
        "universal_appeal_score": round(appeal, 3),
        "value_rating": _value_rating(appeal),
        "deal_breakdown": {
            "annual_salary_usd": salary,
            "net_purchasing_power": npp_val,
            "visa_probability": visa,
            "flags": ([f"Fresh Hot Lead"] if hot_lead else []) + (["Stale (30d+)"] if stale else []) +
                     (["Visa Sponsorship Likely"] if visa >= 100 else []) +
                     (["Tax-Free Income"] if _tax_for(loc) == 0.0 and salary else []),
            "why": _job_reason(salary, npp_val, visa, hot_lead, loc),
        },
    }


def _job_reason(salary, npp, visa, hot, loc) -> str:
    parts = []
    if salary:
        parts.append(f"${int(salary):,}/yr")
    if _tax_for(loc) == 0.0 and salary:
        parts.append("0% tax region")
    if visa >= 100:
        parts.append("mentions visa/sponsorship")
    if hot:
        parts.append("fresh high-pay lead")
    return " · ".join(parts) or "Limited salary/visa signal"


def _score_university(r: Dict[str, Any]) -> Dict[str, Any]:
    m = r.get("metadata") or {}
    blob = " ".join(str(v) for v in (r.get("description", ""), m.get("criteria", ""),
                                     m.get("hot_subjects", ""), r.get("title", ""))).lower()

    # Leniency index
    lenient_hits = sum(1 for k in _LENIENT_KEYWORDS if k in blob)
    has_strict = bool(_STRICT_CGPA.search(blob)) or (m.get("gpa_minimum") and float(m.get("gpa_minimum") or 0) >= 3.5)
    cgpa_friendly = (lenient_hits > 0 or "ielts 6" in blob) and not has_strict
    leniency_score = _clamp(0.3 + 0.18 * lenient_hits + (0.25 if cgpa_friendly else 0) - (0.3 if has_strict else 0))

    # ROI score (grad salary / tuition)
    tuition = _num(m.get("tuition_out_of_state") or m.get("tuition") or m.get("annual_fee"))
    grad_sal = _num(m.get("median_earnings") or m.get("graduate_salary"))
    roi, roi_score = None, 0.45
    if tuition and grad_sal:
        roi = round(grad_sal / tuition, 2)
        roi_score = _clamp(roi / 4.0)  # 4x = top tier
    elif tuition and tuition < 15000:
        roi_score = 0.7  # cheap tuition is inherently high-appeal

    # Scholarship density (keyword proxy)
    sch = blob.count("scholarship") + blob.count("funding") + blob.count("bursary") + blob.count("financial aid")
    sch_score = _clamp(0.35 + 0.15 * sch)

    # Deadline urgency
    deadline_days = _deadline_within_days(blob + " " + str(m.get("deadlines", "")) +
                                          " " + str(m.get("application_deadline", "")))
    deadline_soon = deadline_days is not None

    # Academic-intel taxonomy: late-intake windows + stipend/free-tuition triggers.
    # Prefer flags already attached by the pipeline enrichment stage; else compute.
    ai_flags = m.get("academic_flags")
    if ai_flags is None:
        from core import academic_intel
        ai_flags = academic_intel.flags(blob, m)
    is_late = ai_flags.get("is_late_intake")
    has_funding = ai_flags.get("has_funding")
    free_tuition = ai_flags.get("free_tuition")
    cash_stipend = ai_flags.get("cash_stipend")

    appeal = _clamp(0.35 * leniency_score + 0.25 * roi_score + 0.25 * sch_score)
    if deadline_soon:
        appeal = _clamp(appeal + 0.08)
    if is_late:
        appeal = _clamp(appeal + 0.15)   # open-now window = act immediately
    if cash_stipend:
        appeal = _clamp(appeal + 0.15)   # gets paid to study
    elif free_tuition:
        appeal = _clamp(appeal + 0.10)
    elif has_funding:
        appeal = _clamp(appeal + 0.05)

    flags = []
    if is_late:
        flags.append(f"🔓 Late intake ({', '.join(ai_flags.get('late_terms', [])[:2]) or 'open'})")
    if cash_stipend:
        flags.append("💵 Cash stipend")
    elif free_tuition:
        flags.append("Free tuition")
    if cgpa_friendly:
        flags.append("CGPA-Friendly")
    if roi and roi >= 3:
        flags.append("High ROI")
    if sch >= 2 or has_funding:
        flags.append("Funding available")
    if deadline_soon:
        flags.append(f"Deadline in {deadline_days}d")

    return {
        "universal_appeal_score": round(appeal, 3),
        "value_rating": _value_rating(appeal),
        "deal_breakdown": {
            "leniency_index": round(leniency_score, 2),
            "cgpa_friendly": cgpa_friendly,
            "roi_score": roi,
            "scholarship_density": sch,
            "deadline_days_left": deadline_days,
            "is_late_intake": is_late, "cash_stipend": cash_stipend, "free_tuition": free_tuition,
            "funding_class": ai_flags.get("funding_class"),
            "admission_status": ai_flags.get("admission_status"),
            "flags": flags,
            "why": ai_flags.get("why_valuable") or _uni_reason(cgpa_friendly, roi, sch, deadline_days,
                                                               is_late, cash_stipend or free_tuition),
        },
    }


def _uni_reason(friendly, roi, sch, dl, is_late=False, funded=False) -> str:
    parts = []
    if is_late:
        parts.append("open-now late intake")
    if funded:
        parts.append("funding/stipend available")
    if friendly:
        parts.append("accepts average grades")
    if roi and roi >= 3:
        parts.append(f"{roi}x salary-to-tuition ROI")
    if sch >= 2:
        parts.append("multiple funding mentions")
    if dl is not None:
        parts.append(f"apply within {dl} days")
    return " · ".join(parts) or "Standard admissions profile"


def _score_visa(r: Dict[str, Any]) -> Dict[str, Any]:
    """Visa ease scoring — low friction / no job offer / passport-neutral = high value."""
    m = r.get("metadata") or {}
    blob = f"{r.get('title','')} {r.get('description','')}"
    vf = m.get("visa_flags")
    if vf is None:
        from core import visa_intel
        vf = visa_intel.flags(blob, m)
    simplicity = float(vf.get("simplicity_score") or 0)
    new_route = vf.get("is_new_route")
    passport_neutral = vf.get("passport_neutral")
    requires_job = vf.get("requires_job_offer")

    appeal = _clamp(simplicity / 10)
    if new_route:
        appeal = _clamp(appeal + 0.08)
    if passport_neutral:
        appeal = _clamp(appeal + 0.08)
    if requires_job:
        appeal = _clamp(appeal - 0.15)

    flags = []
    if vf.get("friction_level") == "Low":
        flags.append(f"🟢 Low friction ({simplicity}/10)")
    if not requires_job and vf.get("ease_terms"):
        flags.append("No job offer needed")
    if passport_neutral:
        flags.append("Passport-neutral")
    if new_route:
        flags.append("🆕 New route")

    return {
        "universal_appeal_score": round(appeal, 3),
        "value_rating": _value_rating(appeal),
        "deal_breakdown": {
            "simplicity_score": simplicity,
            "friction_level": vf.get("friction_level"),
            "requires_job_offer": requires_job,
            "passport_neutral": passport_neutral,
            "is_new_route": new_route,
            "ease_terms": vf.get("ease_terms"),
            "flags": flags,
            "why": vf.get("bypass_value") or _visa_reason(simplicity, requires_job, passport_neutral, new_route),
        },
    }


def _visa_reason(simplicity, requires_job, neutral, new_route) -> str:
    parts = []
    if simplicity >= 7:
        parts.append(f"easy ({simplicity}/10)")
    if not requires_job:
        parts.append("no job offer required")
    if neutral:
        parts.append("centralized/passport-neutral processing")
    if new_route:
        parts.append("newly launched route")
    return " · ".join(parts) or "Standard visa pathway"


def _score_vehicle(r: Dict[str, Any], baseline: Dict[Tuple, Tuple[float, float]]) -> Dict[str, Any]:
    m = r.get("metadata") or {}
    price = _num(m.get("price_usd")) or _num(r.get("price"))
    make = str(m.get("make", "")).lower()
    model = str(m.get("model", "")).split()[0].lower() if m.get("model") else ""
    year = m.get("year")
    key = (make, model, year)

    median, std = baseline.get(key) or baseline.get(("_ALL_", "", None)) or (price, 1)
    deal_score, pct_below = 0.0, None
    if price and median and std and std > 0:
        deal_score = round((median - price) / std, 2)
        pct_below = round((median - price) / median * 100, 1) if median else None

    # Mileage penalty / service history bonus
    mileage = _num(m.get("mileage"))
    car_age = max(1, (datetime.now().year - int(year))) if year else 1
    km_per_year = (mileage / car_age) if mileage else 0
    mileage_penalty = km_per_year > 20000
    desc = (r.get("description") or "").lower()
    service_history = any(k in desc for k in _SERVICE_HISTORY)

    base = 0.5 + 0.18 * deal_score
    if mileage_penalty:
        base -= 0.15
    if service_history:
        base += 0.12
    appeal = _clamp(base)

    return {
        "universal_appeal_score": round(appeal, 3),
        "value_rating": _value_rating(appeal),
        "deal_breakdown": {
            "listing_price_usd": price,
            "market_median_usd": round(median) if median else None,
            "deal_z_score": deal_score,
            "pct_below_market": pct_below,
            "km_per_year": round(km_per_year) if km_per_year else None,
            "flags": (["Significantly Below Market"] if deal_score > 1.5 else []) +
                     (["High Mileage"] if mileage_penalty else []) +
                     (["Full Service History"] if service_history else []),
            "why": _car_reason(pct_below, deal_score, service_history, mileage_penalty),
        },
    }


def _car_reason(pct, z, svc, high_km) -> str:
    parts = []
    if pct and pct > 0:
        parts.append(f"{pct}% below market")
    if z > 1.5:
        parts.append(f"Z={z} (rare deal)")
    if svc:
        parts.append("full service history")
    if high_km:
        parts.append("high annual mileage")
    return " · ".join(parts) or "Priced at market average"


_ICP_TITLES = {"founder": 35, "ceo": 32, "cto": 30, "vp": 25, "chief": 28,
               "director": 22, "head": 20, "owner": 26, "manager": 15,
               "lead": 14, "engineer": 10, "marketing": 12, "sales": 12}


_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().\-]{7,}\d)")
_URL_RE = re.compile(r"(https?://|www\.|\.com|\.ae|\.io|\.co\b|\.net)", re.I)
_REACH_RE = re.compile(r"([\d][\d.,]*)\s*([KMB])?\s*(followers|likes|subscribers)", re.I)


def _parse_reach(text: str) -> int:
    """Largest follower/like count found in text → integer."""
    best = 0
    for num, unit, _ in _REACH_RE.findall(text or ""):
        try:
            val = float(num.replace(",", ""))
        except ValueError:
            continue
        mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get((unit or "").lower(), 1)
        best = max(best, int(val * mult))
    return best


def _score_lead(r: Dict[str, Any]) -> Dict[str, Any]:
    """Lead appeal = max(individual ICP intent, business contactability + reach).

    Individual leads score on role seniority + buying intent. Business leads
    (agencies, pages, Maps listings) score on contactability (phone/website),
    audience reach (followers/likes), and buying intent — so a real business
    with a phone number and audience ranks high even without a 'role'.
    """
    m = r.get("metadata") or {}
    role = (m.get("role") or "").lower()
    text = f"{r.get('title','')} {r.get('description','')} {' '.join(m.get('comments') or [])}"
    blob = text.lower()

    # ── Individual ICP track ──
    icp = 0
    for kw, pts in _ICP_TITLES.items():
        if kw in role or kw in blob:
            icp = max(icp, pts)
    icp_score = _clamp(icp / 35)

    # ── Intent / sentiment / signals (from GROQ analysis if present) ──
    intent = (m.get("intent") or "").lower()
    sentiment = (m.get("sentiment") or "").lower()
    actionable = bool(m.get("actionable"))
    signals = m.get("buying_signals") or []
    intent_score = 1.0 if intent == "interested" else 0.5 if intent in ("undecided", "") else 0.15
    sig_score = _clamp(0.25 + 0.2 * len(signals))

    # ── Business contactability + reach track ──
    has_phone = bool(m.get("phone")) or bool(_PHONE_RE.search(text))
    has_web = bool(_URL_RE.search(text)) or bool(m.get("website"))
    has_email = bool(m.get("email")) or ("@" in text and "gmail" not in blob[:0])
    reach = _parse_reach(text)
    reach_score = _clamp(math.log10(reach + 1) / 6) if reach else 0.0   # 1M ≈ 1.0
    contact_score = 0.5 * (1 if has_phone else 0) + 0.3 * (1 if has_web else 0) + 0.2 * (1 if has_email else 0)
    business_score = _clamp(0.35 * contact_score + 0.35 * reach_score + 0.30 * intent_score)

    individual_score = _clamp(0.45 * icp_score + 0.35 * intent_score + 0.20 * sig_score)

    # ── Operational-pain track (Review Miner) — the "bleeding-leads" prospect ──
    rating = m.get("rating")
    review_count = m.get("review_count") or 0
    pain_like = m.get("pain_likelihood")
    frictions = m.get("likely_friction") or []
    complaint_hit = any(k in blob for k in
                        ("missed call", "no answer", "no response", "slow", "rude",
                         "never called", "no reply", "waited", "ghosted", "complaint"))
    # High review volume + sub-4.2 rating = systemic failure = hot lead
    pain_score = 0.0
    if pain_like is not None:
        pain_score = float(pain_like)
    elif rating:
        pain_score = _clamp((4.6 - float(rating)) / 1.6) * (0.6 + 0.4 * _clamp(review_count / 200))
    if complaint_hit:
        pain_score = _clamp(pain_score + 0.15)

    appeal = max(business_score, individual_score, pain_score)
    if actionable:
        appeal = _clamp(appeal + 0.10)
    if sentiment == "positive":
        appeal = _clamp(appeal + 0.05)
    if has_phone:
        appeal = _clamp(appeal + 0.08)  # direct contact = highly actionable
    if frictions:
        appeal = _clamp(appeal + 0.06)

    flags = []
    if has_phone:
        flags.append("☎ Phone available")
    if has_web:
        flags.append("Website")
    if reach >= 1000:
        flags.append(f"{_human_reach(reach)} reach")
    if rating and pain_score >= 0.5:
        flags.append(f"⚠ Pain: {rating}★/{review_count} reviews")
    for fr in frictions[:2]:
        flags.append(f"Pain: {fr}")
    if intent == "interested":
        flags.append("High Intent")
    if signals:
        flags.append(f"{len(signals)} buying signals")
    if icp >= 20:
        flags.append(f"ICP: {role[:18]}")
    if actionable:
        flags.append("Actionable")

    return {
        "universal_appeal_score": round(appeal, 3),
        "value_rating": _value_rating(appeal),
        "deal_breakdown": {
            "platform": m.get("platform"),
            "has_phone": has_phone, "has_website": has_web, "reach": reach,
            "rating": rating, "review_count": review_count,
            "pain_score": round(pain_score, 3), "likely_friction": frictions,
            "department": m.get("department"), "recommended_offer": m.get("recommended_offer"),
            "icp_score": icp, "intent": intent or None, "sentiment": sentiment or None,
            "buying_signals": signals,
            "flags": flags,
            "why": _lead_reason_v2(role, icp, intent, signals, actionable, has_phone,
                                   has_web, reach, rating, review_count, pain_score, frictions,
                                   m.get("recommended_offer")),
        },
    }


def _lead_reason_v2(role, icp, intent, signals, actionable, has_phone, has_web, reach,
                    rating, reviews, pain_score, frictions, offer) -> str:
    parts = []
    if pain_score >= 0.5 and rating:
        parts.append(f"{rating}★ w/ {reviews} reviews (operational pain)")
    if frictions:
        parts.append(f"friction: {', '.join(frictions[:2])}")
    if offer:
        parts.append(f"pitch: {offer}")
    if has_phone:
        parts.append("phone on file")
    if reach >= 1000:
        parts.append(f"{_human_reach(reach)} audience")
    if intent == "interested":
        parts.append("high buying intent")
    if signals:
        parts.append(f"signals: {', '.join(signals[:2])}")
    return " · ".join(parts) or "Standard lead profile"


def _human_reach(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1e6:.1f}M"
    if n >= 1_000:
        return f"{n/1e3:.0f}K"
    return str(n)


def _lead_reason(role, icp, intent, signals, actionable, has_phone=False, has_web=False, reach=0) -> str:
    parts = []
    if has_phone:
        parts.append("phone on file")
    if reach >= 1000:
        parts.append(f"{_human_reach(reach)} audience")
    if has_web:
        parts.append("has website")
    if icp >= 20:
        parts.append(f"senior role ({role[:20]})")
    if intent == "interested":
        parts.append("high buying intent")
    if signals:
        parts.append(f"signals: {', '.join(signals[:2])}")
    if actionable:
        parts.append("actionable")
    return " · ".join(parts) or "Standard lead profile"


def _score_generic(r: Dict[str, Any]) -> Dict[str, Any]:
    """Visa / other records — informational appeal (freshness-based)."""
    age = _days_since((r.get("metadata") or {}).get("scraped_at", ""))
    appeal = 0.55 if (age is not None and age <= 7) else 0.45
    return {
        "universal_appeal_score": round(appeal, 3),
        "value_rating": _value_rating(appeal),
        "deal_breakdown": {"flags": [], "why": "Reference / policy record"},
    }


# ── Baseline computation for vehicles ─────────────────────────────────────────

def _build_vehicle_baseline(vehicles: List[Dict[str, Any]]) -> Dict[Tuple, Tuple[float, float]]:
    groups: Dict[Tuple, List[float]] = {}
    all_prices: List[float] = []
    for r in vehicles:
        m = r.get("metadata") or {}
        price = _num(m.get("price_usd")) or _num(r.get("price"))
        if not price:
            continue
        make = str(m.get("make", "")).lower()
        model = str(m.get("model", "")).split()[0].lower() if m.get("model") else ""
        key = (make, model, m.get("year"))
        groups.setdefault(key, []).append(price)
        all_prices.append(price)

    baseline: Dict[Tuple, Tuple[float, float]] = {}
    for key, prices in groups.items():
        if len(prices) >= 3:
            baseline[key] = (statistics.median(prices), statistics.pstdev(prices) or 1)
    if all_prices:
        baseline[("_ALL_", "", None)] = (
            statistics.median(all_prices),
            statistics.pstdev(all_prices) or (statistics.median(all_prices) * 0.15) or 1,
        )
    return baseline


def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(re.sub(r"[^\d.]", "", str(v)) or 0) or None
    except (ValueError, TypeError):
        return None


# ── Public entrypoint ─────────────────────────────────────────────────────────

def analyze_records(records: List[Dict[str, Any]],
                    history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Score every record; return list of {original_data, ai_scores} ranked desc.

    `history` (past persisted records) is folded into the vehicle price baseline
    so Deal Z-scores are computed over the full historical population, not just
    the current batch — this is what makes deal detection genuinely accurate.
    Only current `records` are scored/returned; history only informs baselines.
    """
    current_vehicles = [r for r in records if _category_of(r) == "Automobiles"]
    hist_vehicles = [r for r in (history or []) if _category_of(r) == "Automobiles"]
    baseline = _build_vehicle_baseline(current_vehicles + hist_vehicles)

    out: List[Dict[str, Any]] = []
    for r in records:
        cat = _category_of(r)
        if cat == "Jobs":
            scores = _score_job(r)
        elif cat == "University":
            scores = _score_university(r)
        elif cat == "Automobiles":
            scores = _score_vehicle(r, baseline)
        elif cat == "Leads":
            scores = _score_lead(r)
        elif cat == "Visa":
            scores = _score_visa(r)
        else:
            scores = _score_generic(r)
        scores["category"] = cat
        scores["source"] = r.get("_source", "")
        out.append({"original_data": r, "ai_scores": scores})

    out.sort(key=lambda x: x["ai_scores"]["universal_appeal_score"], reverse=True)
    return out


def summarize(scored: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate stats for the dashboard header."""
    ratings = [s["ai_scores"]["value_rating"] for s in scored]
    return {
        "total": len(scored),
        "hidden_gems": ratings.count("Hidden Gem"),
        "good_deals": ratings.count("Good Deal"),
        "average": ratings.count("Average"),
        "overpriced": ratings.count("Overpriced"),
        "avg_appeal": round(statistics.mean(
            [s["ai_scores"]["universal_appeal_score"] for s in scored]), 3) if scored else 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

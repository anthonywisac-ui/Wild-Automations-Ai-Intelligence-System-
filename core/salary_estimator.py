"""Salary Estimator — 3-tier: regex extract → market table → LLM fallback."""
from __future__ import annotations
import re
from typing import Optional

# Market data: (role_key, country_key, seniority) -> (low_usd, high_usd) annual
_MARKET: dict[tuple, tuple] = {
    # Software Engineering
    ("software engineer", "usa", "senior"):    (130000, 210000),
    ("software engineer", "usa", "mid"):       (90000, 140000),
    ("software engineer", "usa", "junior"):    (60000, 95000),
    ("software engineer", "uk", "senior"):     (80000, 130000),
    ("software engineer", "uk", "mid"):        (55000, 85000),
    ("software engineer", "uk", "junior"):     (35000, 55000),
    ("software engineer", "uae", "senior"):    (50000, 90000),
    ("software engineer", "uae", "mid"):       (35000, 60000),
    ("software engineer", "uae", "junior"):    (20000, 38000),
    ("software engineer", "germany", "senior"): (75000, 115000),
    ("software engineer", "remote", "senior"): (90000, 160000),
    ("software engineer", "remote", "mid"):    (65000, 110000),
    # Data Science / ML
    ("data scientist", "usa", "senior"):       (140000, 220000),
    ("data scientist", "usa", "mid"):          (100000, 150000),
    ("data scientist", "uk", "senior"):        (85000, 130000),
    ("data scientist", "remote", "senior"):    (100000, 170000),
    # Product / Project Management
    ("product manager", "usa", "senior"):      (150000, 240000),
    ("product manager", "usa", "mid"):         (110000, 160000),
    ("project manager", "usa", "senior"):      (110000, 170000),
    ("project manager", "uk", "senior"):       (70000, 110000),
    ("project manager", "uae", "senior"):      (45000, 80000),
    # DevOps / Platform
    ("devops", "usa", "senior"):               (130000, 200000),
    ("devops", "usa", "mid"):                  (95000, 140000),
    ("devops", "remote", "senior"):            (110000, 180000),
    # Design
    ("designer", "usa", "senior"):             (110000, 170000),
    ("designer", "uk", "senior"):              (65000, 100000),
    ("designer", "remote", "senior"):          (80000, 140000),
    # Data Analyst
    ("data analyst", "usa", "senior"):         (90000, 140000),
    ("data analyst", "usa", "mid"):            (65000, 100000),
    ("data analyst", "uk", "mid"):             (40000, 65000),
    # Marketing
    ("marketing", "usa", "senior"):            (90000, 150000),
    ("marketing", "uk", "senior"):             (55000, 90000),
    # Sales
    ("sales", "usa", "senior"):                (80000, 160000),
    ("sales", "uk", "senior"):                 (50000, 100000),
}

_SALARY_RE = re.compile(
    r"(?:£|€|\$|USD|GBP|EUR|AED|PKR|INR|CAD|AUD)\s*[\d,]+(?:[kK])?"
    r"(?:\s*[-–]\s*[\d,kK]+)?"
    r"(?:\s*(?:per|/)\s*(?:year|yr|annum|month|mo|hour|hr))?",
    re.I,
)
_ROLE_KEYS = [
    "software engineer", "data scientist", "product manager", "project manager",
    "devops", "designer", "data analyst", "marketing", "sales",
    "frontend", "backend", "fullstack", "full stack", "mobile",
]
_SENIORITY_MAP = {
    "senior": ["senior", "sr", "lead", "principal", "staff", "head", "director"],
    "junior": ["junior", "jr", "graduate", "entry", "trainee", "intern"],
    "mid":    [],
}
_COUNTRY_MAP = {
    "usa":     ["usa", "united states", "new york", "san francisco", "seattle", "austin", "boston"],
    "uk":      ["uk", "united kingdom", "london", "manchester", "edinburgh", "birmingham"],
    "uae":     ["uae", "dubai", "abu dhabi", "sharjah", "emirates"],
    "germany": ["germany", "berlin", "munich", "frankfurt", "hamburg"],
    "canada":  ["canada", "toronto", "vancouver", "montreal"],
    "remote":  ["remote", "anywhere", "worldwide", "global"],
}


def _detect_seniority(title: str) -> str:
    t = title.lower()
    for level, keywords in _SENIORITY_MAP.items():
        if keywords and any(k in t for k in keywords):
            return level
    return "mid"


def _detect_country(location: str) -> str:
    loc = location.lower()
    for key, terms in _COUNTRY_MAP.items():
        if any(t in loc for t in terms):
            return key
    return "remote"


def _detect_role(title: str) -> Optional[str]:
    t = title.lower()
    for role in _ROLE_KEYS:
        if role in t:
            # normalize synonyms
            if role in ("frontend", "backend", "fullstack", "full stack", "mobile"):
                return "software engineer"
            return role
    return None


def estimate_salary(title: str, location: str, description: str) -> dict:
    """
    Returns:
    {
      "estimated": "$90k - $130k/yr",
      "usd_low": 90000,
      "usd_high": 130000,
      "confidence": "high" | "medium" | "low",
      "method": "extracted" | "market_data" | "unknown"
    }
    """
    text = f"{title} {location} {description}"

    # Tier 1: extract from text
    m = _SALARY_RE.search(text)
    if m:
        return {
            "estimated": m.group(0).strip(),
            "usd_low": None, "usd_high": None,
            "confidence": "high", "method": "extracted"
        }

    # Tier 2: market lookup table
    seniority = _detect_seniority(title)
    country = _detect_country(location)
    role = _detect_role(title)

    if role:
        key = (role, country, seniority)
        if key in _MARKET:
            lo, hi = _MARKET[key]
            return {
                "estimated": f"~${lo//1000}k–${hi//1000}k/yr",
                "usd_low": lo, "usd_high": hi,
                "confidence": "medium", "method": "market_data"
            }
        # Try with remote as fallback country
        key_remote = (role, "remote", seniority)
        if key_remote in _MARKET:
            lo, hi = _MARKET[key_remote]
            return {
                "estimated": f"~${lo//1000}k–${hi//1000}k/yr (est.)",
                "usd_low": lo, "usd_high": hi,
                "confidence": "low", "method": "market_estimate"
            }

    return {"estimated": None, "usd_low": None, "usd_high": None,
            "confidence": "unknown", "method": "unknown"}

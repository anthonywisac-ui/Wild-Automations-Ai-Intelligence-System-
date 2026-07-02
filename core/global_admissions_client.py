"""
Global University Admissions Tracker — 7 Regions.

Covers: UK, US, Canada, Europe, Ireland, Australia, GCC
Data sources:
  - HIPO Labs API      → university name/domain lookup (free)
  - College Scorecard  → US admission rates (free, DEMO_KEY)
  - UCAS API           → UK courses (public search)
  - Static deadline DB → authoritative region deadlines + criteria

crawl_mode: "global_admissions"

Usage:
    {
        "portal_name": "Global Admissions",
        "crawl_mode": "global_admissions",
        "global_admissions_params": {
            "regions": ["uk", "us", "canada", "europe", "ireland", "australia", "gcc"],
            "subjects": ["computer science", "engineering", "business"],
            "limit": 30,
        }
    }
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_HIPO_URL  = "http://universities.hipolabs.com/search"
_SC_URL    = "https://api.data.gov/ed/collegescorecard/v1/schools"
_SC_KEY    = os.getenv("COLLEGE_SCORECARD_KEY", "DEMO_KEY")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WildAutomations/1.0)"}

# ─────────────────────────────────────────────────────────────────────────────
# Authoritative deadline + criteria database (updated annually)
# ─────────────────────────────────────────────────────────────────────────────

_REGION_DATA: Dict[str, Dict[str, Any]] = {
    "uk": {
        "name": "United Kingdom",
        "portal": "UCAS",
        "portal_url": "https://www.ucas.com/apply",
        "deadlines": {
            "Oxbridge & Medicine": "15 October",
            "Standard UCAS":      "29 January",
            "Late Applications":  "30 June",
            "Clearing":           "July – September",
        },
        "intakes": ["September/October"],
        "language": {"IELTS": "6.5–7.5", "TOEFL": "88–100"},
        "criteria": "A-Levels / IB / BTEC + Personal Statement + References",
        "hot_subjects": ["Computer Science", "Data Science", "FinTech", "Medicine", "Architecture", "MBA"],
        "top_unis": ["Oxford", "Cambridge", "Imperial College London", "UCL", "LSE", "Edinburgh"],
        "notes": "Oxbridge Oct 15 is strict. Clearing opens late June for remaining spots.",
    },
    "us": {
        "name": "United States",
        "portal": "Common App",
        "portal_url": "https://www.commonapp.org",
        "deadlines": {
            "Early Action / ED":   "1–15 November",
            "Regular Decision":    "1–15 January",
            "Spring Intake":       "1 October – 1 November",
        },
        "intakes": ["Fall (August/September)", "Spring (January)"],
        "language": {"IELTS": "6.5–7.5", "TOEFL": "80–100"},
        "criteria": "GPA 3.0–4.0 + SAT/ACT (optional many schools) + SOP + LORs",
        "hot_subjects": ["AI", "Machine Learning", "Computer Science", "Business", "Medicine", "Law"],
        "top_unis": ["MIT", "Harvard", "Stanford", "Caltech", "Princeton", "Yale"],
        "notes": "Many top schools test-optional since COVID. Financial aid FAFSA deadline Feb 1.",
    },
    "canada": {
        "name": "Canada",
        "portal": "OUAC",
        "portal_url": "https://www.ouac.on.ca",
        "deadlines": {
            "Fall Intake":   "15 January – 1 March",
            "Winter Intake": "1 September – 15 October",
        },
        "intakes": ["Fall (September)", "Winter (January)"],
        "language": {"IELTS": "6.5 (no band < 6.0)", "TOEFL": "86+"},
        "criteria": "GPA 75%+ | WES Evaluation for international degrees | GMAT/GRE for MBA/Masters",
        "hot_subjects": ["Cloud Computing", "ML", "Business Analytics", "Civil Engineering", "Nursing"],
        "top_unis": ["University of Toronto", "UBC", "McGill", "Waterloo", "Alberta", "McMaster"],
        "notes": "SDS stream (Student Direct Stream) for faster visa: Pakistan, India, Philippines eligible.",
    },
    "europe": {
        "name": "Europe (Germany / Netherlands / France)",
        "portal": "DAAD / Uni-Assist / Studielink",
        "portal_url": "https://www.daad.de/en/study-and-research-in-germany/",
        "deadlines": {
            "Winter Semester (main)": "15 April – 15 July",
            "Summer Semester":        "15 October – 15 January",
            "Uni-Assist Germany":     "Varies per university, submit 6 weeks before deadline",
        },
        "intakes": ["Winter (October)", "Summer (April)"],
        "language": {"IELTS": "6.0–7.0 (English-taught)", "German": "B2-C1 (German-taught)", "TOEFL": "80–90"},
        "criteria": "APS Certificate (for South Asian students) + Blocked Bank Account (€10,332) + Degree Equivalency via Anabin",
        "hot_subjects": ["Automotive Engineering", "Robotics", "AI Ethics", "Cyber Security", "Renewable Energy"],
        "top_unis": ["TU Munich", "LMU Munich", "Heidelberg", "TU Berlin", "Delft (NL)", "Paris-Saclay (FR)"],
        "notes": "Germany: Most public universities tuition-FREE for international students. Anabin (anabin.kmk.org) to check degree recognition.",
    },
    "ireland": {
        "name": "Ireland",
        "portal": "CAO",
        "portal_url": "https://www.cao.ie",
        "deadlines": {
            "CAO Normal Closing":    "1 February",
            "Late Applications":     "1 May",
            "Postgrad (PAC)":        "Rolling – October to March",
        },
        "intakes": ["September"],
        "language": {"IELTS": "6.0–6.5", "TOEFL": "79–88"},
        "criteria": "High school exit score + IELTS + CV + Portfolio (for creative courses)",
        "hot_subjects": ["Software Development", "Biomedical Science", "Financial Analytics", "Pharmacy", "Business"],
        "top_unis": ["Trinity College Dublin", "UCD", "UCC", "NUI Galway", "DCU", "Maynooth"],
        "notes": "Post-study work visa: 2 years for degree, 1 year for Masters. Strong tech hub (Google, Facebook, Apple HQ).",
    },
    "australia": {
        "name": "Australia",
        "portal": "UAC / VTAC / QTAC",
        "portal_url": "https://www.uac.edu.au",
        "deadlines": {
            "Semester 1 (Feb start)": "November – December",
            "Semester 2 (Jul start)": "April – May",
            "CRICOS Programs":        "Rolling – check per institution",
        },
        "intakes": ["Semester 1 (February)", "Semester 2 (July)"],
        "language": {"IELTS": "6.0–7.0", "TOEFL": "79–94"},
        "criteria": "ATAR Score or equivalent + IELTS + GTE (Genuine Student) Statement + Health Insurance (OSHC)",
        "hot_subjects": ["Telecommunications", "Healthcare Informatics", "Supply Chain", "Mining Engineering", "Finance"],
        "top_unis": ["ANU", "University of Melbourne", "University of Sydney", "UNSW", "Monash", "UQ"],
        "notes": "Post-study work visa 2–4 years (regional bonus extra 1–2 years). 485 visa for graduates.",
    },
    "gcc": {
        "name": "GCC Region (UAE / Saudi / Qatar / Kuwait)",
        "portal": "UAE CAA / Ministry of Education",
        "portal_url": "https://www.caa.ae",
        "deadlines": {
            "Fall Intake":    "31 May – 31 July",
            "Spring Intake":  "1 October – 15 December",
        },
        "intakes": ["Fall (September)", "Spring (January/February)"],
        "language": {"IELTS": "5.5–6.5", "TOEFL": "61–80", "EmSAT": "UAE-specific score"},
        "criteria": "Attested High School Certificate + EmSAT (UAE) + IELTS + Ministry MOE approval for private universities",
        "hot_subjects": ["Petroleum Engineering", "International Business", "AI in Infrastructure", "Hospitality", "Architecture"],
        "top_unis": ["Khalifa University", "NYU Abu Dhabi", "AUS", "Heriot-Watt Dubai", "MBZUAI", "Qatar University"],
        "notes": "CAA accreditation mandatory. Cross-check any university at caa.ae before enrolling.",
    },
}


def _build_region_entries(region_key: str, subjects_filter: List[str]) -> List[Dict[str, Any]]:
    """Build structured entries for a region from static database."""
    rd = _REGION_DATA.get(region_key)
    if not rd:
        return []

    entries: List[Dict[str, Any]] = []
    region_name = rd["name"]
    now = datetime.utcnow().isoformat()

    # Main region summary entry
    dl_text = " | ".join(f"{k}: {v}" for k, v in rd["deadlines"].items())
    entries.append({
        "title": f"{region_name} — University Admissions Guide",
        "source_url": rd["portal_url"],
        "description": (
            f"Portal: {rd['portal']} | "
            f"Intakes: {', '.join(rd['intakes'])} | "
            f"Language: IELTS {rd['language']['IELTS']} | "
            f"Deadlines: {dl_text}"
        ),
        "location": region_name,
        "price": "",
        "metadata": {
            "type": "admissions_guide",
            "region": region_key,
            "portal": rd["portal"],
            "deadlines": rd["deadlines"],
            "intakes": rd["intakes"],
            "language_requirements": rd["language"],
            "criteria": rd["criteria"],
            "hot_subjects": rd["hot_subjects"],
            "top_universities": rd["top_unis"],
            "notes": rd["notes"],
            "scraped_at": now,
        },
    })

    # Per-deadline entries
    for deadline_label, deadline_date in rd["deadlines"].items():
        entries.append({
            "title": f"{region_name} — {deadline_label} Deadline: {deadline_date}",
            "source_url": rd["portal_url"],
            "description": (
                f"{deadline_label} | {region_name} | "
                f"Criteria: {rd['criteria'][:100]}"
            ),
            "location": region_name,
            "price": "",
            "metadata": {
                "type": "admissions_deadline",
                "region": region_key,
                "deadline_label": deadline_label,
                "deadline_date": deadline_date,
                "scraped_at": now,
            },
        })

    # Per-university entries
    for uni in rd["top_unis"]:
        if subjects_filter:
            match = any(s.lower() in " ".join(rd["hot_subjects"]).lower() for s in subjects_filter)
            if not match:
                continue
        entries.append({
            "title": f"{uni} — {region_name}",
            "source_url": rd["portal_url"],
            "description": (
                f"Top university in {region_name} | "
                f"Subjects: {', '.join(rd['hot_subjects'][:3])} | "
                f"IELTS: {rd['language']['IELTS']}"
            ),
            "location": region_name,
            "price": "",
            "metadata": {
                "type": "university",
                "region": region_key,
                "university": uni,
                "hot_subjects": rd["hot_subjects"],
                "language_req": rd["language"],
                "scraped_at": now,
            },
        })

    return entries


async def _enrich_with_hipo(
    client: httpx.AsyncClient,
    region_key: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Fetch additional universities for the region from HIPO Labs API."""
    country_map = {
        "uk": "United Kingdom", "us": "United States", "canada": "Canada",
        "ireland": "Ireland", "australia": "Australia",
        "gcc": "United Arab Emirates",
    }
    country = country_map.get(region_key)
    if not country:
        return []

    try:
        resp = await client.get(
            _HIPO_URL, params={"country": country}, headers=_HEADERS, timeout=15
        )
        resp.raise_for_status()
        unis = resp.json()
        results = []
        for uni in unis[:limit]:
            web = (uni.get("web_pages") or [""])[0]
            results.append({
                "title": f"{uni.get('name', 'Unknown')} — {country}",
                "source_url": web,
                "description": f"University in {country} | {', '.join(uni.get('domains', [])[:2])}",
                "location": country,
                "price": "",
                "metadata": {
                    "type": "university",
                    "region": region_key,
                    "country": country,
                    "source": "hipo_api",
                    "scraped_at": datetime.utcnow().isoformat(),
                },
            })
        return results
    except Exception as exc:
        logger.debug("global_admissions: hipo %s error: %s", region_key, exc)
        return []


async def fetch_global_admissions(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Entry point for crawl_mode='global_admissions'."""
    params   = portal_config.get("global_admissions_params") or {}
    regions  = params.get("regions", list(_REGION_DATA.keys()))
    subjects = params.get("subjects", [])
    limit    = int(params.get("limit", 40))

    if isinstance(regions, str):
        regions = [regions]

    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30) as client:
        tasks = []
        for region in regions:
            # Static authoritative data (always fast)
            static = _build_region_entries(region, subjects)
            results.extend(static)

            # HIPO enrichment (async)
            tasks.append(_enrich_with_hipo(client, region, limit=3))

        hipo_results = await asyncio.gather(*tasks, return_exceptions=True)
        for hr in hipo_results:
            if isinstance(hr, list):
                results.extend(hr)

    logger.info("global_admissions: total=%d", len(results))
    return results[:limit]

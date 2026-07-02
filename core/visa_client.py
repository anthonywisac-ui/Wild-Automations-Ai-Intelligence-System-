"""
Visa Scraper Client — integrates GitHub visa scrapers directly (no Apify).

Sources (from scrapers-info.md):
  - DavidBellamy/visa_dates       → US Visa Bulletin (travel.state.gov)
  - btran12/visa-bulletin         → US Visa Bulletin monthly dates
  - kellywaldro/processing-times  → Canada PR processing times (IRCC)
  - vinaygopinath/visa-req-wiki-scraper → Wikipedia global visa requirements

crawl_mode: "visa_bulletin"  → US + Canada visa data
crawl_mode: "visa_wiki"      → Wikipedia global visa requirements

Usage (set in portal_config):
    {
        "portal_name": "US Visa Bulletin",
        "crawl_mode": "visa_bulletin",
        "visa_params": {
            "source": "us_bulletin",   # or "canada_pr" or "both"
        }
    }
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# US Visa Bulletin  (DavidBellamy/visa_dates + btran12/visa-bulletin logic)
# Source: travel.state.gov
# ─────────────────────────────────────────────────────────────────────────────

_US_BULLETIN_URL = "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html"
_BULLETIN_LINK_RE = re.compile(r'/content/travel/en/legal/visa-law0/visa-bulletin/\d{4}/visa-bulletin-for-\w+-\d{4}\.html', re.I)


async def _fetch_us_visa_bulletin(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch latest US Visa Bulletin page links and extract cutoff date table."""
    try:
        resp = await client.get(_US_BULLETIN_URL, timeout=20)
        resp.raise_for_status()
        html = resp.text

        # Find the most recent bulletin link
        links = _BULLETIN_LINK_RE.findall(html)
        if not links:
            logger.warning("visa_client: no bulletin links found on travel.state.gov")
            return []

        latest_link = "https://travel.state.gov" + links[0]
        resp2 = await client.get(latest_link, timeout=20)
        resp2.raise_for_status()

        # Extract priority date tables (simple text extraction)
        content = resp2.text
        # Find month/year in title
        month_match = re.search(r'visa-bulletin-for-(\w+-\d{4})', latest_link, re.I)
        bulletin_period = month_match.group(1).replace('-', ' ').title() if month_match else "Latest"

        # Extract table rows with priority dates (EB/FB categories)
        rows = re.findall(r'<td[^>]*>\s*([A-Z]{1,2}\s*-?\s*\d+[A-Z]?)\s*</td>', content)
        dates = re.findall(r'(\d{2}[A-Z]{3}\d{2}|C|U)', content)

        results = [{
            "title": f"US Visa Bulletin — {bulletin_period}",
            "source_url": latest_link,
            "description": f"US employment/family-based visa priority dates. {len(dates)} date entries found.",
            "location": "United States",
            "price": "",
            "metadata": {
                "type": "visa_bulletin",
                "country": "US",
                "period": bulletin_period,
                "bulletin_url": latest_link,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        }]
        logger.info("visa_client: US bulletin fetched period=%s", bulletin_period)
        return results

    except Exception as exc:
        logger.error("visa_client: US bulletin error: %s", exc)
        return _us_bulletin_fallback()


# ─────────────────────────────────────────────────────────────────────────────
# Canada PR Processing Times  (kellywaldro/processing-times logic)
# Source: ircc.canada.ca
# ─────────────────────────────────────────────────────────────────────────────

_CANADA_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/check-processing-times.html"


async def _fetch_canada_processing_times(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch Canada PR processing times from IRCC page."""
    try:
        resp = await client.get(_CANADA_URL, timeout=20, headers={"Accept-Language": "en-CA,en;q=0.9"})
        resp.raise_for_status()
        html = resp.text

        # Extract processing time entries from text
        times = re.findall(r'(\d+)\s+(?:to\s+(\d+)\s+)?months?', html, re.I)
        entries = []
        for match in times[:10]:  # top 10
            lo, hi = match
            time_str = f"{lo}–{hi} months" if hi else f"{lo} months"
            entries.append({
                "title": f"Canada PR Processing Time: {time_str}",
                "source_url": _CANADA_URL,
                "description": f"Canada immigration processing time: {time_str}. Check IRCC for latest updates.",
                "location": "Canada",
                "price": "",
                "metadata": {
                    "type": "processing_time",
                    "country": "Canada",
                    "time_range": time_str,
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            })

        if not entries:
            entries = [{
                "title": "Canada PR Processing Times",
                "source_url": _CANADA_URL,
                "description": "Canada immigration processing times — check IRCC portal for current data.",
                "location": "Canada",
                "price": "",
                "metadata": {"type": "processing_time", "country": "Canada"}
            }]

        logger.info("visa_client: Canada times fetched entries=%d", len(entries))
        return entries

    except Exception as exc:
        logger.error("visa_client: Canada processing times error: %s", exc)
        return _canada_fallback()


# ─────────────────────────────────────────────────────────────────────────────
# Wikipedia Visa Requirements  (vinaygopinath/visa-req-wiki-scraper logic)
# ─────────────────────────────────────────────────────────────────────────────

_WIKI_BASE = "https://en.wikipedia.org/wiki/Visa_requirements_for_{}_citizens"

_COMMON_PASSPORTS = [
    ("pakistani", "Pakistani"),
    ("indian", "Indian"),
    ("emirati", "UAE"),
    ("saudi_arabian", "Saudi"),
]


_PASSPORT_CSV_URL = "https://raw.githubusercontent.com/ilyankou/passport-index-dataset/master/passport-index-tidy.csv"

# Fallback known passport strengths (visa-free count) from Henley Index 2024
_PASSPORT_FALLBACK = {
    "pakistani": {"visa_free": 33, "voa": 42, "rank": 101},
    "indian": {"visa_free": 58, "voa": 42, "rank": 82},
    "emirati": {"visa_free": 185, "voa": 0, "rank": 11},
    "saudi arabian": {"visa_free": 87, "voa": 57, "rank": 60},
    "bangladeshi": {"visa_free": 40, "voa": 43, "rank": 99},
    "british": {"visa_free": 190, "voa": 4, "rank": 4},
    "american": {"visa_free": 186, "voa": 4, "rank": 7},
}


async def _fetch_wiki_visa_requirements(
    client: httpx.AsyncClient,
    passports: List[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch visa requirements using Passport Index CSV (GitHub).
    Wikipedia visa pages return 403. CSV is public and always accessible.
    """
    targets = passports or ["pakistani", "indian"]
    results = []

    # Try to load passport CSV for accurate counts
    csv_data: dict = {}
    try:
        resp = await client.get(_PASSPORT_CSV_URL, timeout=20)
        if resp.status_code == 200:
            import csv, io
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                passport_name = (row.get("Passport") or "").strip().lower()
                requirement = (row.get("Requirement") or "").strip()
                if passport_name not in csv_data:
                    csv_data[passport_name] = {"VF": 0, "VOA": 0, "ETA": 0, "VR": 0, "total": 0}
                csv_data[passport_name]["total"] += 1
                if requirement in ("VF", "visa free", "Visa Free"):
                    csv_data[passport_name]["VF"] += 1
                elif requirement in ("VOA", "visa on arrival"):
                    csv_data[passport_name]["VOA"] += 1
                elif requirement == "ETA":
                    csv_data[passport_name]["ETA"] += 1
                else:
                    csv_data[passport_name]["VR"] += 1
    except Exception as exc:
        logger.warning("visa_client: csv load error: %s — using fallback", exc)

    for passport in targets:
        label = passport.replace("_", " ").title()
        passport_key = passport.lower().replace("_", " ")

        if passport_key in csv_data:
            d = csv_data[passport_key]
            vf = d["VF"]
            voa = d["VOA"] + d["ETA"]
            vr = d["VR"]
            source = "passport_index_csv"
        else:
            fb = _PASSPORT_FALLBACK.get(passport_key, {"visa_free": 0, "voa": 0, "rank": 0})
            vf = fb["visa_free"]
            voa = fb["voa"]
            vr = 0
            source = "henley_index_2024_static"

        wiki_url = _WIKI_BASE.format(passport.replace(" ", "_"))
        results.append({
            "title": f"Visa Requirements — {label} Passport",
            "source_url": wiki_url,
            "description": (
                f"{label} passport: {vf} visa-free destinations, "
                f"{voa} visa-on-arrival/ETA, {vr} visa required."
            ),
            "location": "Global",
            "price": "",
            "metadata": {
                "type": "visa_requirements",
                "passport": label,
                "visa_free": vf,
                "visa_on_arrival": voa,
                "visa_required": vr,
                "data_source": source,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        })
        logger.info("visa_client: wiki/csv passport=%s vf=%d voa=%d", label, vf, voa)

    return results


def _us_bulletin_fallback() -> List[Dict[str, Any]]:
    now = datetime.utcnow().isoformat()
    categories = [
        ("EB-1 Worldwide", "C", "Current — all countries priority"),
        ("EB-2 India", "01JAN15", "Employment-based 2nd preference — India"),
        ("EB-2 China", "01JUN19", "Employment-based 2nd preference — China"),
        ("EB-3 Philippines", "01JAN20", "Employment-based 3rd preference — Philippines"),
        ("EB-3 Worldwide", "01JAN22", "Employment-based 3rd preference — Worldwide"),
        ("FB-1 Mexico", "22MAR00", "Family-based 1st preference — Mexico"),
        ("F2A Worldwide", "01AUG22", "Family-based 2A — Worldwide"),
    ]
    return [{"title":f"US Visa Bulletin — {c}","source_url":"https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html",
             "description":f"Priority date: {d} | {desc} (cached fallback Jun 2025)","location":"United States","price":"",
             "metadata":{"type":"visa_bulletin","country":"US","category":c,"priority_date":d,"scraped_at":now}}
            for c,d,desc in categories]


def _canada_fallback() -> List[Dict[str, Any]]:
    now = datetime.utcnow().isoformat()
    programs = [
        ("Express Entry (FSW)", "3–5 months"), ("Canadian Experience Class", "3–4 months"),
        ("Provincial Nominee Program", "19–24 months"), ("Spousal Sponsorship", "12–18 months"),
        ("Study Permit", "8–16 weeks"), ("Visitor Visa (TRV)", "14–60 days"),
    ]
    return [{"title":f"Canada {prog} Processing Time: {time}","source_url":"https://www.canada.ca/en/immigration-refugees-citizenship/services/application/check-processing-times.html",
             "description":f"IRCC estimated processing time for {prog}: {time} (cached fallback 2025)","location":"Canada","price":"",
             "metadata":{"type":"processing_time","country":"Canada","program":prog,"time_range":time,"scraped_at":now}}
            for prog,time in programs]


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_visa_data(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Main entry point called by SmartScraperEngine for crawl_mode="visa_bulletin" or "visa_wiki".

    portal_config keys:
        crawl_mode: "visa_bulletin" | "visa_wiki"
        visa_params:
            source: "us_bulletin" | "canada_pr" | "both"  (for visa_bulletin)
            passports: ["pakistani", "indian", ...]        (for visa_wiki)
    """
    params = portal_config.get("visa_params") or {}
    mode = portal_config.get("crawl_mode", "visa_bulletin")

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30) as client:
        if mode == "visa_wiki":
            passports = params.get("passports", ["pakistani", "indian"])
            return await _fetch_wiki_visa_requirements(client, passports)

        # Default: visa_bulletin
        source = params.get("source", "both")
        results = []

        if source in ("us_bulletin", "both"):
            results += await _fetch_us_visa_bulletin(client)

        if source in ("canada_pr", "both"):
            results += await _fetch_canada_processing_times(client)

        return results

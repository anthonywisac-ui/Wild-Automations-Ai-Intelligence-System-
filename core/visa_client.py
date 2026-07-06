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

        now = datetime.utcnow().isoformat()
        results = [{
            "title": f"US Visa Bulletin — {bulletin_period}",
            "source_url": latest_link,
            "description": "US employment/family-based visa priority dates (Final Action Dates).",
            "location": "United States",
            "price": "",
            "metadata": {
                "type": "visa_bulletin",
                "country": "US",
                "period": bulletin_period,
                "bulletin_url": latest_link,
                "scraped_at": now,
            }
        }]
        # Structured per-category records: parse each table into
        # category (row head) x country (column head) -> cutoff date cells.
        results += _parse_bulletin_tables(content, bulletin_period, latest_link, now)
        logger.info("visa_client: US bulletin fetched period=%s records=%d",
                    bulletin_period, len(results))
        return results

    except Exception as exc:
        logger.error("visa_client: US bulletin error: %s", exc)
        return _us_bulletin_fallback()


def _parse_bulletin_tables(html: str, period: str, url: str,
                           now: str) -> List[Dict[str, Any]]:
    """Parse bulletin HTML tables into per-category/per-country cutoff records.
    Fail-soft: any parse problem just yields fewer records."""
    records: List[Dict[str, Any]] = []
    try:
        import html as _html
        cell_re = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL | re.I)
        strip = lambda c: re.sub(
            r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
        date_re = re.compile(r"^(\d{2}[A-Z]{3}\d{2}|C|U)$")

        for table in re.findall(r"<table[^>]*>(.*?)</table>", html, re.DOTALL | re.I):
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.DOTALL | re.I)
            if len(rows) < 2:
                continue
            headers = [strip(c) for c in cell_re.findall(rows[0])]
            if len(headers) < 2:
                continue
            countries = headers[1:]
            for row in rows[1:]:
                cells = [strip(c) for c in cell_re.findall(row)]
                if len(cells) < 2:
                    continue
                category = cells[0][:60]
                if not category:
                    continue
                for country, value in zip(countries, cells[1:]):
                    if not date_re.match(value):
                        continue
                    label = {"C": "Current", "U": "Unavailable"}.get(value, value)
                    records.append({
                        "title": f"US Visa Bulletin {period} — {category} · {country[:40]}",
                        "source_url": url,
                        "description": (f"Final action date for {category} "
                                        f"({country[:40]}): {label}"),
                        "location": "United States",
                        "price": "",
                        "metadata": {
                            "type": "visa_bulletin_entry", "country": "US",
                            "period": period, "category": category,
                            "chargeability": country[:40], "cutoff": value,
                            "current": value == "C", "scraped_at": now,
                        },
                    })
        # keep it digestible — bulletin has hundreds of cells
        return records[:60]
    except Exception as exc:
        logger.warning("visa_client: bulletin table parse failed: %s", exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Canada PR Processing Times — IRCC official JSON first, HTML regex fallback
# ─────────────────────────────────────────────────────────────────────────────

_CANADA_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/check-processing-times.html"
_IRCC_JSON_URL = "https://www.canada.ca/content/dam/ircc/documents/json/data-ptime-en.json"

_TIME_VALUE_RE = re.compile(r"\d+\s*(?:day|week|month|year)s?", re.I)


def _walk_ircc_json(node: Any, path: List[str], out: List[tuple]) -> None:
    """Recursively collect (label-path, human time string) pairs from IRCC's
    processing-times JSON — schema-agnostic so IRCC layout changes don't break us."""
    if isinstance(node, dict):
        for k, v in node.items():
            _walk_ircc_json(v, path + [str(k)], out)
    elif isinstance(node, list):
        for v in node:
            _walk_ircc_json(v, path, out)
    elif isinstance(node, str) and _TIME_VALUE_RE.search(node):
        label = " · ".join(p.replace("_", " ").replace("-", " ").title()
                           for p in path[-2:] if p and not p.isdigit())
        if label:
            out.append((label, node.strip()))


async def _fetch_canada_processing_times(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Canada processing times — official IRCC JSON, then HTML, then static."""
    now = datetime.utcnow().isoformat()
    # 1) official JSON the IRCC widget itself uses
    try:
        resp = await client.get(_IRCC_JSON_URL, timeout=20,
                                headers={"Accept": "application/json"})
        resp.raise_for_status()
        pairs: List[tuple] = []
        _walk_ircc_json(resp.json(), [], pairs)
        # dedup by label, keep first
        seen: Dict[str, str] = {}
        for label, val in pairs:
            seen.setdefault(label, val)
        entries = [{
            "title": f"Canada Processing Time — {label}: {val}",
            "source_url": _CANADA_URL,
            "description": f"IRCC official processing time for {label}: {val}.",
            "location": "Canada",
            "price": "",
            "metadata": {"type": "processing_time", "country": "Canada",
                         "program": label, "time_range": val,
                         "data_source": "ircc_json", "scraped_at": now},
        } for label, val in list(seen.items())[:25]]
        if entries:
            logger.info("visa_client: Canada IRCC JSON entries=%d", len(entries))
            return entries
    except Exception as exc:
        logger.warning("visa_client: IRCC JSON failed: %s — trying HTML", exc)

    # 2) HTML page regex (legacy path)
    try:
        resp = await client.get(_CANADA_URL, timeout=20,
                                headers={"Accept-Language": "en-CA,en;q=0.9"})
        resp.raise_for_status()
        times = re.findall(r'(\d+)\s+(?:to\s+(\d+)\s+)?months?', resp.text, re.I)
        entries = []
        for lo, hi in times[:10]:
            time_str = f"{lo}–{hi} months" if hi else f"{lo} months"
            entries.append({
                "title": f"Canada PR Processing Time: {time_str}",
                "source_url": _CANADA_URL,
                "description": f"Canada immigration processing time: {time_str}. "
                               "Check IRCC for latest updates.",
                "location": "Canada", "price": "",
                "metadata": {"type": "processing_time", "country": "Canada",
                             "time_range": time_str, "data_source": "ircc_html",
                             "scraped_at": now},
            })
        if entries:
            logger.info("visa_client: Canada HTML entries=%d", len(entries))
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

    # CSV rows are COUNTRY names ("Pakistan"); configs pass adjectives
    # ("pakistani") — map adjective -> country so lookups actually hit.
    _ADJ_TO_COUNTRY = {
        "pakistani": "pakistan", "indian": "india", "emirati": "united arab emirates",
        "saudi arabian": "saudi arabia", "saudi": "saudi arabia",
        "bangladeshi": "bangladesh", "british": "united kingdom",
        "american": "united states", "filipino": "philippines",
        "nigerian": "nigeria", "egyptian": "egypt", "nepali": "nepal",
        "sri lankan": "sri lanka", "chinese": "china", "canadian": "canada",
    }

    # Try to load passport CSV for accurate counts
    csv_data: dict = {}
    try:
        resp = await client.get(_PASSPORT_CSV_URL, timeout=20)
        if resp.status_code == 200:
            import csv, io
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                passport_name = (row.get("Passport") or "").strip().lower()
                req = (row.get("Requirement") or "").strip().lower()
                if passport_name not in csv_data:
                    csv_data[passport_name] = {"VF": 0, "VOA": 0, "ETA": 0, "VR": 0, "total": 0}
                csv_data[passport_name]["total"] += 1
                # tidy-CSV values: number of visa-free days ("90"), "visa free",
                # "visa on arrival", "e-visa", "eta", "visa required", "no admission"
                if req.isdigit() or "visa free" in req or req == "vf":
                    csv_data[passport_name]["VF"] += 1
                elif "arrival" in req or req == "voa":
                    csv_data[passport_name]["VOA"] += 1
                elif "e-visa" in req or "eta" in req or "evisa" in req:
                    csv_data[passport_name]["ETA"] += 1
                else:
                    csv_data[passport_name]["VR"] += 1
    except Exception as exc:
        logger.warning("visa_client: csv load error: %s — using fallback", exc)

    for passport in targets:
        label = passport.replace("_", " ").title()
        adj_key = passport.lower().replace("_", " ")
        passport_key = _ADJ_TO_COUNTRY.get(adj_key, adj_key)

        if passport_key in csv_data:
            d = csv_data[passport_key]
            vf = d["VF"]
            voa = d["VOA"] + d["ETA"]
            vr = d["VR"]
            source = "passport_index_csv"
        else:
            fb = _PASSPORT_FALLBACK.get(adj_key, {"visa_free": 0, "voa": 0, "rank": 0})
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

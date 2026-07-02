"""
Data Enrichment Engine — inserted between Search Planner and Entity Resolution.

For each raw business lead it collects the operational + digital signals that the
Evidence Graph and Recommendation Engine need but the scraper cannot provide:

    website · phone · whatsapp · email · social profiles (linkedin/instagram/
    facebook/tiktok/youtube) · tech stack · Meta Pixel · Google Analytics/GTM ·
    booking system · forms · chatbot · basic SEO signals · hiring activity ·
    ads detectability · derived operational pain signals.

Deterministic and fast: website discovery via DuckDuckGo HTML, homepage fetched
with httpx (no browser), parsed with selectolax/regex. Fail-soft — a lead that
can't be enriched simply carries fewer signals. Framework-agnostic.

Enrichment is additive: it writes `metadata.enrichment` (full detail) and lifts
key fields (phone/email/website/whatsapp/…) to metadata for existing consumers.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}

# Directory/aggregator/social hosts that are NOT a business's own website.
_NON_WEBSITE = ("google.", "facebook.", "instagram.", "tripadvisor.", "yelp.",
                "justdial.", "yellowpages", "linkedin.", "youtube.", "tiktok.",
                "zomato.", "talabat.", "maps.", "bing.", "duckduckgo.", "wikipedia.")

_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().\-]{7,}\d)")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_SOCIAL_RE = {
    "linkedin": re.compile(r"https?://(?:[a-z]+\.)?linkedin\.com/[^\"'\s>]+", re.I),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[^\"'\s>]+", re.I),
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[^\"'\s>]+", re.I),
    "tiktok": re.compile(r"https?://(?:www\.)?tiktok\.com/[^\"'\s>]+", re.I),
    "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/[^\"'\s>]+", re.I),
}


def _clean_host(url: str) -> str:
    return re.sub(r"^https?://", "", (url or "")).strip("/").lower().split("/")[0]


def _is_business_site(host: str) -> bool:
    return bool(host) and "." in host and not any(b in host for b in _NON_WEBSITE)


async def _provider_maps(name, location, md) -> Optional[Dict[str, Any]]:
    """Highest confidence: the scraper already carries the official Maps website."""
    w = md.get("website") or (md.get("place") or {}).get("website")
    if w and _is_business_site(_clean_host(w)):
        return {"url": w if w.startswith("http") else "https://" + w,
                "source": "google_maps", "confidence": 0.98}
    return None


async def _provider_bing(name, location, md) -> Optional[Dict[str, Any]]:
    q = f"{name} {location}".strip().replace(" ", "+")
    try:
        async with httpx.AsyncClient(timeout=10, verify=False, headers=_HEADERS,
                                     follow_redirects=True) as c:
            r = await c.get(f"https://www.bing.com/search?q={q}")
            for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>', r.text):
                host = _clean_host(m.group(1))
                if _is_business_site(host):
                    return {"url": "https://" + host, "source": "bing", "confidence": 0.85}
    except Exception as exc:
        logger.debug("enrichment: bing failed for %s: %s", name, exc)
    return None


async def _provider_ddg(name, location, md) -> Optional[Dict[str, Any]]:
    q = f"{name} {location}".strip().replace(" ", "+")
    try:
        async with httpx.AsyncClient(timeout=10, verify=False, headers=_HEADERS,
                                     follow_redirects=True) as c:
            r = await c.get(f"https://html.duckduckgo.com/html/?q={q}")
            for raw in re.findall(r'class="result__url"[^>]*>\s*([^<]+?)\s*<', r.text):
                host = raw.strip().strip("/").lower().split("/")[0]
                if _is_business_site(host):
                    return {"url": "https://" + host, "source": "duckduckgo", "confidence": 0.8}
    except Exception as exc:
        logger.debug("enrichment: ddg failed for %s: %s", name, exc)
    return None


async def _provider_llm(name, location, md) -> Optional[Dict[str, Any]]:
    """Lowest confidence: infer the likely official domain (unverified)."""
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return None
        out = (await llm.complete(
            f"What is the official website domain of the business '{name}' in {location}? "
            "Reply with ONLY the domain (e.g. example.com) or 'unknown'.",
            max_tokens=20, temperature=0.0)).strip().lower()
        host = _clean_host(out)
        if _is_business_site(host) and "unknown" not in host:
            return {"url": "https://" + host, "source": "llm_inference", "confidence": 0.4}
    except Exception:
        pass
    return None


_DISCOVERY_CHAIN = [_provider_maps, _provider_bing, _provider_ddg, _provider_llm]


async def _discover_candidate(name: str, location: str, md: Dict[str, Any]) -> Dict[str, Any]:
    """Provider chain → best website candidate with source + confidence."""
    if not name:
        return {"url": None, "source": None, "confidence": 0.0}
    for provider in _DISCOVERY_CHAIN:
        try:
            res = await provider(name, location, md)
            if res and res.get("url"):
                return res
        except Exception:
            continue
    return {"url": None, "source": None, "confidence": 0.0}


def _analyze_html(url: str, html: str) -> Dict[str, Any]:
    """Extract contact + tech + social + SEO + hiring signals from homepage HTML."""
    low = html.lower()

    phone = None
    tm = re.search(r'href="tel:([+\d][\d\s().\-]{6,})"', html)
    if tm:
        phone = tm.group(1).strip()
    else:
        for cand in _PHONE_RE.findall(html):
            digits = re.sub(r"\D", "", cand)
            # phones are 9-15 digits; reject 8-digit YYYYMMDD dates
            if 9 <= len(digits) <= 15 and not re.match(r"^(?:19|20)\d{6}$", digits):
                phone = cand.strip()
                break

    email = None
    em = re.search(r'href="mailto:([^"?]+)"', html)
    if em:
        email = em.group(1).strip()
    else:
        e2 = _EMAIL_RE.search(html)
        email = e2.group(0) if e2 else None

    whatsapp = bool(re.search(r"wa\.me/|api\.whatsapp\.com|whatsapp", low))

    socials: Dict[str, str] = {}
    for plat, rx in _SOCIAL_RE.items():
        m = rx.search(html)
        if m:
            socials[plat] = m.group(0).split("?")[0]

    tech = {
        "meta_pixel": bool(re.search(r"fbq\(|fbevents\.js|connect\.facebook\.net", low)),
        "google_analytics": bool(re.search(r"gtag\(|google-analytics\.com|analytics\.js|ga\(", low)),
        "gtm": bool(re.search(r"gtm-[a-z0-9]+|googletagmanager\.com/gtm", low)),
        "cms": next((c for c in ("shopify", "wordpress", "wix", "squarespace", "webflow",
                                 "godaddy", "duda") if c in low or f"{c}.com" in low), None),
    }
    tech["runs_ads"] = tech["meta_pixel"] or bool(re.search(r"googleadservices|gclid|adsystem", low))

    booking = next((b for b in ("calendly", "acuityscheduling", "opentable", "resy",
                                "setmore", "simplybook", "fresha", "booksy")
                    if b in low), None)
    booking = booking or ("book now" in low or "book online" in low or "book appointment" in low)
    chatbot = next((c for c in ("intercom", "tawk.to", "drift", "crisp", "zendesk",
                                "livechat", "tidio", "hubspot") if c in low), None)
    has_forms = "<form" in low
    hiring = bool(re.search(r"careers|we're hiring|we are hiring|join our team|/jobs|vacanc", low))

    seo = {
        "has_title": "<title" in low,
        "has_meta_desc": 'name="description"' in low,
        "has_h1": "<h1" in low,
        "https": url.startswith("https://"),
        "mobile_viewport": 'name="viewport"' in low,
    }

    return {
        "website": url, "phone": phone, "email": email, "whatsapp": whatsapp,
        "socials": socials, "tech": tech, "booking_system": booking,
        "has_forms": has_forms, "chatbot": chatbot, "seo": seo, "hiring": hiring,
        "runs_ads": tech["runs_ads"],
    }


def _pain_signals(enr: Dict[str, Any]) -> List[str]:
    """Derive operational/digital pain from what's MISSING."""
    pains = []
    if not enr.get("website"):
        pains.append("no website")
    else:
        seo = enr.get("seo") or {}
        if not enr.get("whatsapp"):
            pains.append("no whatsapp")
        if not enr.get("booking_system"):
            pains.append("no online booking")
        if not enr.get("chatbot"):
            pains.append("no chatbot")
        if not seo.get("mobile_viewport"):
            pains.append("not mobile-friendly")
        if not seo.get("has_meta_desc"):
            pains.append("weak seo")
        if not enr.get("socials"):
            pains.append("weak social presence")
        if not (enr.get("tech") or {}).get("meta_pixel"):
            pains.append("not running trackable ads")
    return pains


def _name_match(name: str, html: str) -> bool:
    toks = [t for t in re.findall(r"[a-z]+", (name or "").lower()) if len(t) > 3][:3]
    low = (html or "").lower()
    return bool(toks) and sum(1 for t in toks if t in low) >= max(1, len(toks) // 2)


def _build_provenance(enr: Dict[str, Any], md: Dict[str, Any],
                      disc: Dict[str, Any]) -> Dict[str, Any]:
    """Per-signal {source, confidence} — feeds evidence-node provenance + learning."""
    prov: Dict[str, Any] = {}
    tech = enr.get("tech") or {}
    from_maps_phone = bool(md.get("phone")) and md.get("phone") == enr.get("phone")
    if enr.get("website"):
        prov["website"] = {"source": disc.get("source"), "confidence": disc.get("confidence"),
                           "verification_status": enr.get("verification_status", "unverified")}
    if enr.get("phone"):
        prov["phone"] = {"source": "google_maps" if from_maps_phone else "website_html",
                         "confidence": 0.98 if from_maps_phone else 0.9}
    if enr.get("whatsapp"):
        prov["whatsapp"] = {"source": "website_html", "confidence": 0.92}
    if enr.get("email"):
        prov["email"] = {"source": "website_html", "confidence": 0.9}
    for plat in (enr.get("socials") or {}):
        prov[f"social_{plat}"] = {"source": "website", "confidence": 0.94}
    for k in ("meta_pixel", "google_analytics", "gtm"):
        if tech.get(k):
            prov[k] = {"source": "html", "confidence": 1.0}
    if tech.get("cms"):
        prov["cms"] = {"source": "html", "confidence": 0.95}
    if enr.get("booking_system"):
        prov["booking"] = {"source": "html", "confidence": 0.9}
    if enr.get("chatbot"):
        prov["chatbot"] = {"source": "html", "confidence": 0.95}
    if enr.get("hiring"):
        prov["hiring"] = {"source": "careers_page", "confidence": 0.95}
    return prov


async def enrich(record: Dict[str, Any], *, timeout: int = 12) -> Dict[str, Any]:
    """Enrich a business record: provider-chain discovery, verification, provenance,
    with cache (skip unchanged) + change detection. Never raises."""
    try:
        from core import enrichment_cache, change_detection
    except Exception:
        enrichment_cache = change_detection = None

    try:
        md = record.setdefault("metadata", {})
        name = md.get("company") or record.get("title") or ""
        location = record.get("location") or md.get("location") or ""
        key = enrichment_cache.business_key(name, location) if enrichment_cache else ""

        # 1. cache — skip crawl if fresh
        cached = enrichment_cache.get(key) if (enrichment_cache and key) else None
        if cached and not enrichment_cache.should_refresh(key):
            enr = cached.get("enrichment") or {}
            md["enrichment"] = enr
            _lift_fields(md, enr)
            md["enriched"] = True
            md["enrichment_cached"] = True
            return record

        # 2. provider-chain website discovery (source + confidence)
        disc = await asyncio.wait_for(_discover_candidate(name, location, md), timeout=timeout)

        # 3. fetch + analyze (single fetch also used for verification)
        html = ""
        enr: Dict[str, Any] = {"website": None}
        if disc.get("url"):
            try:
                async with httpx.AsyncClient(timeout=timeout, verify=False, headers=_HEADERS,
                                             follow_redirects=True) as c:
                    r = await c.get(disc["url"])
                    if r.status_code < 400 and r.text:
                        html = r.text[:400000]
                        enr = _analyze_html(str(r.url), html)
                        enr["verification_status"] = "verified" if _name_match(name, html) else "unverified"
            except Exception as exc:
                logger.debug("enrichment: fetch failed %s: %s", disc["url"], exc)
        enr["discovery"] = disc
        enr["pain_signals"] = _pain_signals(enr)
        enr["provenance"] = _build_provenance(enr, md, disc)

        # 4. change detection vs cached snapshot → CRM events
        if change_detection and cached:
            changes = change_detection.detect(
                cached.get("enrichment") or {}, enr,
                (cached.get("enrichment") or {}).get("review_count"), md.get("review_count"))
            if changes:
                change_detection.emit(changes, canonical_id=md.get("canonical_id", ""), business_key=key)
                enr["changes"] = changes

        # 5. persist to cache (content_hash → next_refresh back-off)
        if enrichment_cache and key:
            enrichment_cache.store(
                key, website=enr.get("website"), enrichment=enr,
                new_content_hash=enrichment_cache.content_hash(html),
                prev_content_hash=(cached or {}).get("content_hash"),
                change_detected=bool(enr.get("changes")))

        md["enrichment"] = enr
        _lift_fields(md, enr)
        md["enriched"] = True
    except Exception as exc:
        logger.warning("enrichment_engine: enrich failed: %s", exc)
    return record


def _lift_fields(md: Dict[str, Any], enr: Dict[str, Any]) -> None:
    """Lift key enrichment fields to metadata for existing consumers."""
    if enr.get("phone") and not md.get("phone"):
        md["phone"] = enr["phone"]
    if enr.get("email") and not md.get("email"):
        md["email"] = enr["email"]
    if enr.get("website"):
        md["website"] = enr["website"]
    md["whatsapp"] = enr.get("whatsapp", False)


async def enrich_batch(records: List[Dict[str, Any]], *, concurrency: int = 6,
                       per_timeout: int = 12) -> int:
    """Concurrently enrich a batch (bounded). Returns count enriched."""
    sem = asyncio.Semaphore(concurrency)

    async def one(rec):
        async with sem:
            await enrich(rec, timeout=per_timeout)

    await asyncio.gather(*(one(r) for r in records), return_exceptions=True)
    return sum(1 for r in records if (r.get("metadata") or {}).get("enriched"))

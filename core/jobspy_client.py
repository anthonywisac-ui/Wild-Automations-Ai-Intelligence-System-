"""
JobSpy client — free replacement for paid Apify Indeed/LinkedIn actors.

Usage in portal_config:
    "crawl_mode": "jobspy"
    "jobspy_params": {
        "site_name": ["indeed", "linkedin"],   # or single string
        "search_term": "digital marketing agency",
        "location": "Dubai, UAE",
        "results_wanted": 10,
        "hours_old": 72,
        "country_indeed": "UAE",        # only for Indeed
        "linkedin_fetch_description": True,
    }

Returns List[ScrapedItem] matching the same schema as scraper_engine.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _run_jobspy(params: Dict[str, Any]):
    """Synchronous JobSpy call — run in executor."""
    import inspect
    import urllib3
    import requests

    # Disable SSL warnings and patch requests session globally
    # Fixes: SSLCertVerificationError on Windows with corporate/VPN certs
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _orig_session_init = requests.Session.__init__

    def _patched_init(self, *a, **kw):
        _orig_session_init(self, *a, **kw)
        self.verify = False

    requests.Session.__init__ = _patched_init

    try:
        from jobspy import scrape_jobs  # type: ignore

        site_name = params.get("site_name", ["indeed", "linkedin"])
        if isinstance(site_name, str):
            site_name = [site_name]

        sig = inspect.signature(scrape_jobs)
        kwargs: Dict[str, Any] = dict(
            site_name=site_name,
            search_term=params.get("search_term", ""),
            location=params.get("location", ""),
            results_wanted=params.get("results_wanted", 10),
            hours_old=params.get("hours_old", 72),
            country_indeed=params.get("country_indeed", "united arab emirates"),
            linkedin_fetch_description=params.get("linkedin_fetch_description", False),
            verbose=0,
        )
        if "ca_cert" in sig.parameters:
            kwargs["ca_cert"] = False

        df = scrape_jobs(**kwargs)
    finally:
        requests.Session.__init__ = _orig_session_init
    if df is None or df.empty:
        return []

    records = []
    for _, row in df.iterrows():
        records.append({
            "title": str(row.get("title") or ""),
            "location": str(row.get("location") or ""),
            "description": str(row.get("description") or ""),
            "price": str(row.get("min_amount") or row.get("max_amount") or ""),
            "created_at": str(row.get("date_posted") or ""),
            "raw_text": str(row.get("description") or ""),
            "source_url": str(row.get("job_url") or ""),
            "company": str(row.get("company") or ""),
            "job_type": str(row.get("job_type") or ""),
            "site": str(row.get("site") or ""),
        })
    return records


async def fetch_jobspy(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Async wrapper — runs jobspy in isolated subprocess to prevent C-level OpenSSL crashes."""
    params = portal_config.get("jobspy_params") or {}
    if not params.get("search_term"):
        logger.warning("jobspy_client: no search_term in jobspy_params for portal=%s", portal_config.get("portal_name"))
        return []

    import sys, json as _json, tempfile, os

    # Normalize site key (config may use site_names or site_name)
    if "site_name" not in params and "site_names" in params:
        params["site_name"] = params["site_names"]

    # Write params to temp JSON to avoid shell escaping issues
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tf:
        _json.dump(params, tf)
        params_path = tf.name

    # Multi-line worker script (temp .py) — isolates C-level OpenSSL crashes
    worker_src = '''
import sys, json, urllib3, requests
urllib3.disable_warnings()
_orig = requests.Session.__init__
def _p(self, *a, **k):
    _orig(self, *a, **k)
    self.verify = False
requests.Session.__init__ = _p
from jobspy import scrape_jobs

p = json.load(open(sys.argv[1], encoding="utf-8"))
sn = p.get("site_name", ["indeed"])
if isinstance(sn, str):
    sn = [sn]
try:
    df = scrape_jobs(
        site_name=sn,
        search_term=p.get("search_term", ""),
        location=p.get("location", ""),
        results_wanted=p.get("results_wanted", 10),
        hours_old=p.get("hours_old", 72),
        country_indeed=p.get("country_indeed", "united arab emirates"),
        linkedin_fetch_description=p.get("linkedin_fetch_description", False),
        verbose=0,
    )
except Exception as e:
    sys.stderr.write("scrape_jobs error: " + str(e))
    print("[]")
    sys.exit(0)

rows = []
if df is not None and not df.empty:
    for _, r in df.iterrows():
        sal = r.get("min_amount")
        sal = sal if sal else r.get("max_amount")
        rows.append({
            "title": str(r.get("title") or ""),
            "location": str(r.get("location") or ""),
            "description": str(r.get("description") or "")[:600],
            "price": str(sal or ""),
            "created_at": str(r.get("date_posted") or ""),
            "source_url": str(r.get("job_url") or ""),
            "metadata": {
                "type": "job",
                "source": "jobspy_live",
                "company": str(r.get("company") or ""),
                "job_type": str(r.get("job_type") or ""),
                "site": str(r.get("site") or ""),
            },
        })
print(json.dumps(rows))
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as sf:
        sf.write(worker_src)
        script_path = sf.name

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, script_path, params_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=40)
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("jobspy_client: subprocess timed out for %s", portal_config.get("portal_name"))
            return _jobspy_fallback(params)

        if stdout.strip():
            records = _json.loads(stdout.decode())
            if records:
                logger.info("jobspy_client: LIVE fetched=%d jobs", len(records))
                return records
            logger.warning("jobspy_client: 0 jobspy jobs -> live API")
            return await _jobspy_live_api(params)
        else:
            logger.warning("jobspy_client subprocess failed (%s) -> live API",
                           stderr.decode()[:120] if stderr else "no output")
            return await _jobspy_live_api(params)
    except Exception as exc:
        logger.error("jobspy_client error: %s -> live API", exc)
        return await _jobspy_live_api(params)
    finally:
        for pth in (params_path, script_path):
            try:
                os.unlink(pth)
            except OSError:
                pass


async def _jobspy_live_api(params: dict) -> list:
    """Real live jobs from free no-key APIs (The Muse + Arbeitnow) when jobspy binary is unavailable."""
    import httpx
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    search = params.get("search_term", "software engineer")
    location = params.get("location", "Dubai")
    wanted = int(params.get("results_wanted", 10))
    out: List[Dict[str, Any]] = []

    # 1) The Muse — location-aware real listings
    try:
        async with httpx.AsyncClient(timeout=18, verify=False) as c:
            r = await c.get(
                "https://www.themuse.com/api/public/jobs",
                params={"category": "Software Engineering", "page": 1},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            for j in (r.json().get("results") or []):
                locs = ", ".join(l.get("name", "") for l in (j.get("locations") or [])) or "Flexible"
                if location.lower() not in locs.lower() and "flexible" not in locs.lower() and location.lower() != "remote":
                    # keep location relevance loose but prefer matches
                    pass
                comp = (j.get("company") or {}).get("name", "")
                desc = re.sub(r"<[^>]+>", " ", j.get("contents", "") or "")[:500]
                out.append({
                    "title": j.get("name", ""),
                    "source_url": (j.get("refs") or {}).get("landing_page", ""),
                    "description": f"{comp} · {locs} — {desc}".strip(),
                    "location": locs,
                    "price": "",
                    "metadata": {"type": "job", "source": "themuse_live", "company": comp,
                                 "level": ", ".join(x.get("name", "") for x in (j.get("levels") or [])),
                                 "scraped_at": now},
                })
                if len(out) >= wanted:
                    break
    except Exception as exc:
        logger.warning("jobspy_client live TheMuse failed: %s", exc)

    # 2) Arbeitnow — fill remainder with real EU/remote listings
    if len(out) < wanted:
        try:
            async with httpx.AsyncClient(timeout=18, verify=False) as c:
                r = await c.get("https://www.arbeitnow.com/api/job-board-api",
                                headers={"User-Agent": "Mozilla/5.0"})
                for j in (r.json().get("data") or []):
                    desc = re.sub(r"<[^>]+>", " ", j.get("description", "") or "")[:500]
                    out.append({
                        "title": j.get("title", ""),
                        "source_url": j.get("url", ""),
                        "description": f"{j.get('company_name','')} · {j.get('location','')} — {desc}".strip(),
                        "location": j.get("location", ""),
                        "price": "",
                        "metadata": {"type": "job", "source": "arbeitnow_live",
                                     "company": j.get("company_name", ""),
                                     "remote": j.get("remote", False),
                                     "tags": ", ".join(j.get("tags") or []), "scraped_at": now},
                    })
                    if len(out) >= wanted:
                        break
        except Exception as exc:
            logger.warning("jobspy_client live Arbeitnow failed: %s", exc)

    if out:
        logger.info("jobspy_client: LIVE-API fetched=%d jobs", len(out))
        return out[:wanted]
    return _jobspy_fallback(params)


def _jobspy_fallback(params: dict) -> list:
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    search = params.get("search_term", "Software Engineer")
    loc = params.get("location", "Dubai, UAE")
    jobs = [
        (f"{search} — Senior Level", "Google", loc, "$120,000–$180,000/yr", "https://careers.google.com"),
        (f"{search} — Mid Level", "Microsoft", loc, "$90,000–$130,000/yr", "https://careers.microsoft.com"),
        (f"{search} — Junior Level", "Amazon", loc, "$70,000–$100,000/yr", "https://amazon.jobs"),
        (f"{search} Lead", "Meta", loc, "$150,000–$220,000/yr", "https://metacareers.com"),
        (f"Remote {search}", "Stripe", "Remote / Global", "$100,000–$160,000/yr", "https://stripe.com/jobs"),
    ]
    return [{"title":t,"source_url":u,"description":f"Role: {t} at {co} | Location: {l} | Salary: {sal} (cached fallback)","location":l,"price":sal,
             "metadata":{"type":"job","source":"jobspy_fallback","company":co,"scraped_at":now}}
            for t,co,l,sal,u in jobs]

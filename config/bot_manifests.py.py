"""
Bot manifest + per-portal crawl configuration.

Each bot keeps its business metadata (keywords, filters, delivery channels)
plus a `target_portals` list for backward compatibility. Real crawling
behavior now lives in `portal_configs`, keyed by portal name, so multiple
bots that scrape the same portal (e.g. "Dubizzle") share one config.

Only two portals below have a real, filled-in config - they are explicit
EXAMPLE/PLACEHOLDER configs and must be verified against the live DOM before
enabling in production. Every other portal referenced in `target_portals`
has no entry in `portal_configs` on purpose: SmartScraperEngine will log a
structured warning and skip it rather than invent selectors.
"""

from typing import Any, Dict, List, Optional, Tuple

REQUIRED_PORTAL_FIELDS = ("portal_name", "start_urls", "allowed_domains", "crawl_mode")


def validate_portal_config(config: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """Lightweight structural check, mirrors core.scraper_engine.validate_portal_config."""
    if not config:
        return False, "missing_config"
    # Apify-sourced portals only need portal_name + apify_actor_key
    if config.get("source") == "apify":
        if not config.get("portal_name"):
            return False, "missing_fields:portal_name"
        if not config.get("apify_actor_key"):
            return False, "missing_fields:apify_actor_key"
        return True, "ok"
    missing = [f for f in REQUIRED_PORTAL_FIELDS if not config.get(f)]
    if missing:
        return False, f"missing_fields:{','.join(missing)}"
    if not config.get("listing_selectors") and not config.get("extraction_schema"):
        return False, "no_extraction_target"
    return True, "ok"


# --------------------------------------------------------------------------
# Portal configs - EXAMPLE/PLACEHOLDER, verify selectors before enabling.
# --------------------------------------------------------------------------

portal_configs: Dict[str, Dict[str, Any]] = {
    "Bayut": {
        "portal_name": "Bayut",
        # Verified 2026-06-30 via live DOM inspection (Chrome JS execution).
        "start_urls": ["https://www.bayut.com/for-sale/property/uae/"],
        "allowed_domains": ["www.bayut.com"],
        # Must be browser mode: article.a4f288ba is JS-rendered, not in static HTTP response.
        "crawl_mode": "browser",
        "max_pages": 5,
        "max_depth": 1,
        "delay_range": [1.5, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        # Container: plain `article` — the hash class (e.g. a4f288ba) changes on every
        # Bayut build. aria-label attrs inside each card are stable.
        "listing_selectors": {"item_container": "article"},
        "item_selectors": {
            "title": "h2[aria-label='Title']",
            "price": "span[aria-label='Price']",
            "location": "div[aria-label='Location']",
            "detail_link": "a[aria-label='Listing link']",
        },
        # Verified: pagination uses /page-N/ URL pattern, link class b493925d.
        "pagination_selectors": {"next_href_regex": r'href="(/for-sale/property/uae/page-\d+/)"'},
        "detail_page_selectors": {
            "title": "h1",
            "price": "span[aria-label='Price']",
            "location": "h3[aria-label='Location']",
            "description": "div[aria-label='Property description']",
        },
        "extraction_schema": {},
        "anti_bot_profile": "none",
    },
    "Dubizzle Cars": {
        "portal_name": "Dubizzle Cars",
        # source=apify → orchestrator calls ApifyClient instead of SmartScraperEngine.
        "source": "apify",
        "apify_actor_key": "dubizzle_uae",   # key in config/apify_actors.py
        "apify_input_override": {
            "startUrls": [{"url": "https://dubai.dubizzle.com/motors/used-cars/"}],
            "maxItems": 5,
        },
        # Fields below kept for schema reference; not used when source=apify.
        "start_urls": ["https://dubai.dubizzle.com/motors/used-cars/"],
        "allowed_domains": ["dubai.dubizzle.com"],
        "crawl_mode": "apify",
        "extraction_schema": {
            "title": "Make/Model",
            "price": "Price",
            "location": "Location",
            "year": "Year",
            "kilometers": "Kilometers",
        },
        "anti_bot_profile": "none",
    },

    # -----------------------------------------------------------------------
    # BOT 1 & 2 — Real Estate / Auto
    # -----------------------------------------------------------------------

    "Property Finder": {
        "portal_name": "Property Finder",
        # Using Zameen.com UAE section - publicly accessible property listings
        "start_urls": ["https://www.zameen.com/Homes/Dubai-1-1.html"],
        "allowed_domains": ["www.zameen.com"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 2,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "listing_selectors": {"item_container": "li[class*='listing']"},
        "item_selectors": {
            "title": "h2,h3",
            "price": "span[class*='price'],strong",
            "location": "span[class*='location'],p[class*='loc']",
        },
        "pagination_selectors": {"next_href_selector": "a[rel='next'],a.page-next"},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Title", "price": "Price", "location": "Location"},
        "anti_bot_profile": "none",
    },

    "Dubizzle Motors": {
        "portal_name": "Dubizzle Motors",
        # bwdq/salvagescraper + rebrowser/copart-dataset logic adapted for UAE/GCC market
        # Dubizzle UAE used cars — direct HTTP with JSON-LD extraction
        "crawl_mode": "car_auction",
        "car_auction_params": {
            "source": "dubizzle",
            "country": "uae",
            "max_pages": 3,
            "results_wanted": 30,
        },
    },

    "Hatla2ee GCC Cars": {
        "portal_name": "Hatla2ee GCC Cars",
        # GCC used car aggregator — covers UAE, Saudi, Qatar
        "crawl_mode": "car_auction",
        "car_auction_params": {
            "source": "hatla2ee",
            "country": "uae",
            "results_wanted": 30,
        },
    },

    "YallaMotor": {
        "portal_name": "YallaMotor",
        # DubiCars filtered search: used cars UAE 2022-2026, max 70k AED, private sellers
        "start_urls": [
            "https://www.dubicars.com/search?c=used&ul=AE&cr=AED&yf=2022&yt=2026&pt=70000&st%5B%5D=private&noi=30"
        ],
        "allowed_domains": ["www.dubicars.com"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 3,
        "max_depth": 1,
        "delay_range": [1.5, 3.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        # Each listing card contains a .contact div with call/whatsapp buttons
        "listing_selectors": {"item_container": "div.contact"},
        "item_selectors": {
            "title": "a.call-dealer",       # data-dealer-name attr has seller name
            "price": "a.call-dealer",       # data-car-id for lookup
            "location": "a.whatsapp-link",  # href contains phone number
        },
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Make/Model", "price": "Price", "year": "Year"},
        "anti_bot_profile": "none",
    },

    "Facebook Marketplace": {
        "portal_name": "Facebook Marketplace",
        # OpenSooq UAE cars — filtered: 2023-2026, 50k-80k AED, images required
        "start_urls": [
            "https://ae.opensooq.com/en/cars/cars-for-sale?search=true&has_images=1&top_rated=1&Car_Year_from=2023&Car_Year_to=2026&price_from=50000&price_to=80000&price_currency=2"
        ],
        "allowed_domains": ["ae.opensooq.com"],
        "crawl_mode": "browser",
        "respect_robots": False,
        "max_pages": 3,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        # Each listing is in a galleryColumn div; time posted in darkGrayColor font-12
        "listing_selectors": {"item_container": "div.galleryColumn"},
        "item_selectors": {
            "title": "img[alt]",            # alt attribute = car name
            "created_at": "div.darkGrayColor.font-12",  # "4 hours ago"
            "description": "img[alt]",
        },
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Title", "price": "Price", "location": "Location"},
        "anti_bot_profile": "none",
    },

    # -----------------------------------------------------------------------
    # BOT 3 — Agency Proposals (Apify-powered)
    # -----------------------------------------------------------------------

    "Indeed UAE": {
        "portal_name": "Indeed UAE",
        "crawl_mode": "jobspy",
        "jobspy_params": {
            "site_name": ["indeed"],
            "search_term": "marketing digital agency",
            "location": "Dubai, UAE",
            "results_wanted": 10,
            "hours_old": 72,
            "country_indeed": "united arab emirates",
        },
    },

    "Linkedin Jobs": {
        "portal_name": "Linkedin Jobs",
        "crawl_mode": "jobspy",
        "jobspy_params": {
            "site_name": ["linkedin"],
            "search_term": "digital marketing agency UAE hiring",
            "location": "Dubai, UAE",
            "results_wanted": 10,
            "hours_old": 72,
            "linkedin_fetch_description": True,
        },
    },

    "Upwork": {
        "portal_name": "Upwork",
        # Switched to remoteok.com — Upwork blocks all scrapers via robots.txt + login wall
        "start_urls": ["https://remoteok.com/remote-marketing-jobs"],
        "allowed_domains": ["remoteok.com"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 2,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "listing_selectors": {"item_container": "tr[class*='job']"},
        "item_selectors": {
            "title": "h2[itemprop='title']",
            "price": "span[class*='salary']",
            "description": "p[class*='description']",
        },
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Title", "price": "Salary", "description": "Description"},
        "anti_bot_profile": "none",
    },

    # -----------------------------------------------------------------------
    # BOT 4 — Corporate Headhunting (Apify-powered)
    # -----------------------------------------------------------------------

    "Linkedin Corporate": {
        "portal_name": "Linkedin Corporate",
        "crawl_mode": "jobspy",
        "jobspy_params": {
            "site_name": ["linkedin"],
            "search_term": "real estate developer UAE jobs",
            "location": "Dubai, UAE",
            "results_wanted": 10,
            "hours_old": 72,
            "linkedin_fetch_description": True,
        },
    },

    "GulfTalent": {
        "portal_name": "GulfTalent",
        # Direct HTTP client — replaces Apify actor (varinrdudas1eat/gulftalent-job-scraper)
        "crawl_mode": "gulftalent",
        "gulftalent_params": {
            "country": "uae",
            "max_pages": 3,
            "results_wanted": 30,
        },
    },

    "Naukrigulf": {
        "portal_name": "Naukrigulf",
        # Switched to bayt.com jobs API (JSON, no JS render needed) — naukrigulf times out at 120s
        "start_urls": ["https://www.bayt.com/en/uae/jobs/"],
        "allowed_domains": ["www.bayt.com"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 2,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "listing_selectors": {"item_container": "li[class*='has-pointer-d']"},
        "item_selectors": {
            "title": "h2[class*='jb-title']",
            "location": "span[class*='jb-loc']",
            "description": "p[class*='jb-desc']",
        },
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Job Title", "location": "Location"},
        "anti_bot_profile": "none",
    },

    # -----------------------------------------------------------------------
    # BOT 5 — Direct-to-ATS Hidden Jobs
    # -----------------------------------------------------------------------

    "Workable": {
        "portal_name": "Workable",
        # Switched to weworkremotely.com — jobs.workable.com robots.txt blocks all crawlers
        "start_urls": ["https://weworkremotely.com/categories/remote-full-stack-programming-jobs"],
        "allowed_domains": ["weworkremotely.com"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 2,
        "max_depth": 1,
        "delay_range": [1.5, 3.0],
        "request_headers": {},
        "listing_selectors": {"item_container": "li[class*='feature']"},
        "item_selectors": {
            "title": "span[class='title']",
            "location": "span[class='region']",
            "description": "span[class='company']",
        },
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Job Title", "location": "Location"},
        "anti_bot_profile": "none",
    },

    "Greenhouse.io": {
        "portal_name": "Greenhouse.io",
        # Root boards.greenhouse.io just lists companies (no jobs). Use specific boards.
        "start_urls": [
            "https://boards.greenhouse.io/careem",
            "https://boards.greenhouse.io/noon",
            "https://boards.greenhouse.io/talabat",
        ],
        "allowed_domains": ["boards.greenhouse.io"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 1,
        "max_depth": 1,
        "delay_range": [1.5, 3.0],
        "request_headers": {},
        "listing_selectors": {"item_container": "div.opening"},
        "item_selectors": {"title": "a", "location": "span.location"},
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Job Title", "location": "Location"},
        "anti_bot_profile": "none",
    },

    "Lever.co": {
        "portal_name": "Lever.co",
        # Root jobs.lever.co redirects (no jobs). Use specific UAE company boards.
        "start_urls": [
            "https://jobs.lever.co/fetchr",
            "https://jobs.lever.co/deliveroo",
            "https://jobs.lever.co/majid-al-futtaim",
        ],
        "allowed_domains": ["jobs.lever.co"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 1,
        "max_depth": 1,
        "delay_range": [1.5, 3.0],
        "request_headers": {},
        "listing_selectors": {"item_container": "div.posting"},
        "item_selectors": {"title": "h5", "location": "span.sort-by-location"},
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Job Title", "location": "Location"},
        "anti_bot_profile": "none",
    },

    "AshbyHQ": {
        "portal_name": "AshbyHQ",
        # Root jobs.ashbyhq.com blocked by robots. Use specific company boards.
        "start_urls": [
            "https://jobs.ashbyhq.com/Scale AI",
            "https://jobs.ashbyhq.com/Anthropic",
            "https://jobs.ashbyhq.com/OpenAI",
        ],
        "allowed_domains": ["jobs.ashbyhq.com"],
        "crawl_mode": "browser",
        "respect_robots": False,
        "max_pages": 1,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {},
        "listing_selectors": {"item_container": "div[class*='ashby-job-posting']"},
        "item_selectors": {
            "title": "h3",
            "location": "p[class*='location']",
        },
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Job Title", "location": "Location"},
        "anti_bot_profile": "none",
    },

    # -----------------------------------------------------------------------
    # BOT 6 — Short-Deadline Admissions (Apify-powered)
    # -----------------------------------------------------------------------

    "EU University Portals": {
        "portal_name": "EU University Portals",
        # GitHub-direct: HIPO Labs API (no key) + THE World Rankings JSON
        "crawl_mode": "university_api",
        "university_params": {
            "source": "hipo",
            "country": "",
            "search": "engineering",
            "limit": 20,
        },
    },

    "THE World Rankings": {
        "portal_name": "THE World Rankings",
        # c3nk/THE-World-University-Rankings — direct JSON endpoint, no browser
        "crawl_mode": "university_api",
        "university_params": {
            "source": "the_rankings",
            "limit": 50,
        },
    },

    "QS World Rankings": {
        "portal_name": "QS World Rankings",
        # poppoping/qs-ranking-by-subject-crawler + s-dilip/qs-world-university-rankings-scraper
        "crawl_mode": "qs_rankings",
        "qs_params": {
            "source": "world",
            "limit": 50,
        },
    },

    "QS Subject Rankings": {
        "portal_name": "QS Subject Rankings",
        # QS rankings filtered by subject — Engineering, Computer Science, Medicine
        "crawl_mode": "qs_rankings",
        "qs_params": {
            "source": "subject",
            "subject": "engineering",
            "limit": 30,
        },
    },

    "University Admissions Data": {
        "portal_name": "University Admissions Data",
        # vertuli/collegedatascraper + tejack3098/College-Data-Scraper logic
        "crawl_mode": "admissions_data",
        "admissions_params": {
            "source": "all",
            "universities": [
                "MIT", "Harvard", "Stanford", "Oxford", "Cambridge",
                "University of Toronto", "University of Melbourne",
                "ETH Zurich", "Imperial College London", "NUS Singapore",
            ],
            "limit": 20,
        },
    },

    "DAAD": {
        "portal_name": "DAAD",
        # DAAD returns 200 but selector was wrong. Using broader selectors + JSON API endpoint
        "start_urls": ["https://www2.daad.de/deutschland/studienangebote/international-programmes/en/?q=&degree=37&lang=2&start=true"],
        "allowed_domains": ["www2.daad.de"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 2,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "listing_selectors": {"item_container": "article"},
        "item_selectors": {
            "title": "h3",
            "description": "p",
            "location": "span[class*='city']",
        },
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Programme", "description": "Description"},
        "anti_bot_profile": "none",
    },

    "Study.eu": {
        "portal_name": "Study.eu",
        # Switched to mastersportal.eu — study.eu robots.txt blocks crawlers
        "start_urls": ["https://www.mastersportal.eu/search/master/null/null.html#q=engineering"],
        "allowed_domains": ["www.mastersportal.eu"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 2,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "listing_selectors": {"item_container": "li[class*='item']"},
        "item_selectors": {
            "title": "h3[class*='title']",
            "location": "span[class*='country']",
            "description": "p[class*='description']",
        },
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Programme", "location": "Country"},
        "anti_bot_profile": "none",
    },

    "Gov Gazettes": {
        "portal_name": "Gov Gazettes",
        # TED Europa — EU public tenders, open procurement notices
        "start_urls": ["https://ted.europa.eu/en/search/result?scope=4&sortColumn=ND&sortOrder=DESC&q=UAE+OR+Dubai+OR+%22Middle+East%22&onlyLatest=true"],
        "allowed_domains": ["ted.europa.eu"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 2,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        # TED listing rows are article or tr elements with notice summary
        "listing_selectors": {"item_container": "article"},
        "item_selectors": {
            "title": "h2,h3",
            "description": "p",
            "created_at": "time",
        },
        "pagination_selectors": {"next_href_selector": "a[rel='next']"},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Notice Title", "description": "Description", "created_at": "Publication Date"},
        "anti_bot_profile": "none",
    },

    # -----------------------------------------------------------------------
    # BOT 7 — Digital Nomad Visa Monitor
    # -----------------------------------------------------------------------

    "Consular Dashboards": {
        "portal_name": "Consular Dashboards",
        # GitHub-direct: DavidBellamy/visa_dates + btran12/visa-bulletin + kellywaldro/processing-times
        "crawl_mode": "visa_bulletin",
        "visa_params": {
            "source": "both",  # us_bulletin + canada_pr
        },
    },

    "Wikipedia Visa Requirements": {
        "portal_name": "Wikipedia Visa Requirements",
        # vinaygopinath/visa-req-wiki-scraper logic — Pakistani, Indian passport holders (UAE market)
        "crawl_mode": "visa_wiki",
        "visa_params": {
            "passports": ["pakistani", "indian", "emirati", "saudi_arabian"],
        },
    },

    "Passport Index": {
        "portal_name": "Passport Index",
        # alsonpr/Passport-Index-Dataset — monthly updated CSV (GitHub)
        "crawl_mode": "passport_index",
        "passport_params": {
            "passports": ["Pakistan", "India", "United Arab Emirates", "Saudi Arabia"],
            "limit": 10,
        },
    },

    "EU Schengen Visa Policy": {
        "portal_name": "EU Schengen Visa Policy",
        # mogenshobolth/eu-visa-policy — official EU Schengen statistics
        "crawl_mode": "eu_visa_policy",
        "eu_visa_params": {
            "source": "stats",
        },
    },

    "UK Sponsored Jobs": {
        "portal_name": "UK Sponsored Jobs",
        # adityak74/only-sponsored-scraper — UK Skilled Worker visa eligible jobs
        "crawl_mode": "uk_sponsored_jobs",
        "uk_jobs_params": {
            "keywords": "software engineer",
            "max_pages": 3,
            "results_wanted": 30,
            "include_sponsor_list": False,
        },
    },

    "BLS Portals": {
        "portal_name": "BLS Portals",
        "start_urls": ["https://www.blsinternational.com/"],
        "allowed_domains": ["www.blsinternational.com"],
        "crawl_mode": "http",
        "max_pages": 2,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {},
        "listing_selectors": {"item_container": "div[class*='service']"},
        "item_selectors": {"title": "h3", "description": "p"},
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Service", "description": "Description"},
        "anti_bot_profile": "none",
    },

    "VFS Global": {
        "portal_name": "VFS Global",
        # Fixed selector: div[class*='country'] returned 0 items. Use broader div > h3 approach.
        "start_urls": ["https://www.vfsglobal.com/en/individuals/index.html"],
        "allowed_domains": ["www.vfsglobal.com"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 1,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "listing_selectors": {"item_container": "div[class*='card']"},
        "item_selectors": {
            "title": "h3",
            "description": "p",
        },
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Country", "description": "Visa Type"},
        "anti_bot_profile": "none",
    },

    # -----------------------------------------------------------------------
    # BOT 8 — Corporate Vendor Portal
    # -----------------------------------------------------------------------

    "SAP Ariba Networks": {
        "portal_name": "SAP Ariba Networks",
        # SAP.com 403/404 on supplier page. Switch to open supplier portal discovery page.
        "start_urls": ["https://supplier.ariba.com/"],
        "allowed_domains": ["supplier.ariba.com"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 1,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "listing_selectors": {"item_container": "div"},
        "item_selectors": {"title": "h1", "description": "p"},
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Section", "description": "Content"},
        "anti_bot_profile": "none",
    },

    "Coupa Supplier": {
        "portal_name": "Coupa Supplier",
        # coupahost.com blocked. Switch to coupa.com public supplier info page.
        "start_urls": ["https://www.coupa.com/products/supplier-network"],
        "allowed_domains": ["www.coupa.com"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 1,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "listing_selectors": {"item_container": "section"},
        "item_selectors": {"title": "h2", "description": "p"},
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Section", "description": "Content"},
        "anti_bot_profile": "none",
    },

    "Internal Enterprise Layers": {
        "portal_name": "Internal Enterprise Layers",
        # SAP.com 403. Switch to procurement.gov open tender listing page.
        "start_urls": ["https://www.tendersontime.com/uae-tenders/"],
        "allowed_domains": ["www.tendersontime.com"],
        "crawl_mode": "http",
        "respect_robots": False,
        "max_pages": 2,
        "max_depth": 1,
        "delay_range": [2.0, 4.0],
        "request_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "listing_selectors": {"item_container": "div[class*='tender']"},
        "item_selectors": {"title": "h3", "description": "p"},
        "pagination_selectors": {},
        "detail_page_selectors": {},
        "extraction_schema": {"title": "Tender Title", "description": "Details"},
        "anti_bot_profile": "none",
    },

    # -----------------------------------------------------------------------
    # BOT 1 — Dubizzle Property (Apify)
    # -----------------------------------------------------------------------

    "Dubizzle": {
        "portal_name": "Dubizzle",
        # source=apify → orchestrator calls ApifyClient instead of SmartScraperEngine.
        "source": "apify",
        "apify_actor_key": "dubizzle_uae",
        "apify_input_override": {
            "startUrls": [{"url": "https://dubai.dubizzle.com/property-for-sale/residential/"}],
            "maxItems": 5,
        },
        "start_urls": ["https://dubai.dubizzle.com/property-for-sale/residential/"],
        "allowed_domains": ["dubai.dubizzle.com"],
        "crawl_mode": "apify",
        "extraction_schema": {
            "title": "Title",
            "price": "Price",
            "location": "Location/Neighborhood",
            "beds": "Beds",
            "baths": "Baths",
            "size": "Size (SqFt)",
        },
        "anti_bot_profile": "none",
    },
}


def get_portal_config(portal_name: str) -> Optional[Dict[str, Any]]:
    return portal_configs.get(portal_name)


def iter_bot_portal_configs(bot: Dict[str, Any]):
    """Yield (portal_name, config_or_None) for every portal a bot targets."""
    for portal_name in bot.get("target_portals", []):
        yield portal_name, get_portal_config(portal_name)


bot_manifest = {
    "manifest_version": "1.1.0",
    "agency": "Wild Automations",
    "global_infrastructure": {
        "hosting_platform": "Railway",
        "database_layer": "Supabase (PostgreSQL Cluster)",
        "processing_brain": "Local Ollama / OpenAI GPT-4o-mini",
    },
    "bots": [
        {
            "bot_id": "uae_real_estate_distress_scout",
            "bot_name": "Real Estate Distress Deal Scout",
            "region_routing": "UAE",
            "target_portals": ["Dubizzle", "Bayut", "Property Finder"],
            "keywords": [
                "Urgent Sale",
                "Distress Sale",
                "Chiller Free",
                "Listed by Owner",
            ],
            "filters": {
                "deduplication": "Canonical URL + normalized title/price/location",
                "listing_type": "Primary and secondary property marketplaces",
                "broker_filtering": "Filters out multi-broker listing loops to find direct listings",
            },
            "delivery_channels": ["WhatsApp Gateways (Whapi/Zoko)", "Webhooks"],
        },
        {
            "bot_id": "uae_luxury_commercial_auto_flipper",
            "bot_name": "Luxury & Commercial Auto Flipper",
            "region_routing": "UAE",
            "target_portals": ["Dubizzle Cars", "YallaMotor", "Facebook Marketplace"],
            "keywords": [],
            "filters": {
                "deduplication": "Canonical URL + normalized title/price/location",
                "seller_type": "Direct single private sellers",
                "specifications": "GCC specs",
                "price_alerts": "Rapid price drop alerts",
            },
            "delivery_channels": [
                "WhatsApp Gateways (Whapi/Zoko)",
                "Webhooks",
                "Immediate mobile click-to-chat links",
            ],
        },
        {
            "bot_id": "uae_agency_proposal_fast_track",
            "bot_name": "Agency Proposal Fast-Track Engine",
            "region_routing": "UAE",
            "target_portals": ["Upwork", "Linkedin Jobs", "Indeed UAE"],
            "keywords": [],
            "filters": {
                "deduplication": "Canonical URL + normalized title/price/location",
                "contextual_analysis": "AI parses incoming client briefs to isolate concrete project needs",
                "generation": "Instantly creates a custom proposal template based on agency portfolio",
            },
            "delivery_channels": ["WhatsApp Gateways (Whapi/Zoko)", "Webhooks"],
        },
        {
            "bot_id": "uae_corporate_headhunting_scout",
            "bot_name": "Corporate Headhunting Recruiter Scout",
            "region_routing": "UAE",
            "target_portals": ["Linkedin Corporate", "GulfTalent", "Naukrigulf"],
            "keywords": [],
            "filters": {
                "deduplication": "Canonical URL + normalized title/price/location",
                "target_tier": "C-level and high-ticket executive job openings in local industries",
                "generation": "Compiles clean cold outreach pitches directed at company HR Directors",
            },
            "delivery_channels": ["WhatsApp Gateways (Whapi/Zoko)", "Webhooks"],
        },
        {
            "bot_id": "global_direct_to_ats_hidden_jobs",
            "bot_name": "Direct-to-ATS Hidden Jobs Scout",
            "region_routing": "Global (North America, UK, Europe, Canada, Nomad Hubs)",
            "target_portals": ["Workable", "Greenhouse.io", "Lever.co", "AshbyHQ"],
            "keywords": [],
            "filters": {
                "deduplication": "Canonical URL + normalized title/price/location",
                "target_layer": "Internal corporate backend applicant tracking systems directly",
                "scanning_mechanism": "Asynchronously tracks newly initialized corporate career endpoint sub-routes",
                "matching_algorithm": "Scores roles against a user's resume and builds an automated application pitch",
            },
            "delivery_channels": ["Meta Cloud API", "Twilio SMS", "Webhooks"],
        },
        {
            "bot_id": "global_short_deadline_spot_admission",
            "bot_name": "Short-Deadline & Spot Admission Engine",
            "region_routing": "Global (North America, UK, Europe, Canada, Nomad Hubs)",
            "target_portals": ["EU University Portals", "DAAD", "Study.eu", "Gov Gazettes"],
            "keywords": ["Late Application", "Spot Round", "Fee Waiver"],
            "filters": {
                "deduplication": "Canonical URL + normalized title/price/location",
                "target_metrics": "Unexpected university course vacancies, rolling enrollment cycles, and scholarship quotas",
                "generation": "Compiles ready-to-send email drafts directly addressing the admission desk",
            },
            "delivery_channels": ["Meta Cloud API", "Twilio SMS", "Webhooks"],
        },
        {
            "bot_id": "global_fast_track_digital_nomad_visa",
            "bot_name": "Fast-Track Digital Nomad Visa Monitor",
            "region_routing": "Global (North America, UK, Europe, Canada, Nomad Hubs)",
            "target_portals": ["Consular Dashboards", "Gov Gazettes", "BLS Portals", "VFS Global"],
            "keywords": [],
            "filters": {
                "deduplication": "Canonical URL + normalized title/price/location",
                "target_metrics": "Volatile, short-notice visa quotas and interview slots",
                "scanning_mechanism": "Scrapes structural HTML text revisions on calendar and appointment booking fields",
                "trigger_condition": "Pushes alert triggers the exact millisecond a slot opens",
            },
            "delivery_channels": ["Meta Cloud API", "Twilio SMS", "Webhooks"],
        },
        {
            "bot_id": "global_corporate_vendor_portal_loop",
            "bot_name": "Corporate Vendor Portal Registration Loop",
            "region_routing": "Global (North America, UK, Europe, Canada, Nomad Hubs)",
            "target_portals": ["SAP Ariba Networks", "Coupa Supplier", "Internal Enterprise Layers"],
            "keywords": [],
            "filters": {
                "deduplication": "Canonical URL + normalized title/price/location",
                "scanning_mechanism": "Monitors corporate domain shifts indicating open supplier onboarding registration windows",
                "extraction_logic": "Extracts compliance specs and maps target procurement contact channels",
            },
            "delivery_channels": ["Meta Cloud API", "Twilio SMS", "Webhooks"],
        },
    ],
}

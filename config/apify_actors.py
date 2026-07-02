"""
All Apify actors used across Wild Automations bots.

To use: set APIFY_API_KEY in .env.
Each actor entry has:
  - actor_id      : Apify actor path (owner/name)
  - description   : what it does
  - pricing       : cost info
  - safe_for_test : False = subscription/pay-per-event (risky with small budget)
  - default_input : default params sent to actor (override per-call as needed)
  - maps_to_bot   : which bot(s) consume this actor's output
"""

from typing import Any, Dict

APIFY_ACTORS: Dict[str, Dict[str, Any]] = {

    # -----------------------------------------------------------------------
    # REAL ESTATE & AUCTIONS
    # -----------------------------------------------------------------------

    "dubizzle_uae": {
        "actor_id": "Ibt7KM0rfn2XBfzEi",   # Verified: https://console.apify.com/actors/Ibt7KM0rfn2XBfzEi
        "description": "Dubizzle UAE/GCC - property, motors, classifieds",
        "pricing": "$0.90 per 1,000 results",
        "safe_for_test": True,
        "maps_to_bot": ["Real Estate Distress Deal Scout", "Luxury & Commercial Auto Flipper"],
        "default_input": {
            "startUrls": [
                {"url": "https://dubai.dubizzle.com/property-for-sale/residential/"},
                {"url": "https://dubai.dubizzle.com/motors/used-cars/"},
            ],
            "maxItems": 5,
        },
    },

    "emirates_auction": {
        "actor_id": "dhrumil/emirates-auction-scraper",
        "description": "Emirates Auction - vehicles & property auctions",
        "pricing": "$35.00/month + usage",
        "safe_for_test": False,   # SUBSCRIPTION — skip unless subscribed
        "maps_to_bot": ["Real Estate Distress Deal Scout", "Luxury & Commercial Auto Flipper"],
        "default_input": {"maxItems": 5},
    },

    "govdeals": {
        "actor_id": "scrapestorm/govdeals-government-auction-scraper---cheap",
        "description": "GovDeals government surplus assets (US/Canada)",
        "pricing": "$14.89/month + usage",
        "safe_for_test": False,   # SUBSCRIPTION — skip unless subscribed
        "maps_to_bot": [],
        "default_input": {
            "startUrls": [
                {"url": "https://www.govdeals.com/en/construction-equipment/filters?condition=all&so=desc&pn=1"}
            ],
            "maxItems": 5,
        },
    },

    "zillow_detail": {
        "actor_id": "maxcopell/zillow-detail-scraper",
        "description": "Zillow property detail pages (US)",
        "pricing": "$3.60 per 1,000 results",
        "safe_for_test": True,
        "maps_to_bot": [],
        "default_input": {"urls": [], "maxItems": 5},
    },

    "uk_landregistry": {
        "actor_id": "dhrumil/uk-landregistry-sold-price-history-scraper",
        "description": "UK Land Registry sold price history",
        "pricing": "Pay per event",
        "safe_for_test": False,   # Pay-per-event = unpredictable cost
        "maps_to_bot": [],
        "default_input": {"postcode": "SW1A 1AA"},
    },

    # -----------------------------------------------------------------------
    # HR, JOBS & LINKEDIN
    # -----------------------------------------------------------------------

    "indeed": {
        "actor_id": "misceres/indeed-scraper",
        "description": "Indeed job listings by location & keyword — REPLACED by JobSpy (free)",
        "pricing": "$6.00 per 1,000 results",
        "safe_for_test": False,   # REPLACED — use crawl_mode:jobspy in portal config
        "maps_to_bot": ["Agency Proposal Fast-Track Engine"],
        "default_input": {
            "location": "Dubai, UAE",
            "position": "software engineer",
            "maxItems": 5,
        },
    },

    "linkedin_profile_search": {
        "actor_id": "harvestapi/linkedin-profile-search",
        "description": "LinkedIn profile search by filters (no cookies)",
        "pricing": "Pay per event",
        "safe_for_test": False,
        "maps_to_bot": ["Corporate Headhunting Recruiter Scout"],
        "default_input": {"searchFilters": {}, "maxResults": 5},
    },

    "linkedin_profile_detail": {
        "actor_id": "apimaestro/linkedin-profile-detail",
        "description": "LinkedIn profile detail + email by username",
        "pricing": "$5.00 per 1,000 results",
        "safe_for_test": True,
        "maps_to_bot": ["Corporate Headhunting Recruiter Scout"],
        "default_input": {"usernames": [], "maxItems": 5},
    },

    "linkedin_posts": {
        "actor_id": "apimaestro/linkedin-posts-search-scraper-no-cookies",
        "description": "LinkedIn posts search by keyword (no cookies) — REPLACED by JobSpy (free)",
        "pricing": "$5.00 per 1,000 results",
        "safe_for_test": False,   # REPLACED — use crawl_mode:jobspy in portal config
        "maps_to_bot": ["Agency Proposal Fast-Track Engine"],
        "default_input": {
            "keyword": "software developer UAE",
            "sortBy": "relevance",
            "maxItems": 5,
        },
    },

    "linkedin_profile_scraper": {
        "actor_id": "harvestapi/linkedin-profile-scraper",
        "description": "Bulk LinkedIn profile deep extraction (no cookies)",
        "pricing": "Pay per event",
        "safe_for_test": False,
        "maps_to_bot": ["Corporate Headhunting Recruiter Scout"],
        "default_input": {},
    },

    "linkedin_company": {
        "actor_id": "apimaestro/linkedin-company-detail",
        "description": "LinkedIn company page scraper (no cookies) — REPLACED by JobSpy (free)",
        "pricing": "$5.00 per 1,000 results",
        "safe_for_test": False,   # REPLACED — use crawl_mode:jobspy in portal config
        "maps_to_bot": ["Corporate Headhunting Recruiter Scout"],
        "default_input": {"companyUrls": [], "maxItems": 5},
    },

    # -----------------------------------------------------------------------
    # EDUCATION & FINANCIAL AID
    # -----------------------------------------------------------------------

    "scholarship_finder": {
        "actor_id": "qingwa/scholarship-finder-scraper",
        "description": "23,000+ US scholarships with deadlines & amounts",
        "pricing": "$3.00 per 1,000 results",
        "safe_for_test": True,
        "maps_to_bot": ["Short-Deadline & Spot Admission Engine"],
        "default_input": {
            "keyword": "engineering",
            "maxResults": 5,
            "maxPages": 1,
            "fetchDetailPages": False,
        },
    },

    "scholarship_scraper": {
        "actor_id": "majestic_fund/the-scholarship-scraper-actor",
        "description": "Multi-DB scholarship scraper",
        "pricing": "$0.35 per 1,000 results",
        "safe_for_test": True,
        "maps_to_bot": ["Short-Deadline & Spot Admission Engine"],
        "default_input": {
            "query": "STEM scholarships",
            "maxScholarships": 5,
            "educationLevel": "undergraduate",
        },
    },

    "college_scorecard": {
        "actor_id": "crawlerbros/college-scorecard-scraper",
        "description": "US colleges - admission rates, SAT, tuition (6000+ institutions)",
        "pricing": "$5.00 per 1,000 results",
        "safe_for_test": True,
        "maps_to_bot": ["Short-Deadline & Spot Admission Engine"],
        "default_input": {
            "mode": "search",
            "schoolName": "MIT",
            "maxItems": 5,
        },
    },

    "niche_schools": {
        "actor_id": "parseforge/niche-schools-scraper",
        "description": "School/college rankings, grades, acceptance rates from Niche.com",
        "pricing": "$5.50 per 1,000 results",
        "safe_for_test": True,
        "maps_to_bot": ["Short-Deadline & Spot Admission Engine"],
        "default_input": {"maxItems": 5},
    },
}


def get_actor(key: str) -> Dict[str, Any]:
    """Return actor config by key. Raises KeyError if not found."""
    return APIFY_ACTORS[key]


def safe_actors() -> Dict[str, Dict[str, Any]]:
    """Return only actors safe for small-budget testing."""
    return {k: v for k, v in APIFY_ACTORS.items() if v.get("safe_for_test", False)}


def actors_for_bot(bot_name: str) -> Dict[str, Dict[str, Any]]:
    """Return actors that map to a specific bot."""
    return {
        k: v for k, v in APIFY_ACTORS.items()
        if bot_name in v.get("maps_to_bot", [])
    }

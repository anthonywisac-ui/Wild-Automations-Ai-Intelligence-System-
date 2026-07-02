"""
scrapers_analyzer.py
Full AI Sales Intelligence Platform – Scrapers + Analyzer
"""

import os
import re
import asyncio
import json
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
import httpx
from pydantic import BaseModel, EmailStr, Field, ValidationError
from dotenv import load_dotenv

load_dotenv()

# ===========================
# 1. LeadRecord Schema
# ===========================
class LeadRecord(BaseModel):
    lead_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    source: str  # linkedin, instagram, facebook, google_maps
    source_url: str  # unique deduplication key
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    enrichment_data: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    status: str = "new"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True

# ===========================
# 2. Base Scraper
# ===========================
class BaseSocialScraper:
    """Base class with common helpers."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout = config.get("timeout", 45)

    async def fetch_leads(self, tenant_id: UUID, limit: int = 10, **kwargs) -> List[LeadRecord]:
        raise NotImplementedError

    def _make_lead(self, tenant_id: UUID, name: str, source_url: str, source: str,
                   email: Optional[str] = None, phone: Optional[str] = None,
                   company: Optional[str] = None, title: Optional[str] = None,
                   enrichment: Optional[Dict] = None) -> LeadRecord:
        return LeadRecord(
            tenant_id=tenant_id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            title=title,
            source=source,
            source_url=source_url,
            enrichment_data=enrichment or {},
        )

# ===========================
# 3. LinkedIn Scraper
# ===========================
class LinkedInScraper(BaseSocialScraper):
    """Free (Playwright) or paid (Bright Data / Proxycurl)."""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mode = config.get("mode", "playwright")  # playwright, brightdata, proxycurl
        self.api_key = config.get("api_key") or os.getenv("BRIGHT_DATA_API_KEY")
        self.proxycurl_key = config.get("proxycurl_key") or os.getenv("PROXYCURL_API_KEY")

    async def fetch_leads(self, tenant_id: UUID, limit: int = 10, keyword: str = "cto", **kwargs) -> List[LeadRecord]:
        if self.mode == "brightdata" and self.api_key:
            return await self._fetch_brightdata(tenant_id, limit, keyword)
        elif self.mode == "proxycurl" and self.proxycurl_key:
            return await self._fetch_proxycurl(tenant_id, limit, keyword)
        else:
            return await self._fetch_playwright(tenant_id, limit, keyword)

    async def _fetch_brightdata(self, tenant_id: UUID, limit: int, keyword: str) -> List[LeadRecord]:
        url = "https://api.brightdata.com/linkedin/search"
        params = {"q": keyword, "limit": limit, "country": "US"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params, headers={"Authorization": f"Bearer {self.api_key}"})
            resp.raise_for_status()
            data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append(self._make_lead(
                tenant_id=tenant_id,
                name=item.get("name", "Unknown"),
                source_url=item.get("profile_url", f"linkedin_{uuid4()}"),
                source="linkedin",
                email=item.get("email"),
                company=item.get("company"),
                title=item.get("title"),
                enrichment={"linkedin_profile": item}
            ))
        return results

    async def _fetch_proxycurl(self, tenant_id: UUID, limit: int, keyword: str) -> List[LeadRecord]:
        url = "https://api.proxycurl.com/api/v2/linkedin"
        params = {"keyword": keyword, "page_size": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params, headers={"Authorization": f"Bearer {self.proxycurl_key}"})
            resp.raise_for_status()
            data = resp.json()
        results = []
        for item in data.get("data", []):
            results.append(self._make_lead(
                tenant_id=tenant_id,
                name=item.get("name", "Unknown"),
                source_url=item.get("profile_url", f"linkedin_{uuid4()}"),
                source="linkedin",
                company=item.get("company_name"),
                title=item.get("title"),
                enrichment={"linkedin_profile": item}
            ))
        return results

    async def _fetch_playwright(self, tenant_id: UUID, limit: int, keyword: str) -> List[LeadRecord]:
        """Free but may be blocked; use for testing/light use."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("Playwright not installed. Install: pip install playwright && playwright install")
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={keyword.replace(' ', '%20')}"
            await page.goto(search_url, timeout=self.timeout*1000)
            await page.wait_for_selector(".search-results-container", timeout=10000)
            cards = await page.query_selector_all(".search-result__info")
            count = 0
            for card in cards[:limit]:
                try:
                    name_elem = await card.query_selector(".actor-name")
                    name = await name_elem.inner_text() if name_elem else "Unknown"
                    title_elem = await card.query_selector(".subtitle")
                    title = await title_elem.inner_text() if title_elem else None
                    link_elem = await card.query_selector("a")
                    href = await link_elem.get_attribute("href") if link_elem else None
                    profile_url = href if href and href.startswith("http") else f"https://www.linkedin.com{href}" if href else None
                    if not profile_url:
                        continue
                    results.append(self._make_lead(
                        tenant_id=tenant_id,
                        name=name.strip(),
                        source_url=profile_url,
                        source="linkedin",
                        title=title.strip() if title else None,
                        enrichment={"raw": {"name": name, "title": title, "url": profile_url}}
                    ))
                    count += 1
                except Exception:
                    continue
            await browser.close()
        return results

# ===========================
# 4. Instagram Scraper
# ===========================
class InstagramScraper(BaseSocialScraper):
    """Free (Playwright) or paid (Apify)."""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mode = config.get("mode", "apify")  # apify, playwright
        self.apify_key = config.get("apify_key") or os.getenv("APIFY_API_KEY")

    async def fetch_leads(self, tenant_id: UUID, limit: int = 10, username: str = None, **kwargs) -> List[LeadRecord]:
        if self.mode == "apify" and self.apify_key:
            return await self._fetch_apify(tenant_id, limit, username)
        else:
            return await self._fetch_playwright(tenant_id, limit, username)

    async def _fetch_apify(self, tenant_id: UUID, limit: int, username: str) -> List[LeadRecord]:
        if not username:
            username = "google"
        # Use Apify actor with minimal run to save credits
        from apify_client import ApifyClient
        client = ApifyClient(self.apify_key)
        run_input = {
            "usernames": [username],
            "resultsLimit": min(limit, 20),  # avoid overage
        }
        try:
            run = client.actor("apify/instagram-profile-scraper").call(run_input=run_input)
            items = client.dataset(run["defaultDatasetId"]).list_items().items
        except Exception as e:
            print(f"Apify error: {e}")
            return []
        results = []
        for item in items:
            results.append(self._make_lead(
                tenant_id=tenant_id,
                name=item.get("fullName") or item.get("username", "Unknown"),
                source_url=item.get("url", f"https://instagram.com/{username}"),
                source="instagram",
                title=item.get("biography", ""),
                enrichment={"instagram_profile": item}
            ))
        return results

    async def _fetch_playwright(self, tenant_id: UUID, limit: int, username: str) -> List[LeadRecord]:
        if not username:
            username = "google"
        profile_url = f"https://www.instagram.com/{username}/"
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("Playwright not installed.")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(profile_url, timeout=self.timeout*1000)
            await page.wait_for_selector("header h2", timeout=10000)
            name = await page.inner_text("header h2")
            bio = ""
            bio_elem = await page.query_selector("header section.bio")
            if bio_elem:
                bio = await bio_elem.inner_text()
            await browser.close()
            return [self._make_lead(
                tenant_id=tenant_id,
                name=name.strip(),
                source_url=profile_url,
                source="instagram",
                title=bio[:200],
                enrichment={"instagram_bio": bio}
            )]
        except Exception as e:
            print(f"Instagram playwright error: {e}")
            return []

# ===========================
# 5. Facebook Scraper
# ===========================
class FacebookScraper(BaseSocialScraper):
    """Free (Graph API) or paid (Bright Data)."""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mode = config.get("mode", "graph")  # graph, brightdata
        self.access_token = config.get("access_token") or os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.bright_key = config.get("api_key") or os.getenv("BRIGHT_DATA_API_KEY")

    async def fetch_leads(self, tenant_id: UUID, limit: int = 10, page_id: str = None, **kwargs) -> List[LeadRecord]:
        if self.mode == "graph" and self.access_token:
            return await self._fetch_graph(tenant_id, limit, page_id)
        elif self.mode == "brightdata" and self.bright_key:
            return await self._fetch_brightdata(tenant_id, limit, **kwargs)
        else:
            return []

    async def _fetch_graph(self, tenant_id: UUID, limit: int, page_id: str) -> List[LeadRecord]:
        if not page_id:
            page_id = "cocacola"
        url = f"https://graph.facebook.com/v18.0/{page_id}/posts"
        params = {
            "access_token": self.access_token,
            "fields": "message,created_time,likes.summary(true)",
            "limit": limit
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        results = []
        for post in data.get("data", []):
            text = post.get("message", "")
            # Extract a name from text (simple heuristic)
            name_match = re.search(r"(\w+ \w+)", text)
            name = name_match.group(1) if name_match else "Facebook User"
            results.append(self._make_lead(
                tenant_id=tenant_id,
                name=name,
                source_url=post.get("id", f"fb_{uuid4()}"),
                source="facebook",
                title=text[:200],
                enrichment={"post": post}
            ))
        return results

    async def _fetch_brightdata(self, tenant_id: UUID, limit: int, keyword: str = "marketing") -> List[LeadRecord]:
        url = "https://api.brightdata.com/facebook/search"
        params = {"q": keyword, "limit": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params, headers={"Authorization": f"Bearer {self.bright_key}"})
            resp.raise_for_status()
            data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append(self._make_lead(
                tenant_id=tenant_id,
                name=item.get("name", "Unknown"),
                source_url=item.get("url", f"fb_{uuid4()}"),
                source="facebook",
                title=item.get("about", ""),
                enrichment={"facebook_profile": item}
            ))
        return results

# ===========================
# 6. Google Maps Scraper
# ===========================
class GoogleMapsScraper(BaseSocialScraper):
    """Free (Google Maps API) or paid (Apify/Bright Data)."""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mode = config.get("mode", "api")  # api, apify, brightdata
        self.api_key = config.get("api_key") or os.getenv("GOOGLE_MAPS_API_KEY")
        self.apify_key = config.get("apify_key") or os.getenv("APIFY_API_KEY")
        self.bright_key = config.get("bright_key") or os.getenv("BRIGHT_DATA_API_KEY")

    async def fetch_leads(self, tenant_id: UUID, limit: int = 10, keyword: str = "restaurants", location: str = "New York", **kwargs) -> List[LeadRecord]:
        if self.mode == "api" and self.api_key:
            return await self._fetch_api(tenant_id, limit, keyword, location)
        elif self.mode == "apify" and self.apify_key:
            return await self._fetch_apify(tenant_id, limit, keyword, location)
        elif self.mode == "brightdata" and self.bright_key:
            return await self._fetch_brightdata(tenant_id, limit, keyword, location)
        else:
            return []

    async def _fetch_api(self, tenant_id: UUID, limit: int, keyword: str, location: str) -> List[LeadRecord]:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": f"{keyword} in {location}",
            "key": self.api_key,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        results = []
        for place in data.get("results", [])[:limit]:
            results.append(self._make_lead(
                tenant_id=tenant_id,
                name=place.get("name", "Unknown"),
                source_url=place.get("place_id", f"gmaps_{uuid4()}"),
                source="google_maps",
                title=place.get("formatted_address", ""),
                enrichment={"place": place}
            ))
        return results

    async def _fetch_apify(self, tenant_id: UUID, limit: int, keyword: str, location: str) -> List[LeadRecord]:
        from apify_client import ApifyClient
        client = ApifyClient(self.apify_key)
        run_input = {
            "searchString": f"{keyword} {location}",
            "maxResults": min(limit, 20),
        }
        try:
            run = client.actor("apify/google-maps-scraper").call(run_input=run_input)
            items = client.dataset(run["defaultDatasetId"]).list_items().items
        except Exception:
            return []
        results = []
        for item in items:
            results.append(self._make_lead(
                tenant_id=tenant_id,
                name=item.get("name", "Unknown"),
                source_url=item.get("placeId", f"gmaps_{uuid4()}"),
                source="google_maps",
                title=item.get("address", ""),
                company=item.get("name"),
                enrichment={"place": item}
            ))
        return results

    async def _fetch_brightdata(self, tenant_id: UUID, limit: int, keyword: str, location: str) -> List[LeadRecord]:
        url = "https://api.brightdata.com/maps/search"
        params = {"keyword": keyword, "location": location, "limit": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params, headers={"Authorization": f"Bearer {self.bright_key}"})
            resp.raise_for_status()
            data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append(self._make_lead(
                tenant_id=tenant_id,
                name=item.get("name", "Unknown"),
                source_url=item.get("place_id", f"gmaps_{uuid4()}"),
                source="google_maps",
                title=item.get("address", ""),
                company=item.get("name"),
                enrichment={"place": item}
            ))
        return results

# ===========================
# 7. Social Analyzer (OpenRouter)
# ===========================
class SocialAnalyzer:
    """Analyzes posts, comments, reviews using OpenRouter (LLM)."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("openrouter_key") or os.getenv("OPENROUTER_API_KEY")
        self.model = config.get("model", "openai/gpt-3.5-turbo")
        self.timeout = config.get("timeout", 45)

    async def analyze(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Returns: {
            "buying_signals": list of detected signals,
            "sentiment": "positive"|"neutral"|"negative",
            "intent": "interested"|"not_interested"|"undecided",
            "summary": str,
            "actionable": bool
        }
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key missing")
        prompt = f"""
        Analyze the following social media post/review and extract:
        - Buying signals (e.g., "looking for", "need", "upgrade", "considering")
        - Sentiment (positive/neutral/negative)
        - Intent (interested, not_interested, undecided)
        - A one-sentence summary of the content.
        - Whether this person is likely a potential lead (actionable: true/false).

        Content: {text[:1500]}

        Return ONLY JSON with keys: buying_signals (list), sentiment, intent, summary, actionable.
        """
        import openai
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=300,
            timeout=self.timeout,
        )
        result = json.loads(response.choices[0].message.content)
        return result

# ===========================
# 8. Main Pipeline
# ===========================
async def run_scraping_pipeline(
    tenant_id: UUID,
    sources: List[str] = ["linkedin", "instagram", "facebook", "google_maps"],
    limit_per_source: int = 5,
    analyze: bool = True,
) -> List[LeadRecord]:
    """
    Run all selected scrapers, optionally analyze posts/comments/reviews.
    Returns list of all new leads (deduplicated by source_url).
    """
    all_leads = []
    configs = {
        "linkedin": {"mode": "playwright", "keyword": "cto"},
        "instagram": {"mode": "apify", "username": "google"},
        "facebook": {"mode": "graph", "page_id": "cocacola"},
        "google_maps": {"mode": "api", "keyword": "restaurants", "location": "New York"},
    }

    scrapers = {
        "linkedin": LinkedInScraper(configs["linkedin"]),
        "instagram": InstagramScraper(configs["instagram"]),
        "facebook": FacebookScraper(configs["facebook"]),
        "google_maps": GoogleMapsScraper(configs["google_maps"]),
    }

    # Run all scrapers concurrently
    tasks = []
    for source in sources:
        scraper = scrapers.get(source)
        if scraper:
            tasks.append(scraper.fetch_leads(tenant_id, limit=limit_per_source))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect leads
    for leads in results:
        if isinstance(leads, list):
            all_leads.extend(leads)
        else:
            print(f"Scraper error: {leads}")

    # Deduplicate by source_url
    seen = set()
    unique_leads = []
    for lead in all_leads:
        if lead.source_url not in seen:
            seen.add(lead.source_url)
            unique_leads.append(lead)

    # Analyze each lead's enrichment text if requested
    if analyze:
        analyzer = SocialAnalyzer({})
        for lead in unique_leads:
            # Extract text from enrichment_data
            text = ""
            if lead.source == "linkedin":
                text = lead.enrichment_data.get("linkedin_profile", {}).get("about", "")
            elif lead.source == "instagram":
                text = lead.enrichment_data.get("instagram_profile", {}).get("biography", "")
            elif lead.source == "facebook":
                text = lead.enrichment_data.get("post", {}).get("message", "")
            elif lead.source == "google_maps":
                text = lead.enrichment_data.get("place", {}).get("formatted_address", "")
            if text:
                try:
                    analysis = await analyzer.analyze(text)
                    lead.enrichment_data["analysis"] = analysis
                    # Update score based on intent
                    if analysis.get("actionable"):
                        lead.score += 30
                    if analysis.get("sentiment") == "positive":
                        lead.score += 20
                    if analysis.get("intent") == "interested":
                        lead.score += 25
                    lead.score = min(100, lead.score)
                    if lead.score >= 70:
                        lead.status = "qualified"
                except Exception as e:
                    print(f"Analysis failed for {lead.source_url}: {e}")

    return unique_leads

# ===========================
# 9. Integration with Your CRM
# ===========================
# Example function to insert leads into your SQLite database
async def save_leads_to_sqlite(leads: List[LeadRecord], db_path: str = "leads.db"):
    """Insert/update leads using your existing SQLite schema."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Create table if not exists (matching your contract)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            lead_id TEXT PRIMARY KEY,
            tenant_id TEXT,
            name TEXT,
            email TEXT,
            phone TEXT,
            company TEXT,
            title TEXT,
            source TEXT,
            source_url TEXT UNIQUE,
            crawled_at TEXT,
            enrichment_data TEXT,
            score REAL,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    for lead in leads:
        cursor.execute("""
            INSERT OR IGNORE INTO leads (
                lead_id, tenant_id, name, email, phone, company, title,
                source, source_url, crawled_at, enrichment_data, score, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(lead.lead_id), str(lead.tenant_id), lead.name, lead.email,
            lead.phone, lead.company, lead.title, lead.source, lead.source_url,
            lead.crawled_at.isoformat(), json.dumps(lead.enrichment_data),
            lead.score, lead.status,
            lead.created_at.isoformat(), lead.updated_at.isoformat()
        ))
    conn.commit()
    conn.close()

# ===========================
# 10. Usage Example (in your test_ui.py)
# ===========================
async def main():
    from uuid import uuid4
    tenant_id = uuid4()  # replace with your tenant
    leads = await run_scraping_pipeline(tenant_id, sources=["linkedin", "instagram"], limit_per_source=3, analyze=True)
    print(f"Fetched {len(leads)} leads")
    await save_leads_to_sqlite(leads)
    for lead in leads:
        print(f"{lead.name} - Score: {lead.score} - Status: {lead.status}")

if __name__ == "__main__":
    asyncio.run(main())
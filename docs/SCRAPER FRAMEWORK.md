1. Scraper Architecture
1.1 Framework Overview
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SCRAPER FRAMEWORK ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    ORCHESTRATION LAYER                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Scheduler  │  │  Coordinator│  │  Manager    │  │  Monitor  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    STRATEGY LAYER                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Apify      │  │   HTTP      │  │  Playwright │  │   RSS     │  │  │
│  │  │  Strategy   │  │  Strategy   │  │   Strategy  │  │  Strategy │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   API       │  │  Webhook    │  │  Fallback   │  │  Retry    │  │  │
│  │  │   Strategy  │  │  Strategy   │  │  Strategy   │  │  Strategy │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    PARSING LAYER                                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  HTML       │  │   JSON      │  │   XML       │  │  CSV      │  │  │
│  │  │  Parser     │  │   Parser    │  │   Parser    │  │  Parser   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    POST-PROCESSING LAYER                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Normalize  │  │  Validate   │  │  Enrich     │  │  Store    │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
1.2 Core Components
python
# scraper_engine.py (Existing - Extended)
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import hashlib

class ScraperType(Enum):
    APIFY = "apify"
    HTTP = "http"
    PLAYWRIGHT = "playwright"
    RSS = "rss"
    API = "api"
    WEBHOOK = "webhook"

class ScraperStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    THROTTLED = "throttled"

@dataclass
class SourceConfig:
    source_id: str
    name: str
    type: ScraperType
    domain: str
    config: Dict
    schedule: str
    enabled: bool = True
    priority: int = 0
    timeout: int = 30
    retry_count: int = 3
    throttle_limit: int = 10
    throttle_period: int = 60
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

@dataclass
class ScrapeResult:
    source_id: str
    items: List[Dict]
    metadata: Dict
    status: ScraperStatus
    error: Optional[str] = None
    execution_time: float = 0.0
    item_count: int = 0
    items_hash: str = ""

class ScraperEngine:
    def __init__(self):
        self.sources: Dict[str, SourceConfig] = {}
        self.strategies: Dict[ScraperType, ScraperStrategy] = {}
        self.status_cache: Dict[str, ScraperStatus] = {}
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """Initialize available scraping strategies"""
        self.strategies[ScraperType.APIFY] = ApifyStrategy()
        self.strategies[ScraperType.HTTP] = HTTPStrategy()
        self.strategies[ScraperType.PLAYWRIGHT] = PlaywrightStrategy()
        self.strategies[ScraperType.RSS] = RSSStrategy()
        self.strategies[ScraperType.API] = APIStrategy()
        self.strategies[ScraperType.WEBHOOK] = WebhookStrategy()
    
    def register_source(self, config: SourceConfig) -> None:
        """Register a new data source"""
        self.sources[config.source_id] = config
        
    def configure_source(self, source_id: str, config: Dict) -> None:
        """Update source configuration"""
        if source_id in self.sources:
            current = self.sources[source_id]
            for key, value in config.items():
                if hasattr(current, key):
                    setattr(current, key, value)
    
    async def scrape(self, source_id: str) -> ScrapeResult:
        """Execute scraping for a specific source"""
        if source_id not in self.sources:
            raise ValueError(f"Source not found: {source_id}")
        
        source = self.sources[source_id]
        
        if not source.enabled:
            return ScrapeResult(
                source_id=source_id,
                items=[],
                metadata={"enabled": False},
                status=ScraperStatus.IDLE
            )
        
        strategy = self.strategies.get(source.type)
        if not strategy:
            raise ValueError(f"No strategy for type: {source.type}")
        
        start_time = time.time()
        
        try:
            # Apply throttling
            await self._apply_throttle(source_id)
            
            # Execute scrape
            result = await strategy.scrape(source)
            
            # Apply fallback strategy if needed
            if result.status == ScraperStatus.FAILED:
                fallback_result = await self._apply_fallback(source, result)
                if fallback_result:
                    result = fallback_result
            
            # Post-process results
            if result.status == ScraperStatus.COMPLETED:
                result = await self._post_process(result)
            
            result.execution_time = time.time() - start_time
            
        except Exception as e:
            result = ScrapeResult(
                source_id=source_id,
                items=[],
                metadata={"error": str(e)},
                status=ScraperStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time
            )
        
        return result
    
    async def schedule_scrape(self, source_id: str, schedule: str) -> None:
        """Schedule periodic scraping for a source"""
        if source_id not in self.sources:
            raise ValueError(f"Source not found: {source_id}")
        
        # Store schedule in database
        await self._save_schedule(source_id, schedule)
        
        # Schedule Celery task
        celery_app.send_task(
            'tasks.scrape_source',
            args=[source_id],
            schedule=schedule
        )
    
    async def get_status(self, source_id: str) -> ScraperStatus:
        """Get current status of a source"""
        return self.status_cache.get(source_id, ScraperStatus.IDLE)
    
    async def _apply_throttle(self, source_id: str) -> None:
        """Apply throttling limits"""
        key = f"throttle:{source_id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, source.throttle_period)
        elif count > source.throttle_limit:
            raise ThrottleError(f"Throttle limit exceeded for {source_id}")
    
    async def _apply_fallback(self, source: SourceConfig, result: ScrapeResult) -> Optional[ScrapeResult]:
        """Apply fallback strategy"""
        if source.type == ScraperType.PLAYWRIGHT:
            # Fallback from Playwright to HTTP
            http_strategy = self.strategies[ScraperType.HTTP]
            return await http_strategy.scrape(source)
        elif source.type == ScraperType.APIFY:
            # Fallback from Apify to HTTP
            http_strategy = self.strategies[ScraperType.HTTP]
            return await http_strategy.scrape(source)
        return None
    
    async def _post_process(self, result: ScrapeResult) -> ScrapeResult:
        """Post-process scraped data"""
        # Add hash for deduplication
        items_hash = hashlib.md5(json.dumps(result.items).encode()).hexdigest()
        result.items_hash = items_hash
        
        # Normalize data
        normalized_items = []
        for item in result.items:
            normalized = await self._normalize_item(item)
            if normalized:
                normalized_items.append(normalized)
        
        result.items = normalized_items
        result.item_count = len(normalized_items)
        
        return result
    
    async def _normalize_item(self, item: Dict) -> Optional[Dict]:
        """Normalize a scraped item"""
        # This would integrate with AI processor
        # For now, just pass through
        return item
2. Scraping Strategies
2.1 Apify Strategy
python
# apify_strategy.py
from typing import Dict, List, Optional
import asyncio
from apify_client import ApifyClient

class ApifyStrategy(ScraperStrategy):
    def __init__(self):
        self.client = ApifyClient(API_KEY)
        self.actor_cache = {}
        self.max_retries = 3
    
    async def scrape(self, source: SourceConfig) -> ScrapeResult:
        """Execute Apify actor"""
        
        # Prepare input
        input_data = source.config.get("input", {})
        actor_id = source.config.get("actor_id")
        
        if not actor_id:
            raise ValueError("Apify actor_id required")
        
        try:
            # Run actor
            run = await self._run_actor(actor_id, input_data)
            
            # Poll for completion
            result = await self._wait_for_completion(run)
            
            if result.get("status") == "SUCCEEDED":
                items = await self._get_items(run["id"])
                return ScrapeResult(
                    source_id=source.source_id,
                    items=items,
                    metadata={"run_id": run["id"]},
                    status=ScraperStatus.COMPLETED
                )
            else:
                return ScrapeResult(
                    source_id=source.source_id,
                    items=[],
                    metadata={"run_id": run["id"], "status": result.get("status")},
                    status=ScraperStatus.FAILED,
                    error=result.get("errorMessage")
                )
                
        except Exception as e:
            return ScrapeResult(
                source_id=source.source_id,
                items=[],
                metadata={},
                status=ScraperStatus.FAILED,
                error=str(e)
            )
    
    async def _run_actor(self, actor_id: str, input_data: Dict) -> Dict:
        """Run an Apify actor"""
        # Check if actor is cached
        if actor_id in self.actor_cache:
            actor = self.actor_cache[actor_id]
        else:
            actor = self.client.actor(actor_id)
            self.actor_cache[actor_id] = actor
        
        return await actor.start(**input_data)
    
    async def _wait_for_completion(self, run: Dict, timeout: int = 300) -> Dict:
        """Wait for actor to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = await self.client.run(run["id"]).get()
            
            if status.get("status") in ["SUCCEEDED", "FAILED"]:
                return status
            
            await asyncio.sleep(5)
        
        return {"status": "TIMEOUT"}
    
    async def _get_items(self, run_id: str) -> List[Dict]:
        """Get items from actor run"""
        items = []
        async for item in self.client.dataset(run_id).iterate_items():
            items.append(item)
        return items

    async def estimate_cost(self, source: SourceConfig) -> float:
        """Estimate Apify cost"""
        # Based on actor consumption
        default_cost = 0.01  # $0.01 per run
        return source.config.get("estimated_cost", default_cost)
2.2 HTTP Strategy
python
# http_strategy.py
from typing import Dict, List, Optional
import aiohttp
import asyncio
from curl_cffi import requests

class HTTPStrategy(ScraperStrategy):
    def __init__(self):
        self.session = None
        self.max_retries = 5
        self.timeout = 30
        self.impersonate = "chrome"
    
    async def scrape(self, source: SourceConfig) -> ScrapeResult:
        """Execute HTTP scraping"""
        
        url = source.config.get("url")
        if not url:
            raise ValueError("URL required for HTTP scraping")
        
        # Build request
        method = source.config.get("method", "GET")
        headers = source.config.get("headers", {})
        params = source.config.get("params", {})
        data = source.config.get("data", {})
        
        # Add user agent
        headers["User-Agent"] = source.user_agent
        
        try:
            # Execute request with retries
            response = await self._execute_with_retry(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                retries=source.retry_count
            )
            
            # Parse response
            items = await self._parse_response(response, source.config)
            
            return ScrapeResult(
                source_id=source.source_id,
                items=items,
                metadata={
                    "url": url,
                    "status_code": response.status_code,
                    "size": len(response.content)
                },
                status=ScraperStatus.COMPLETED
            )
            
        except Exception as e:
            return ScrapeResult(
                source_id=source.source_id,
                items=[],
                metadata={"url": url},
                status=ScraperStatus.FAILED,
                error=str(e)
            )
    
    async def _execute_with_retry(
        self,
        method: str,
        url: str,
        headers: Dict,
        params: Dict,
        data: Dict,
        retries: int
    ) -> Any:
        """Execute request with retry logic"""
        last_error = None
        
        for attempt in range(retries):
            try:
                response = await self._execute_request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data
                )
                
                if response.status_code == 200:
                    return response
                elif response.status_code >= 500:
                    # Server error, retry with backoff
                    await asyncio.sleep(2 ** attempt)
                    continue
                elif response.status_code == 429:
                    # Rate limited, retry with backoff
                    retry_after = int(response.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                last_error = e
                await asyncio.sleep(2 ** attempt)
        
        raise last_error or Exception("Max retries exceeded")
    
    async def _execute_request(
        self,
        method: str,
        url: str,
        headers: Dict,
        params: Dict,
        data: Dict
    ) -> Any:
        """Execute HTTP request using curl_cffi"""
        
        if method.upper() == "GET":
            response = requests.get(
                url,
                headers=headers,
                params=params,
                impersonate=self.impersonate,
                timeout=self.timeout
            )
        elif method.upper() == "POST":
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=data,
                impersonate=self.impersonate,
                timeout=self.timeout
            )
        else:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=data,
                impersonate=self.impersonate,
                timeout=self.timeout
            )
        
        return response
2.3 Playwright Strategy
python
# playwright_strategy.py
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Browser, Page
import asyncio

class PlaywrightStrategy(ScraperStrategy):
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.max_retries = 3
        self.default_timeout = 30000
        self.viewport = {"width": 1920, "height": 1080}
    
    async def initialize(self):
        """Initialize Playwright browser"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox']
            )
    
    async def scrape(self, source: SourceConfig) -> ScrapeResult:
        """Execute Playwright scraping"""
        
        url = source.config.get("url")
        if not url:
            raise ValueError("URL required for Playwright scraping")
        
        await self.initialize()
        
        try:
            page = await self.browser.new_page(viewport=self.viewport)
            
            # Navigate to URL
            await page.goto(url, timeout=self.default_timeout)
            
            # Wait for content
            await self._wait_for_content(page, source.config)
            
            # Extract data
            items = await self._extract_data(page, source.config)
            
            # Close page
            await page.close()
            
            return ScrapeResult(
                source_id=source.source_id,
                items=items,
                metadata={"url": url},
                status=ScraperStatus.COMPLETED
            )
            
        except Exception as e:
            return ScrapeResult(
                source_id=source.source_id,
                items=[],
                metadata={"url": url},
                status=ScraperStatus.FAILED,
                error=str(e)
            )
    
    async def _wait_for_content(self, page: Page, config: Dict):
        """Wait for content to load"""
        selectors = config.get("wait_selectors", [])
        timeout = config.get("wait_timeout", 10000)
        
        for selector in selectors:
            await page.wait_for_selector(selector, timeout=timeout)
        
        # Wait for network idle
        await page.wait_for_load_state("networkidle")
    
    async def _extract_data(self, page: Page, config: Dict) -> List[Dict]:
        """Extract data from page"""
        items = []
        
        # Get extraction config
        extraction_config = config.get("extraction", {})
        
        if extraction_config.get("type") == "list":
            items = await self._extract_list(page, extraction_config)
        elif extraction_config.get("type") == "single":
            items = await self._extract_single(page, extraction_config)
        else:
            # Custom extraction script
            items = await page.evaluate(extraction_config.get("script"))
        
        return items
    
    async def _extract_list(self, page: Page, config: Dict) -> List[Dict]:
        """Extract list of items"""
        items = []
        item_selector = config.get("item_selector")
        
        if not item_selector:
            return items
        
        item_elements = await page.query_selector_all(item_selector)
        
        for element in item_elements:
            item = {}
            for field, selector in config.get("fields", {}).items():
                try:
                    if selector.get("type") == "text":
                        value = await element.text_content(selector.get("selector"))
                    elif selector.get("type") == "attribute":
                        value = await element.get_attribute(
                            selector.get("selector"),
                            selector.get("attribute")
                        )
                    elif selector.get("type") == "html":
                        value = await element.inner_html(selector.get("selector"))
                    else:
                        value = await element.text_content(selector.get("selector"))
                    
                    item[field] = value.strip() if value else None
                    
                except Exception:
                    item[field] = None
            
            items.append(item)
        
        return items
3. Data Normalization
3.1 Domain Normalizers
python
# normalizers.py
from typing import Dict, List, Optional
from datetime import datetime
import re

class DomainNormalizer:
    def __init__(self, domain: str):
        self.domain = domain
        self.rules = self._get_rules()
    
    def normalize(self, raw_data: Dict) -> Dict:
        """Normalize data for a specific domain"""
        
        normalized = {
            "source": raw_data.get("source"),
            "source_id": raw_data.get("id"),
            "domain": self.domain,
            "title": self._normalize_title(raw_data),
            "description": self._normalize_description(raw_data),
            "url": raw_data.get("url"),
            "posted_date": self._normalize_date(raw_data.get("posted_date")),
            "expiry_date": self._normalize_date(raw_data.get("expiry_date")),
            "raw_data": raw_data
        }
        
        # Apply domain-specific normalization
        if self.domain == "jobs":
            normalized.update(self._normalize_job(raw_data))
        elif self.domain == "real_estate":
            normalized.update(self._normalize_real_estate(raw_data))
        elif self.domain == "vehicles":
            normalized.update(self._normalize_vehicle(raw_data))
        elif self.domain == "immigration":
            normalized.update(self._normalize_immigration(raw_data))
        elif self.domain == "education":
            normalized.update(self._normalize_education(raw_data))
        elif self.domain == "scholarships":
            normalized.update(self._normalize_scholarship(raw_data))
        
        # Clean and validate
        normalized = self._clean_data(normalized)
        
        return normalized
    
    def _normalize_job(self, raw: Dict) -> Dict:
        """Normalize job data"""
        return {
            "company_name": raw.get("company", "").strip(),
            "location": self._normalize_location(raw.get("location")),
            "salary": self._normalize_salary(raw.get("salary")),
            "visa_sponsorship": self._parse_boolean(raw.get("visa_sponsorship")),
            "remote_allowed": self._parse_boolean(raw.get("remote")),
            "skills": self._extract_skills(raw.get("description")),
            "experience_level": self._normalize_experience(raw.get("experience")),
            "education_level": self._normalize_education(raw.get("education"))
        }
    
    def _normalize_real_estate(self, raw: Dict) -> Dict:
        """Normalize real estate data"""
        return {
            "property_type": self._normalize_property_type(raw.get("type")),
            "transaction_type": self._normalize_transaction(raw.get("transaction")),
            "bedrooms": self._parse_int(raw.get("bedrooms")),
            "bathrooms": self._parse_int(raw.get("bathrooms")),
            "area_sqft": self._parse_float(raw.get("area")),
            "price": self._parse_float(raw.get("price")),
            "currency": self._normalize_currency(raw.get("currency")),
            "features": self._extract_features(raw.get("features"))
        }
    
    def _normalize_vehicle(self, raw: Dict) -> Dict:
        """Normalize vehicle data"""
        return {
            "make": raw.get("make", "").strip(),
            "model": raw.get("model", "").strip(),
            "year": self._parse_int(raw.get("year")),
            "mileage": self._parse_int(raw.get("mileage")),
            "transmission": self._normalize_transmission(raw.get("transmission")),
            "fuel_type": self._normalize_fuel(raw.get("fuel")),
            "price": self._parse_float(raw.get("price")),
            "currency": self._normalize_currency(raw.get("currency"))
        }
    
    def _normalize_immigration(self, raw: Dict) -> Dict:
        """Normalize immigration data"""
        return {
            "visa_type": raw.get("visa_type", "").strip(),
            "visa_category": raw.get("category", "").strip(),
            "country": raw.get("country", "").strip(),
            "processing_time": self._parse_int(raw.get("processing_time")),
            "requirements": self._extract_requirements(raw.get("requirements")),
            "deadline": self._normalize_date(raw.get("deadline"))
        }
    
    def _normalize_title(self, raw: Dict) -> str:
        """Normalize title"""
        title = raw.get("title", "")
        return title.strip()
    
    def _normalize_description(self, raw: Dict) -> str:
        """Normalize description"""
        desc = raw.get("description", "")
        # Clean HTML
        desc = re.sub(r'<[^>]+>', '', desc)
        # Clean extra whitespace
        desc = re.sub(r'\s+', ' ', desc)
        return desc.strip()
    
    def _normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        """Normalize date string to ISO format"""
        if not date_str:
            return None
        
        try:
            # Try common date formats
            formats = [
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%m/%d/%Y",
                "%b %d, %Y",
                "%d %b %Y",
                "%Y-%m-%dT%H:%M:%S%z"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat() + "Z"
                except ValueError:
                    continue
            
            # Try parsing with dateutil
            from dateutil import parser
            dt = parser.parse(date_str)
            return dt.isoformat() + "Z"
            
        except Exception:
            return None
    
    def _normalize_location(self, location: str) -> Dict:
        """Normalize location"""
        if not location:
            return {}
        
        # Try to parse location string
        parts = location.split(',')
        if len(parts) >= 2:
            return {
                "city": parts[0].strip(),
                "country": parts[-1].strip()
            }
        elif len(parts) == 1:
            return {"city": parts[0].strip()}
        
        return {"text": location}
    
    def _normalize_salary(self, salary: str) -> Dict:
        """Normalize salary"""
        if not salary:
            return {}
        
        # Try to extract numbers and currency
        numbers = re.findall(r'[\d,]+', salary)
        currencies = re.findall(r'[A-Z]{3}', salary)
        
        if numbers:
            min_salary = max_salary = None
            if len(numbers) >= 2:
                min_salary = float(numbers[0].replace(',', ''))
                max_salary = float(numbers[1].replace(',', ''))
            else:
                min_salary = float(numbers[0].replace(',', ''))
            
            return {
                "min": min_salary,
                "max": max_salary or min_salary,
                "currency": currencies[0] if currencies else "USD"
            }
        
        return {}
3.2 Validation Rules
python
# validation.py
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, validator

class OpportunityValidation(BaseModel):
    """Validation schema for opportunities"""
    
    source: str
    source_id: str
    domain: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    posted_date: Optional[str] = None
    expiry_date: Optional[str] = None
    
    @validator('title')
    def title_not_empty(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Title must be at least 3 characters')
        return v.strip()
    
    @validator('source_id')
    def source_id_not_empty(cls, v):
        if not v:
            raise ValueError('Source ID is required')
        return v
    
    @validator('domain')
    def domain_valid(cls, v):
        valid_domains = ['jobs', 'real_estate', 'vehicles', 'immigration', 'education', 'scholarships']
        if v not in valid_domains:
            raise ValueError(f'Invalid domain: {v}')
        return v
    
    @validator('url')
    def url_valid(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Invalid URL format')
        return v
    
    @validator('posted_date')
    def posted_date_valid(cls, v):
        if v:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Invalid date format')
        return v

class DomainValidation:
    """Domain-specific validation rules"""
    
    @staticmethod
    def validate_job(data: Dict) -> bool:
        """Validate job-specific fields"""
        required = ['company_name', 'location']
        for field in required:
            if not data.get(field):
                return False
        
        # Validate location
        location = data.get('location', {})
        if not location.get('country') and not location.get('city'):
            return False
        
        return True
    
    @staticmethod
    def validate_real_estate(data: Dict) -> bool:
        """Validate real estate-specific fields"""
        required = ['property_type', 'transaction_type', 'price']
        for field in required:
            if not data.get(field):
                return False
        
        # Validate price
        if data.get('price', 0) <= 0:
            return False
        
        return True
    
    @staticmethod
    def validate_vehicle(data: Dict) -> bool:
        """Validate vehicle-specific fields"""
        required = ['make', 'model', 'year']
        for field in required:
            if not data.get(field):
                return False
        
        # Validate year
        year = data.get('year')
        if year and (year < 1900 or year > datetime.now().year + 1):
            return False
        
        return True
4. Deduplication Engine
python
# dedupe_engine.py (Existing - Extended)
from typing import Dict, List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import hashlib
import jellyfish

class DedupeEngine:
    def __init__(self):
        self.similarity_threshold = 0.85
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.duplicates_cache = {}
    
    async def is_duplicate(self, opportunity: Dict) -> bool:
        """Check if opportunity is duplicate"""
        
        # Check source_id duplicate
        source_id = opportunity.get('source_id')
        if source_id:
            existing = await self._find_by_source_id(opportunity.get('source'), source_id)
            if existing:
                return True
        
        # Check title similarity
        title = opportunity.get('title', '')
        if title:
            similar = await self._find_similar_titles(title, opportunity.get('domain'))
            if similar:
                return True
        
        # Check fuzzy matching
        if await self._fuzzy_match(opportunity):
            return True
        
        return False
    
    async def resolve_duplicates(self, opportunities: List[Dict]) -> List[Dict]:
        """Resolve duplicate opportunities"""
        
        unique = []
        seen_ids = set()
        
        for opp in opportunities:
            key = self._generate_key(opp)
            if key not in seen_ids:
                # Check for partial duplicates
                is_dup = False
                for existing in unique:
                    if self._is_similar(opp, existing):
                        is_dup = True
                        # Merge duplicates (keep best data)
                        merged = self._merge_opportunities(existing, opp)
                        unique[unique.index(existing)] = merged
                        break
                
                if not is_dup:
                    unique.append(opp)
                    seen_ids.add(key)
        
        return unique
    
    def _generate_key(self, opportunity: Dict) -> str:
        """Generate unique key for opportunity"""
        # Combine source + source_id or title + domain
        if opportunity.get('source_id'):
            key = f"{opportunity.get('source', '')}:{opportunity.get('source_id', '')}"
        else:
            key = f"{opportunity.get('domain', '')}:{opportunity.get('title', '')}"
        
        return hashlib.md5(key.lower().encode()).hexdigest()
    
    def _is_similar(self, opp1: Dict, opp2: Dict) -> bool:
        """Check if two opportunities are similar"""
        # Title similarity
        title1 = opp1.get('title', '')
        title2 = opp2.get('title', '')
        
        if not title1 or not title2:
            return False
        
        # Jaccard similarity
        similarity = self._jaccard_similarity(title1, title2)
        
        if similarity > self.similarity_threshold:
            # Check domain-specific fields
            domain = opp1.get('domain')
            if domain == 'jobs':
                return self._compare_jobs(opp1, opp2)
            elif domain == 'real_estate':
                return self._compare_real_estate(opp1, opp2)
            else:
                return similarity > self.similarity_threshold
        
        return False
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _fuzzy_match(self, opportunity: Dict) -> bool:
        """Fuzzy string matching for duplicates"""
        title = opportunity.get('title', '')
        if not title:
            return False
        
        # Get recent opportunities from same domain
        recent = await self._get_recent_opportunities(
            opportunity.get('domain'),
            limit=100
        )
        
        for opp in recent:
            similarity = jellyfish.levenshtein_distance(
                title.lower(),
                opp.get('title', '').lower()
            )
            max_len = max(len(title), len(opp.get('title', '')))
            similarity_score = 1 - (similarity / max_len)
            
            if similarity_score > 0.85:
                return True
        
        return False
    
    def _merge_opportunities(self, opp1: Dict, opp2: Dict) -> Dict:
        """Merge two duplicate opportunities"""
        merged = opp1.copy()
        
        # Keep the best data
        for key in opp2:
            if key not in merged or not merged[key]:
                merged[key] = opp2[key]
            elif isinstance(merged[key], list) and isinstance(opp2[key], list):
                merged[key] = list(set(merged[key] + opp2[key]))
            elif isinstance(merged[key], dict) and isinstance(opp2[key], dict):
                merged[key] = {**merged[key], **opp2[key]}
        
        # Add metadata
        merged['_merged'] = True
        merged['_merged_from'] = [opp1.get('source_id'), opp2.get('source_id')]
        merged['_merged_at'] = datetime.utcnow().isoformat()
        
        return merged

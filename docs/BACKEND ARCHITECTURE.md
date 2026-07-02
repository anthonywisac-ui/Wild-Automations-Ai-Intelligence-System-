1. Backend Overview
1.1 Core Components
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      FastAPI Application                            │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐   │  │
│  │  │  Routers   │  │  Middleware│  │  Dependencies│  │  Models     │   │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └─────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Business Logic Layer                              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐   │  │
│  │  │  Services  │  │  Managers  │  │  Workers   │  │  Handlers   │   │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └─────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Data Access Layer                                 │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐   │  │
│  │  │   Repos    │  │   Models   │  │  Migrations│  │  Seeds      │   │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └─────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Infrastructure Layer                              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐   │  │
│  │  │  Database  │  │   Cache   │  │   Queue   │  │  Storage    │   │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └─────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
1.2 Technology Stack Details
Layer	Technology	Version	Purpose
Web Framework	FastAPI	0.104+	API development
ORM	SQLAlchemy	2.0+	Database ORM
Migration	Alembic	1.12+	Schema migrations
Task Queue	Celery	5.3+	Async tasks
Broker	Redis	7.0+	Message broker
Database	PostgreSQL	15+	Primary database
Vector	pgvector	0.5+	Vector operations
Cache	Redis	7.0+	Caching layer
Storage	S3	-	Object storage
Monitoring	Prometheus	2.45+	Metrics
Logging	ELK Stack	8.0+	Log aggregation
Tracing	Jaeger	1.50+	Distributed tracing
2. Core Services
2.1 API Service
FastAPI Application Structure
python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler

app = FastAPI(
    title="WildAutomations API",
    version="1.0.0",
    description="Opportunity Intelligence Platform API",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://wildautomations.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["wildautomations.com", "api.wildautomations.com"]
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Router Registration
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
app.include_router(search_router, prefix="/api/v1/search", tags=["search"])
app.include_router(opportunity_router, prefix="/api/v1/opportunities", tags=["opportunities"])
app.include_router(notification_router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(webhook_router, prefix="/api/v1/webhooks", tags=["webhooks"])
Dependency Injection
python
# dependencies.py
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

async def get_current_user(request: Request) -> User:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await auth_service.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

async def get_db_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

# Type annotations
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
2.2 Authentication Service
python
# services/auth_service.py
class AuthService:
    def __init__(self, user_repo: UserRepository, token_manager: TokenManager):
        self.user_repo = user_repo
        self.token_manager = token_manager

    async def register(self, email: str, password: str, phone: str) -> User:
        # Validate input
        if not self._validate_email(email):
            raise ValidationError("Invalid email")
        if not self._validate_password(password):
            raise ValidationError("Password too weak")
        
        # Check existing user
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError("User already exists")
        
        # Hash password
        hashed = self._hash_password(password)
        
        # Create user
        user = User(
            email=email,
            password_hash=hashed,
            phone=phone,
            created_at=datetime.utcnow()
        )
        
        # Save user
        user = await self.user_repo.create(user)
        
        # Create default profile
        await self._create_default_profile(user.id)
        
        # Send welcome email
        await self._send_welcome_email(user.email)
        
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid credentials")
        
        if not self._verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid credentials")
        
        # Generate tokens
        access_token = self.token_manager.create_access_token(user.id)
        refresh_token = self.token_manager.create_refresh_token(user.id)
        
        # Update last login
        await self.user_repo.update_last_login(user.id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600
        )
2.3 Search Service
python
# services/search_service.py
class SearchService:
    def __init__(
        self,
        search_repo: SearchRepository,
        embedding_service: EmbeddingService,
        cache_service: CacheService,
        scoring_service: ScoringService
    ):
        self.search_repo = search_repo
        self.embedding_service = embedding_service
        self.cache_service = cache_service
        self.scoring_service = scoring_service

    async def search(self, query: str, filters: Dict, user_id: str) -> SearchResult:
        # Check cache
        cache_key = self._generate_cache_key(query, filters)
        cached = await self.cache_service.get(cache_key)
        if cached:
            return SearchResult.from_dict(cached)
        
        # Detect intent
        intent = await self._detect_intent(query)
        
        # Generate embedding
        embedding = await self.embedding_service.generate(query)
        
        # Perform hybrid search
        results = await self._hybrid_search(
            query=query,
            embedding=embedding,
            filters=filters,
            intent=intent
        )
        
        # Score and rank
        ranked = await self.scoring_service.score_results(results, user_id)
        
        # Cache results
        await self.cache_service.set(
            cache_key,
            ranked.to_dict(),
            ttl=60  # 1 minute
        )
        
        return ranked

    async def _hybrid_search(self, query: str, embedding: List[float], 
                           filters: Dict, intent: Intent) -> List[Opportunity]:
        # Semantic search
        semantic_results = await self.search_repo.vector_search(
            embedding=embedding,
            filters=filters,
            limit=100
        )
        
        # Keyword search
        keyword_results = await self.search_repo.keyword_search(
            query=query,
            filters=filters,
            limit=100
        )
        
        # Combine and deduplicate
        combined = self._combine_results(semantic_results, keyword_results)
        
        return combined
2.4 AI Service
python
# services/ai_service.py
class AIService:
    def __init__(
        self,
        model_registry: ModelRegistry,
        prompt_service: PromptService,
        context_service: ContextService
    ):
        self.model_registry = model_registry
        self.prompt_service = prompt_service
        self.context_service = context_service

    async def process_query(self, query: str, user_id: str) -> AIResponse:
        # Get user context
        context = await self.context_service.get_user_context(user_id)
        
        # Detect intent
        intent = await self._detect_intent(query, context)
        
        # Select appropriate model
        model = self.model_registry.select_model(intent)
        
        # Build prompt
        prompt = await self.prompt_service.build_prompt(
            query=query,
            intent=intent,
            context=context
        )
        
        # Execute AI request
        response = await model.generate(prompt)
        
        # Update context
        await self.context_service.update_context(user_id, query, response)
        
        return AIResponse(
            text=response.text,
            intent=intent,
            model=model.name,
            confidence=response.confidence
        )
3. Background Workers
3.1 Celery Configuration
python
# celery_app.py
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    'wildautomations',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100
)

# Schedule tasks
celery_app.conf.beat_schedule = {
    'scrape-sources': {
        'task': 'tasks.scrape_sources',
        'schedule': crontab(minute='*/30'),
        'args': ()
    },
    'cleanup-expired': {
        'task': 'tasks.cleanup_expired_opportunities',
        'schedule': crontab(hour=0, minute=0),
    },
    'send-notifications': {
        'task': 'tasks.process_notifications',
        'schedule': crontab(minute='*/5'),
    },
    'generate-embeddings': {
        'task': 'tasks.generate_embeddings',
        'schedule': crontab(minute='*/15'),
    }
}
3.2 Task Definitions
python
# tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(name='tasks.scrape_sources')
def scrape_sources():
    """Scrape all configured sources"""
    logger.info("Starting source scraping")
    
    sources = SourceConfig.get_active_sources()
    
    for source in sources:
        try:
            scrape_source.delay(source.id)
        except Exception as e:
            logger.error(f"Failed to schedule scrape for {source.id}: {e}")

@shared_task(name='tasks.scrape_source', bind=True, max_retries=3)
def scrape_source(self, source_id: str):
    """Scrape a specific source"""
    logger.info(f"Scraping source: {source_id}")
    
    try:
        source = SourceConfig.get(source_id)
        scraper = ScraperEngine.get_scraper(source.type)
        
        # Execute scrape
        result = scraper.scrape(source)
        
        # Process results
        if result.success:
            process_scraped_data.delay(result.data)
        else:
            # Retry with backoff
            self.retry(countdown=60 * (2 ** self.request.retries))
            
    except Exception as e:
        logger.error(f"Scrape failed for {source_id}: {e}")
        self.retry(countdown=60 * (2 ** self.request.retries))

@shared_task(name='tasks.process_scraped_data')
def process_scraped_data(raw_data: dict):
    """Process scraped data through AI pipeline"""
    logger.info(f"Processing scraped data: {len(raw_data)} items")
    
    ai_processor = AIProcessor()
    dedupe_engine = DedupeEngine()
    
    for item in raw_data:
        # Extract structured data
        extracted = ai_processor.extract(item)
        
        # Normalize
        normalized = ai_processor.normalize(extracted)
        
        # Validate
        validated = ai_processor.validate(normalized)
        
        # Deduplicate
        if not dedupe_engine.is_duplicate(validated):
            # Save to database
            save_opportunity.delay(validated)
        else:
            logger.info(f"Duplicate found for {validated.get('title')}")

@shared_task(name='tasks.process_notifications')
def process_notifications():
    """Process pending notifications"""
    logger.info("Processing notifications")
    
    notification_service = NotificationService()
    pending = notification_service.get_pending_notifications()
    
    for notification in pending:
        try:
            notification_service.deliver(notification)
        except Exception as e:
            logger.error(f"Notification delivery failed: {e}")
            notification_service.mark_failed(notification.id)
4. API Implementation
4.1 Search Routes
python
# routes/search.py
from fastapi import APIRouter, Depends, Query
from typing import Optional

router = APIRouter()

@router.post("/search")
@limiter.limit("100/minute")
async def search(
    request: Request,
    search_request: SearchRequest,
    current_user: CurrentUser,
    db: DBSession
) -> SearchResponse:
    """Search for opportunities"""
    
    search_service = SearchService(db)
    
    try:
        results = await search_service.search(
            query=search_request.query,
            filters=search_request.filters,
            user_id=current_user.id
        )
        
        # Log search
        await search_service.log_search(
            user_id=current_user.id,
            query=search_request.query,
            result_count=len(results.items)
        )
        
        return SearchResponse(
            items=results.items,
            total=results.total,
            pagination=results.pagination,
            metadata=results.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suggestions")
async def get_suggestions(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20)
) -> List[str]:
    """Get search suggestions"""
    
    suggestion_service = SuggestionService()
    suggestions = await suggestion_service.get_suggestions(q, limit)
    return suggestions
4.2 Webhook Routes
python
# routes/webhooks.py
from fastapi import APIRouter, Request, BackgroundTasks

router = APIRouter()

@router.post("/apify-webhook")
async def apify_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> dict:
    """Handle Apify webhook callback"""
    
    data = await request.json()
    
    # Process in background
    background_tasks.add_task(process_apify_data, data)
    
    return {"status": "received"}

@router.post("/whatsapp-webhook")
async def whatsapp_webhook(request: Request) -> dict:
    """Handle WhatsApp webhook"""
    
    data = await request.json()
    
    # Process WhatsApp message
    whatsapp_service = WhatsAppService()
    await whatsapp_service.process_message(data)
    
    return {"status": "processed"}
5. Error Handling
5.1 Global Exception Handler
python
# middleware/error_handler.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for all unhandled exceptions"""
    
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred",
                "request_id": request.state.request_id
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for validation errors"""
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Invalid request data",
                "details": exc.errors()
            }
        }
    )

# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
5.2 Business Exceptions
python
# exceptions.py
class BusinessException(Exception):
    """Base class for business exceptions"""
    pass

class ValidationError(BusinessException):
    """Validation error"""
    pass

class AuthenticationError(BusinessException):
    """Authentication error"""
    pass

class AuthorizationError(BusinessException):
    """Authorization error"""
    pass

class NotFoundError(BusinessException):
    """Resource not found"""
    pass

class ConflictError(BusinessException):
    """Resource conflict"""
    pass

class RateLimitError(BusinessException):
    """Rate limit exceeded"""
    pass
6. Performance Optimization
6.1 Caching Strategy
python
# services/cache_service.py
class CacheService:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def get_or_set(self, key: str, func: Callable, ttl: int = 60):
        """Get from cache or execute function and cache"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        
        value = await func()
        await self.redis.setex(key, ttl, json.dumps(value))
        return value

    def cache_decorator(ttl: int = 60):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                cache_key = f"{func.__name__}:{args}:{kwargs}"
                return await cache_service.get_or_set(cache_key, lambda: func(*args, **kwargs), ttl)
            return wrapper
        return decorator
6.2 Database Optimization
python
# repositories/base_repository.py
class BaseRepository:
    def __init__(self, session):
        self.session = session

    async def bulk_insert(self, items: List, chunk_size: int = 1000):
        """Efficient bulk insert"""
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            await self.session.bulk_save_objects(chunk)
            await self.session.commit()

    async def paginated_query(self, query, page: int, size: int):
        """Efficient pagination"""
        offset = (page - 1) * size
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        items = await self.session.execute(query.offset(offset).limit(size))
        return items, total

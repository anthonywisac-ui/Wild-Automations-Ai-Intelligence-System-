1. AI System Overview
1.1 AI Components
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AI ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    AI ORCHESTRATION LAYER                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Model      │  │  Prompt     │  │  Context    │  │  Rate     │  │  │
│  │  │  Router     │  │  Engine     │  │  Manager    │  │  Limiter  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    AI PROCESSING PIPELINE                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Intent     │  │  Entity     │  │  Response   │  │  Embedding │  │  │
│  │  │  Detection  │──►│  Extraction │──►│  Generation│──►│  Generation│  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    MODEL ADAPTERS                                     │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │  │
│  │  │ Gemini  │  │ Claude  │  │   GPT   │  │  Groq   │  │ Mistral │   │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │  │
│  │  ┌─────────┐  ┌─────────┐                                         │  │
│  │  │Cerebras │  │ Ollama  │                                         │  │
│  │  └─────────┘  └─────────┘                                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
1.2 AI Model Registry
python
# models/model_registry.py
from enum import Enum
from typing import Dict, List, Optional

class ModelCapability(Enum):
    INTENT_DETECTION = "intent_detection"
    ENTITY_EXTRACTION = "entity_extraction"
    RESPONSE_GENERATION = "response_generation"
    EMBEDDING = "embedding"
    NORMALIZATION = "normalization"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"

class ModelProvider(Enum):
    GEMINI = "gemini"
    CLAUDE = "claude"
    GPT = "gpt"
    GROQ = "groq"
    MISTRAL = "mistral"
    CEREBRAS = "cerebras"
    OLLAMA = "ollama"

class AIModel:
    def __init__(
        self,
        provider: ModelProvider,
        model_name: str,
        capabilities: List[ModelCapability],
        cost_per_token: float,
        context_window: int,
        latency_ms: int,
        reliability: float,
        supported_languages: List[str],
        default_fallback: bool = False
    ):
        self.provider = provider
        self.model_name = model_name
        self.capabilities = capabilities
        self.cost_per_token = cost_per_token
        self.context_window = context_window
        self.latency_ms = latency_ms
        self.reliability = reliability
        self.supported_languages = supported_languages
        self.default_fallback = default_fallback
        self.usage_count = 0
        self.total_cost = 0.0

class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, AIModel] = {}
        self._initialize_models()
    
    def _initialize_models(self):
        # Gemini Models
        self.models["gemini-pro"] = AIModel(
            provider=ModelProvider.GEMINI,
            model_name="gemini-pro",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION
            ],
            cost_per_token=0.000001,
            context_window=32000,
            latency_ms=800,
            reliability=0.95,
            supported_languages=["en", "ar", "fr", "de", "es"]
        )
        
        # Claude Models
        self.models["claude-3-sonnet"] = AIModel(
            provider=ModelProvider.CLAUDE,
            model_name="claude-3-sonnet-20240229",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION
            ],
            cost_per_token=0.000003,
            context_window=200000,
            latency_ms=1200,
            reliability=0.98,
            supported_languages=["en", "ar", "fr", "de", "es"]
        )
        
        # GPT Models
        self.models["gpt-4o"] = AIModel(
            provider=ModelProvider.GPT,
            model_name="gpt-4o",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION
            ],
            cost_per_token=0.000005,
            context_window=128000,
            latency_ms=1000,
            reliability=0.97,
            supported_languages=["en", "ar", "fr", "de", "es"]
        )
        
        # Groq Models (Fast & Cheap)
        self.models["groq-mixtral"] = AIModel(
            provider=ModelProvider.GROQ,
            model_name="mixtral-8x7b-32768",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.CLASSIFICATION
            ],
            cost_per_token=0.0000005,
            context_window=32768,
            latency_ms=200,
            reliability=0.90,
            supported_languages=["en"]
        )
        
        # Mistral Models
        self.models["mistral-large"] = AIModel(
            provider=ModelProvider.MISTRAL,
            model_name="mistral-large-latest",
            capabilities=[
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION,
                ModelCapability.CLASSIFICATION
            ],
            cost_per_token=0.000002,
            context_window=32000,
            latency_ms=600,
            reliability=0.92,
            supported_languages=["en", "fr", "de", "es"]
        )
        
        # Cerebras (Cheapest)
        self.models["cerebras-gpt"] = AIModel(
            provider=ModelProvider.CEREBRAS,
            model_name="cerebras-gpt-13b",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.CLASSIFICATION
            ],
            cost_per_token=0.0000001,
            context_window=8192,
            latency_ms=300,
            reliability=0.88,
            supported_languages=["en"],
            default_fallback=True
        )
        
        # Ollama (Offline)
        self.models["ollama-mistral"] = AIModel(
            provider=ModelProvider.OLLAMA,
            model_name="mistral",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION
            ],
            cost_per_token=0.0,
            context_window=4096,
            latency_ms=1500,
            reliability=0.80,
            supported_languages=["en"]
        )
    
    def select_model(
        self,
        capability: ModelCapability,
        language: str = "en",
        max_tokens: int = 1000,
        max_cost: float = None,
        min_reliability: float = 0.85
    ) -> AIModel:
        """Select optimal model based on requirements"""
        
        candidates = [
            model for model in self.models.values()
            if capability in model.capabilities
            and language in model.supported_languages
            and model.reliability >= min_reliability
            and (max_cost is None or model.cost_per_token <= max_cost)
        ]
        
        if not candidates:
            # Use fallback model
            return self.get_fallback_model(capability)
        
        # Sort by cost (cheapest first)
        candidates.sort(key=lambda x: x.cost_per_token)
        
        # Check context window requirements
        candidates = [c for c in candidates if c.context_window >= max_tokens]
        
        return candidates[0]
    
    def get_fallback_model(self, capability: ModelCapability) -> AIModel:
        """Get fallback model when primary selection fails"""
        # Try default fallback models
        for model in self.models.values():
            if model.default_fallback and capability in model.capabilities:
                return model
        
        # Try Ollama (offline)
        for model in self.models.values():
            if model.provider == ModelProvider.OLLAMA and capability in model.capabilities:
                return model
        
        # Last resort: first available model
        for model in self.models.values():
            if capability in model.capabilities:
                return model
        
        raise ValueError(f"No model available for capability: {capability}")
2. Prompt Engineering
2.1 Prompt Templates
python
# prompt_engine.py
from typing import Dict, Any, Optional

class PromptEngine:
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        return {
            "intent_detection": """
                You are an intent detection system for an opportunity intelligence platform.
                
                User Query: {query}
                User Context: {context}
                
                Task: Identify the primary intent and extract key entities.
                
                Intents: search, filter, save, notify, compare, explain, help
                
                Domains: jobs, real_estate, vehicles, education, immigration, scholarships, all
                
                Output must be in JSON format:
                {{
                    "intent": "search",
                    "domains": ["jobs", "real_estate"],
                    "entities": {{
                        "location": "Germany",
                        "budget": {{
                            "min": 40000,
                            "max": 50000,
                            "currency": "AED"
                        }},
                        "visa_sponsorship": true,
                        "education": "Bachelor's in Data Science"
                    }},
                    "confidence": 0.95
                }}
            """,
            
            "entity_extraction": """
                You are an entity extraction system for opportunity intelligence.
                
                Text to analyze: {text}
                Domain: {domain}
                
                Extract all relevant entities and structure them according to the domain schema.
                
                Output must be in JSON format matching the domain schema:
                {schema}
                
                Only extract information that is explicitly stated or strongly implied.
                Set confidence scores for each extracted entity.
            """,
            
            "response_generation": """
                You are an AI assistant for an opportunity intelligence platform.
                
                User Query: {query}
                User Context: {context}
                Search Results: {results}
                Intent: {intent}
                
                Generate a helpful, concise, and personalized response.
                
                Guidelines:
                1. Be conversational and helpful
                2. Highlight the most relevant opportunities
                3. Include key details: title, location, price/salary
                4. Suggest follow-up actions
                5. Ask clarifying questions if needed
                6. Format for WhatsApp delivery (text-only, concise)
                
                Response should be:
                - For search: Summary + Top results + Next steps
                - For filter: Explain applied filters + Results
                - For save: Confirmation + Next steps
                - For compare: Comparison table (text-based) + Recommendation
            """,
            
            "opportunity_normalization": """
                You are an opportunity normalization system.
                
                Raw Data: {raw_data}
                Domain: {domain}
                Source: {source}
                
                Normalize the raw data into the standard opportunity schema.
                
                Schema: {schema}
                
                Important:
                1. Map all fields to the schema
                2. Convert dates to ISO 8601 UTC
                3. Normalize currencies to ISO 4217
                4. Clean and validate all text fields
                5. Calculate confidence scores
                6. Flag any uncertain or missing data
                
                Output in JSON format:
                {{
                    "normalized": {{...}},
                    "confidence": 0.92,
                    "warnings": ["missing field: salary_min"],
                    "source_fields": {{...}}
                }}
            """,
            
            "deduplication_check": """
                You are a deduplication system.
                
                New Opportunity: {new_opportunity}
                Existing Opportunities: {existing_opportunities}
                
                Determine if the new opportunity is a duplicate of any existing opportunity.
                
                Consider:
                1. Title similarity (threshold: 0.85)
                2. Description similarity (threshold: 0.75)
                3. Domain-specific fields
                4. Source and source_id match
                
                Output in JSON format:
                {{
                    "is_duplicate": false,
                    "matched_id": null,
                    "similarity_score": 0.45,
                    "explanation": "No duplicate found"
                }}
            """,
            
            "scoring": """
                You are a scoring system for opportunity matching.
                
                User Profile: {profile}
                Opportunity: {opportunity}
                Domain: {domain}
                
                Calculate match score for the following dimensions:
                1. Location match (0-100)
                2. Budget/Salary match (0-100)
                3. Skills/Requirements match (0-100)
                4. Education match (0-100)
                5. Experience match (0-100)
                6. Visa sponsorship match (0-100)
                7. Language match (0-100)
                
                Weights: {weights}
                
                Output in JSON format:
                {{
                    "overall_score": 0.87,
                    "dimensions": {{
                        "location": 0.95,
                        "budget": 0.82,
                        "skills": 0.88,
                        "education": 0.92,
                        "experience": 0.80,
                        "visa": 0.90,
                        "language": 0.85
                    }},
                    "confidence": 0.93,
                    "top_matches": ["location", "education"],
                    "suggestions": ["Update skills section"]
                }}
            """
        }
    
    def render_template(self, template_name: str, **kwargs) -> str:
        """Render a prompt template with variables"""
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing variable in template: {e}")
2.2 Context Management
python
# context_manager.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class ConversationContext:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.messages: List[Dict] = []
        self.intent_history: List[Dict] = []
        self.current_intent: Optional[str] = None
        self.entities: Dict = {}
        self.last_activity: datetime = datetime.utcnow()
        self.search_history: List[Dict] = []
        self.preferences: Dict = {}
        
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        
        # Limit history length
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]
        
        self.last_activity = datetime.utcnow()
    
    def add_intent(self, intent: Dict):
        self.intent_history.append({
            **intent,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.current_intent = intent.get("intent")
        self.entities.update(intent.get("entities", {}))
        
        # Limit intent history
        if len(self.intent_history) > 20:
            self.intent_history = self.intent_history[-20:]
    
    def add_search(self, query: str, results: List[Dict]):
        self.search_history.append({
            "query": query,
            "results_count": len(results),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Limit search history
        if len(self.search_history) > 50:
            self.search_history = self.search_history[-50:]
    
    def get_context_string(self) -> str:
        """Generate context string for AI model"""
        context_parts = []
        
        # User preferences
        if self.preferences:
            context_parts.append(f"User Preferences: {self.preferences}")
        
        # Recent intents
        if self.intent_history:
            recent_intents = self.intent_history[-3:]
            context_parts.append(f"Recent Intents: {recent_intents}")
        
        # Current entities
        if self.entities:
            context_parts.append(f"Current Entities: {self.entities}")
        
        # Search history
        if self.search_history:
            recent_searches = self.search_history[-3:]
            context_parts.append(f"Recent Searches: {recent_searches}")
        
        # Last few messages
        if self.messages:
            recent_messages = self.messages[-5:]
            context_parts.append(f"Recent Messages: {recent_messages}")
        
        return "\n".join(context_parts)
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if context has expired"""
        elapsed = (datetime.utcnow() - self.last_activity).total_seconds() / 60
        return elapsed > timeout_minutes

class ContextManager:
    def __init__(self, cache_service):
        self.cache_service = cache_service
        self.contexts: Dict[str, ConversationContext] = {}
        self.timeout_minutes = 30
    
    async def get_context(self, user_id: str) -> ConversationContext:
        """Get or create conversation context for user"""
        # Check memory cache
        if user_id in self.contexts:
            context = self.contexts[user_id]
            if not context.is_expired(self.timeout_minutes):
                return context
        
        # Check Redis cache
        context_data = await self.cache_service.get(f"context:{user_id}")
        if context_data:
            context = self._deserialize_context(context_data)
            self.contexts[user_id] = context
            return context
        
        # Create new context
        context = ConversationContext(user_id)
        self.contexts[user_id] = context
        await self._save_context(user_id, context)
        return context
    
    async def update_context(self, user_id: str, context: ConversationContext):
        """Update and persist conversation context"""
        self.contexts[user_id] = context
        await self._save_context(user_id, context)
    
    async def _save_context(self, user_id: str, context: ConversationContext):
        """Save context to Redis cache"""
        context_data = self._serialize_context(context)
        await self.cache_service.set(
            f"context:{user_id}",
            context_data,
            ttl=self.timeout_minutes * 60
        )
    
    def _serialize_context(self, context: ConversationContext) -> Dict:
        """Serialize context for storage"""
        return {
            "user_id": context.user_id,
            "messages": context.messages,
            "intent_history": context.intent_history,
            "current_intent": context.current_intent,
            "entities": context.entities,
            "last_activity": context.last_activity.isoformat(),
            "search_history": context.search_history,
            "preferences": context.preferences
        }
    
    def _deserialize_context(self, data: Dict) -> ConversationContext:
        """Deserialize context from storage"""
        context = ConversationContext(data["user_id"])
        context.messages = data.get("messages", [])
        context.intent_history = data.get("intent_history", [])
        context.current_intent = data.get("current_intent")
        context.entities = data.get("entities", {})
        context.last_activity = datetime.fromisoformat(data["last_activity"])
        context.search_history = data.get("search_history", [])
        context.preferences = data.get("preferences", {})
        return context
3. AI Processing Pipeline
3.1 Pipeline Architecture
python
# pipeline.py
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

class PipelineStage(Enum):
    RAW = "raw"
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    VALIDATED = "validated"
    DEDUPLICATED = "deduplicated"
    SCORED = "scored"
    EMBEDDED = "embedded"
    PRODUCTION = "production"

@dataclass
class PipelineContext:
    stage: PipelineStage
    data: Dict
    metadata: Dict
    errors: List[str]
    warnings: List[str]
    confidence: float

class AIPipeline:
    def __init__(
        self,
        model_registry: ModelRegistry,
        prompt_engine: PromptEngine,
        embedding_service: EmbeddingService
    ):
        self.model_registry = model_registry
        self.prompt_engine = prompt_engine
        self.embedding_service = embedding_service
        
    async def process_opportunity(
        self,
        raw_data: Dict,
        domain: str,
        source: str
    ) -> PipelineContext:
        """Process opportunity through complete AI pipeline"""
        
        context = PipelineContext(
            stage=PipelineStage.RAW,
            data=raw_data,
            metadata={"domain": domain, "source": source},
            errors=[],
            warnings=[],
            confidence=1.0
        )
        
        try:
            # Stage 1: Extraction
            context = await self._extract(context)
            
            # Stage 2: Normalization
            context = await self._normalize(context)
            
            # Stage 3: Validation
            context = await self._validate(context)
            
            # Stage 4: Deduplication
            context = await self._deduplicate(context)
            
            # Stage 5: Scoring
            context = await self._score(context)
            
            # Stage 6: Embedding
            context = await self._embed(context)
            
            # Final stage: Production
            context.stage = PipelineStage.PRODUCTION
            context.metadata["processed_at"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            context.errors.append(str(e))
            context.confidence = 0.0
        
        return context
    
    async def _extract(self, context: PipelineContext) -> PipelineContext:
        """Extract structured data from raw data"""
        
        model = self.model_registry.select_model(
            ModelCapability.ENTITY_EXTRACTION,
            language="en"
        )
        
        prompt = self.prompt_engine.render_template(
            "entity_extraction",
            text=context.data.get("text", ""),
            domain=context.metadata["domain"],
            schema=self._get_domain_schema(context.metadata["domain"])
        )
        
        response = await model.generate(prompt)
        
        try:
            extracted = json.loads(response.text)
            context.data = extracted
            context.stage = PipelineStage.EXTRACTED
            context.confidence = min(context.confidence, extracted.get("confidence", 0.8))
        except json.JSONDecodeError:
            context.errors.append("Failed to parse extraction response")
            raise
        
        return context
    
    async def _normalize(self, context: PipelineContext) -> PipelineContext:
        """Normalize extracted data to standard schema"""
        
        model = self.model_registry.select_model(
            ModelCapability.NORMALIZATION,
            language="en"
        )
        
        prompt = self.prompt_engine.render_template(
            "opportunity_normalization",
            raw_data=context.data,
            domain=context.metadata["domain"],
            source=context.metadata["source"],
            schema=self._get_domain_schema(context.metadata["domain"])
        )
        
        response = await model.generate(prompt)
        
        try:
            normalized = json.loads(response.text)
            context.data = normalized.get("normalized", {})
            context.confidence = min(context.confidence, normalized.get("confidence", 0.8))
            context.warnings.extend(normalized.get("warnings", []))
            context.stage = PipelineStage.NORMALIZED
        except json.JSONDecodeError:
            context.errors.append("Failed to parse normalization response")
            raise
        
        return context
    
    def _get_domain_schema(self, domain: str) -> Dict:
        """Get schema for specific domain"""
        schemas = {
            "jobs": {
                "title": "string",
                "company_name": "string",
                "location": {"country": "string", "city": "string"},
                "salary": {"min": "number", "max": "number", "currency": "string"},
                "visa_sponsorship": "boolean",
                "skills": ["string"],
                "experience_level": "string",
                "education_level": "string"
            },
            "real_estate": {
                "title": "string",
                "property_type": "string",
                "transaction_type": "string",
                "location": {"country": "string", "city": "string", "area": "string"},
                "specifications": {
                    "bedrooms": "integer",
                    "bathrooms": "integer",
                    "area_sqft": "number"
                },
                "price": "number",
                "currency": "string"
            }
            # ... other domain schemas
        }
        return schemas.get(domain, {})
3.2 Embedding Generation
python
# embedding_service.py
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.batch_size = 32
        
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.model.encode(
                batch,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            embeddings.extend(batch_embeddings.tolist())
        
        return embeddings
    
    async def generate_opportunity_embedding(self, opportunity: Dict) -> List[float]:
        """Generate embedding for an opportunity"""
        # Combine relevant fields for embedding
        text_parts = []
        
        # Core fields
        for field in ["title", "description"]:
            if field in opportunity:
                text_parts.append(opportunity[field])
        
        # Domain-specific fields
        domain = opportunity.get("domain", "")
        if domain == "jobs":
            fields = ["company_name", "location", "skills", "experience_level"]
            for field in fields:
                if field in opportunity:
                    text_parts.append(str(opportunity[field]))
        elif domain == "real_estate":
            fields = ["property_type", "location", "specifications", "features"]
            for field in fields:
                if field in opportunity:
                    text_parts.append(str(opportunity[field]))
        # ... other domains
        
        # Combine and generate embedding
        full_text = " ".join(text_parts)
        return await self.generate_embedding(full_text)
    
    async def update_opportunity_embeddings(self, opportunities: List[Dict]):
        """Generate and update embeddings for multiple opportunities"""
        texts = []
        for opp in opportunities:
            text_parts = []
            for field in ["title", "description"]:
                if field in opp:
                    text_parts.append(opp[field])
            
            # Add domain-specific fields
            domain = opp.get("domain", "")
            if domain == "jobs":
                fields = ["company_name", "location", "skills", "experience_level"]
                for field in fields:
                    if field in opp:
                        text_parts.append(str(opp[field]))
            
            texts.append(" ".join(text_parts))
        
        # Generate embeddings in batches
        embeddings = await self.generate_batch_embeddings(texts)
        
        # Update opportunities with embeddings
        for i, opp in enumerate(opportunities):
            opp["embedding"] = embeddings[i]
        
        return opportunities
4. Model Routing & Cost Optimization
4.1 Intelligent Router
python
# router.py
from typing import Dict, Optional, List
from dataclasses import dataclass
import asyncio

@dataclass
class ModelRequest:
    task_type: str
    text: str
    language: str
    max_tokens: int
    priority: str  # high, medium, low
    max_cost: Optional[float] = None
    required_accuracy: float = 0.85
    fallback_allowed: bool = True

@dataclass
class ModelResponse:
    text: str
    model_used: str
    cost: float
    latency_ms: float
    confidence: float
    tokens_used: int

class IntelligentRouter:
    def __init__(
        self,
        model_registry: ModelRegistry,
        cost_optimizer: CostOptimizer
    ):
        self.model_registry = model_registry
        self.cost_optimizer = cost_optimizer
        self.performance_history = {}
        
    async def route_request(self, request: ModelRequest) -> ModelResponse:
        """Route request to optimal model"""
        
        # Determine capability from task type
        capability = self._get_capability(request.task_type)
        
        # Get model candidates
        candidates = []
        
        # Add primary models
        for model in self.model_registry.models.values():
            if capability in model.capabilities:
                candidates.append(model)
        
        # Apply cost optimization
        candidates = self.cost_optimizer.optimize_candidates(
            candidates,
            max_cost=request.max_cost
        )
        
        # Apply accuracy requirement
        candidates = [
            c for c in candidates
            if self._get_accuracy(c.model_name) >= request.required_accuracy
        ]
        
        # Try models in order
        for model in candidates:
            try:
                response = await self._try_model(model, request)
                if response and response.confidence >= request.required_accuracy:
                    return response
            except Exception as e:
                # Log failure
                print(f"Model {model.model_name} failed: {e}")
                continue
        
        # Fallback if allowed
        if request.fallback_allowed:
            fallback_model = self.model_registry.get_fallback_model(capability)
            return await self._try_model(fallback_model, request)
        
        raise ValueError("No suitable model available")
    
    async def _try_model(self, model: AIModel, request: ModelRequest) -> ModelResponse:
        """Try a specific model"""
        
        start_time = datetime.utcnow()
        
        # Generate prompt based on task
        prompt = self._build_prompt(request.task_type, request.text)
        
        # Execute model
        result = await model.generate(
            prompt,
            max_tokens=request.max_tokens,
            language=request.language
        )
        
        latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update performance history
        self._update_performance(
            model.model_name,
            latency=latency,
            confidence=result.confidence,
            success=True
        )
        
        return ModelResponse(
            text=result.text,
            model_used=model.model_name,
            cost=result.cost,
            latency_ms=latency,
            confidence=result.confidence,
            tokens_used=result.tokens_used
        )
    
    def _get_capability(self, task_type: str) -> ModelCapability:
        """Map task type to model capability"""
        task_mapping = {
            "intent_detection": ModelCapability.INTENT_DETECTION,
            "entity_extraction": ModelCapability.ENTITY_EXTRACTION,
            "response_generation": ModelCapability.RESPONSE_GENERATION,
            "summarization": ModelCapability.SUMMARIZATION,
            "classification": ModelCapability.CLASSIFICATION,
            "normalization": ModelCapability.NORMALIZATION,
            "embedding": ModelCapability.EMBEDDING
        }
        return task_mapping.get(task_type, ModelCapability.RESPONSE_GENERATION)
4.2 Cost Optimization
python
# cost_optimizer.py
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class CostOptimizationConfig:
    budget_per_day: float = 10.0
    budget_per_user: float = 0.10
    max_cost_per_request: float = 0.01
    cost_warning_threshold: float = 0.80  # 80% of budget
    cost_critical_threshold: float = 0.95  # 95% of budget

class CostOptimizer:
    def __init__(self, config: CostOptimizationConfig = None):
        self.config = config or CostOptimizationConfig()
        self.daily_usage = {}
        self.user_usage = {}
        self.model_usage = {}
    
    def optimize_candidates(
        self,
        candidates: List[AIModel],
        max_cost: Optional[float] = None,
        max_latency: Optional[float] = None,
        min_accuracy: float = 0.85
    ) -> List[AIModel]:
        """Optimize model selection based on cost and requirements"""
        
        # Filter by max cost
        if max_cost:
            candidates = [c for c in candidates if c.cost_per_token <= max_cost]
        
        # Filter by latency
        if max_latency:
            candidates = [c for c in candidates if c.latency_ms <= max_latency]
        
        # Check daily budget
        daily_cost = self.get_daily_cost()
        if daily_cost >= self.config.budget_per_day * self.config.cost_critical_threshold:
            # Use cheapest models only
            candidates = sorted(candidates, key=lambda x: x.cost_per_token)
            candidates = candidates[:2]  # Keep only cheapest options
        
        elif daily_cost >= self.config.budget_per_day * self.config.cost_warning_threshold:
            # Balance cost and quality
            candidates = sorted(candidates, key=lambda x: (x.cost_per_token, -x.reliability))
            candidates = candidates[:3]  # Keep cheap+reliable options
        
        return candidates
    
    def get_daily_cost(self) -> float:
        """Get total cost for today"""
        today = datetime.utcnow().date().isoformat()
        return self.daily_usage.get(today, 0.0)
    
    def get_user_cost(self, user_id: str) -> float:
        """Get total cost for a user today"""
        today = datetime.utcnow().date().isoformat()
        return self.user_usage.get(f"{user_id}:{today}", 0.0)
    
    def add_cost(self, user_id: str, model: str, cost: float) -> bool:
        """Add cost and check budget"""
        # Update daily total
        today = datetime.utcnow().date().isoformat()
        self.daily_usage[today] = self.daily_usage.get(today, 0.0) + cost
        
        # Update user total
        user_key = f"{user_id}:{today}"
        self.user_usage[user_key] = self.user_usage.get(user_key, 0.0) + cost
        
        # Update model usage
        model_key = f"{model}:{today}"
        self.model_usage[model_key] = self.model_usage.get(model_key, 0.0) + cost
        
        # Check budget limits
        if self.daily_usage[today] > self.config.budget_per_day:
            return False
        
        if self.user_usage[user_key] > self.config.budget_per_user:
            return False
        
        return True
5. Offline Fallback
5.1 Offline Mode Implementation
python
# offline_fallback.py
from typing import Optional, Dict
import json

class OfflineFallback:
    def __init__(self):
        self.fallback_responses = self._load_fallback_responses()
        self.offline_mode = False
    
    def _load_fallback_responses(self) -> Dict:
        """Load fallback responses for offline mode"""
        return {
            "intent_detection": {
                "intent": "search",
                "domains": ["all"],
                "entities": {},
                "confidence": 0.5,
                "offline": True
            },
            "entity_extraction": {
                "entities": {},
                "confidence": 0.5,
                "offline": True
            },
            "response_generation": {
                "text": "I'm currently offline. Please try again later.",
                "confidence": 0.5,
                "offline": True
            }
        }
    
    async def handle_offline(self, task: str, text: str) -> Dict:
        """Handle requests when offline"""
        if task in self.fallback_responses:
            return self.fallback_responses[task]
        
        return {
            "text": "Service temporarily unavailable. Please try again later.",
            "offline": True,
            "confidence": 0.0
        }
    
    def is_offline(self) -> bool:
        """Check if in offline mode"""
        return self.offline_mode
    
    def set_offline(self, offline: bool):
        """Set offline mode"""
        self.offline_mode = offline

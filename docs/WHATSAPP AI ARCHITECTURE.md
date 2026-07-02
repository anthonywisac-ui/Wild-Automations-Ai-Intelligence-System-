
1. WhatsApp Integration Overview
1.1 Architecture Components
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WHATSAPP AI ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    WHATSAPP BUSINESS API                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   Meta      │  │   Twilio    │  │   Whapi     │  │   Webhook │  │  │
│  │  │   Cloud API │  │   Adapter   │  │   Adapter   │  │   Handler │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    MESSAGE PROCESSING PIPELINE                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Preprocess │  │  Intent     │  │  Context    │  │  Response │  │  │
│  │  │  & Validate │──►│  Detection  │──►│  Management │──►│ Generation│  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    RESPONSE HANDLERS                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   Text      │  │ Interactive │  │   Media     │  │  Template │  │  │
│  │  │   Handler   │  │   Cards     │  │   Handler   │  │  Handler  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    SESSION MANAGEMENT                                 │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Session    │  │  Context    │  │  Cache      │  │  Rate     │  │  │
│  │  │  Store      │  │  Manager    │  │  Manager    │  │  Limiter  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
1.2 Message Flow
text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   WhatsApp   │    │   Webhook    │    │   Message    │    │   AI         │
│   User       │───►│   Receiver   │───►│   Processor  │───►│   Pipeline   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                       │
                                                                       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   WhatsApp   │◄───│   Response   │◄───│   Response   │◄───│   Response   │
│   Delivery   │    │   Formatter  │    │   Generator  │    │   Handler    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
2. Message Processing Pipeline
2.1 Webhook Receiver
python
# whatsapp/webhook_receiver.py
from fastapi import APIRouter, Request, BackgroundTasks
from typing import Dict, Optional
import hmac
import hashlib

class WhatsAppWebhookReceiver:
    def __init__(self, app_secret: str, verify_token: str):
        self.app_secret = app_secret
        self.verify_token = verify_token
        self.router = APIRouter()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup webhook routes"""
        
        @self.router.get("/webhook")
        async def verify_webhook(request: Request):
            """Verify webhook with WhatsApp"""
            query_params = request.query_params
            
            mode = query_params.get("hub.mode")
            token = query_params.get("hub.verify_token")
            challenge = query_params.get("hub.challenge")
            
            if mode == "subscribe" and token == self.verify_token:
                return challenge
            
            return {"status": "error", "message": "Invalid verification token"}
        
        @self.router.post("/webhook")
        async def handle_webhook(
            request: Request,
            background_tasks: BackgroundTasks
        ):
            """Handle incoming WhatsApp webhook"""
            
            # Verify signature
            signature = request.headers.get("X-Hub-Signature-256", "")
            if not self._verify_signature(await request.body(), signature):
                return {"status": "error", "message": "Invalid signature"}
            
            data = await request.json()
            
            # Process messages in background
            background_tasks.add_task(self._process_webhook, data)
            
            return {"status": "received"}
    
    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        if not signature:
            return False
        
        expected = hmac.new(
            self.app_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(
            signature.split("=")[1],
            expected
        )
    
    async def _process_webhook(self, data: Dict):
        """Process webhook data"""
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                for message in messages:
                    await self._handle_message(value, message)
    
    async def _handle_message(self, metadata: Dict, message: Dict):
        """Handle individual message"""
        message_type = message.get("type")
        
        # Get user info
        user_id = message.get("from")
        profile = metadata.get("contacts", [{}])[0].get("profile", {})
        user_name = profile.get("name", "User")
        
        # Process based on message type
        if message_type == "text":
            await self._handle_text_message(user_id, user_name, message)
        elif message_type == "interactive":
            await self._handle_interactive_message(user_id, user_name, message)
        elif message_type == "media":
            await self._handle_media_message(user_id, user_name, message)
        elif message_type == "location":
            await self._handle_location_message(user_id, user_name, message)
    
    async def _handle_text_message(self, user_id: str, user_name: str, message: Dict):
        """Handle text message"""
        text = message.get("text", {}).get("body", "")
        
        # Process through message processor
        processor = MessageProcessor()
        response = await processor.process_message(
            user_id=user_id,
            user_name=user_name,
            text=text
        )
        
        # Send response
        sender = WhatsAppSender()
        await sender.send_message(user_id, response)
2.2 Message Processor
python
# whatsapp/message_processor.py
from typing import Dict, Optional, List
from enum import Enum

class MessageState(Enum):
    NEW = "new"
    INTENT_DETECTED = "intent_detected"
    PROCESSING = "processing"
    RESPONSE_READY = "response_ready"
    SENT = "sent"
    FAILED = "failed"

class MessageProcessor:
    def __init__(self):
        self.intent_detector = IntentDetector()
        self.context_manager = ContextManager()
        self.response_generator = ResponseGenerator()
        self.session_manager = SessionManager()
    
    async def process_message(
        self,
        user_id: str,
        user_name: str,
        text: str
    ) -> Dict:
        """Process incoming message and generate response"""
        
        # Get user session
        session = await self.session_manager.get_session(user_id)
        
        # Update session
        session.add_message("user", text)
        
        # Detect intent
        intent_result = await self.intent_detector.detect_intent(
            text=text,
            context=session.get_context()
        )
        
        # Process based on intent
        response = await self._handle_intent(
            user_id=user_id,
            user_name=user_name,
            text=text,
            intent=intent_result,
            session=session
        )
        
        # Update session with response
        session.add_message("assistant", response.get("text", ""))
        await self.session_manager.save_session(session)
        
        return response
    
    async def _handle_intent(
        self,
        user_id: str,
        user_name: str,
        text: str,
        intent: Dict,
        session: Session
    ) -> Dict:
        """Handle different intents"""
        
        intent_type = intent.get("intent", "search")
        
        if intent_type == "search":
            return await self._handle_search(user_id, text, intent)
        elif intent_type == "filter":
            return await self._handle_filter(user_id, text, intent)
        elif intent_type == "save":
            return await self._handle_save(user_id, text, intent)
        elif intent_type == "notify":
            return await self._handle_notify(user_id, text, intent)
        elif intent_type == "compare":
            return await self._handle_compare(user_id, text, intent)
        elif intent_type == "explain":
            return await self._handle_explain(user_id, text, intent)
        elif intent_type == "help":
            return await self._handle_help(user_id, user_name)
        elif intent_type == "settings":
            return await self._handle_settings(user_id, text, intent)
        else:
            return await self._handle_general(user_id, text, intent)
    
    async def _handle_search(self, user_id: str, text: str, intent: Dict) -> Dict:
        """Handle search intent"""
        
        # Get user profile
        user_profile = await self._get_user_profile(user_id)
        
        # Execute search
        search_results = await self._execute_search(
            query=text,
            filters=intent.get("filters", {}),
            user_profile=user_profile
        )
        
        # Generate response
        response = await self.response_generator.generate_search_response(
            user_id=user_id,
            query=text,
            results=search_results,
            intent=intent
        )
        
        return response
    
    async def _handle_filter(self, user_id: str, text: str, intent: Dict) -> Dict:
        """Handle filter intent"""
        
        # Apply filters to existing search
        filter_params = intent.get("filters", {})
        
        # Update session filters
        session = await self.session_manager.get_session(user_id)
        session.update_filters(filter_params)
        
        # Re-run search with filters
        search_results = await self._execute_search(
            query=text,
            filters=session.get_filters(),
            user_profile=await self._get_user_profile(user_id)
        )
        
        response = await self.response_generator.generate_filter_response(
            user_id=user_id,
            filters=filter_params,
            results=search_results
        )
        
        return response
    
    async def _handle_save(self, user_id: str, text: str, intent: Dict) -> Dict:
        """Handle save intent"""
        
        opportunity_id = intent.get("entities", {}).get("opportunity_id")
        
        if opportunity_id:
            # Save opportunity
            await self._save_opportunity(user_id, opportunity_id)
            
            response = {
                "text": f"✅ I've saved this opportunity for you! You can view it in your saved list anytime.",
                "type": "text",
                "metadata": {"action": "save", "status": "success"}
            }
        else:
            response = {
                "text": "I'm not sure which opportunity you want to save. Could you please provide more details?",
                "type": "text"
            }
        
        return response
2.3 Intent Detection
python
# whatsapp/intent_detector.py
from typing import Dict, List, Optional
from enum import Enum

class IntentType(Enum):
    SEARCH = "search"
    FILTER = "filter"
    SAVE = "save"
    NOTIFY = "notify"
    COMPARE = "compare"
    EXPLAIN = "explain"
    HELP = "help"
    SETTINGS = "settings"
    GENERAL = "general"

class IntentDetector:
    def __init__(self):
        self.intent_patterns = self._load_patterns()
        self.entity_extractor = EntityExtractor()
    
    def _load_patterns(self) -> Dict:
        """Load intent patterns"""
        return {
            "search": [
                r"find\s+.*\s+(jobs?|opportunities?|properties?|cars?|vehicles?|universities?|scholarships?)",
                r"search\s+for\s+.*",
                r"show\s+me\s+.*",
                r"looking\s+for\s+.*",
                r"need\s+a\s+.*",
                r"want\s+to\s+find\s+.*",
                r"discover\s+.*",
                r"help\s+me\s+find\s+.*"
            ],
            "filter": [
                r"filter\s+by\s+.*",
                r"limit\s+to\s+.*",
                r"only\s+.*",
                r"exclude\s+.*",
                r"within\s+.*",
                r"under\s+.*",
                r"less\s+than\s+.*",
                r"more\s+than\s+.*"
            ],
            "save": [
                r"save\s+.*",
                r"bookmark\s+.*",
                r"favorite\s+.*",
                r"keep\s+.*",
                r"store\s+.*"
            ],
            "notify": [
                r"notify\s+me\s+.*",
                r"alert\s+me\s+.*",
                r"tell\s+me\s+.*\s+new",
                r"update\s+me\s+.*",
                r"let\s+me\s+know\s+.*"
            ],
            "compare": [
                r"compare\s+.*",
                r"versus\s+.*",
                r"vs\s+.*",
                r"difference\s+between\s+.*"
            ],
            "explain": [
                r"explain\s+.*",
                r"what\s+is\s+.*",
                r"tell\s+me\s+about\s+.*",
                r"how\s+does\s+.*"
            ],
            "help": [
                r"help",
                r"what\s+can\s+you\s+do",
                r"capabilities",
                r"guide",
                r"tutorial"
            ],
            "settings": [
                r"settings",
                r"preferences",
                r"profile",
                r"notification",
                r"alert\s+preferences"
            ]
        }
    
    async def detect_intent(self, text: str, context: Dict) -> Dict:
        """Detect intent from text"""
        
        text_lower = text.lower()
        
        # Check patterns
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    # Extract entities
                    entities = await self.entity_extractor.extract(text)
                    
                    return {
                        "intent": intent_type,
                        "confidence": 0.9,
                        "entities": entities,
                        "original_text": text
                    }
        
        # Use AI for complex intent detection
        ai_result = await self._ai_detect(text, context)
        
        return {
            "intent": ai_result.get("intent", "general"),
            "confidence": ai_result.get("confidence", 0.5),
            "entities": ai_result.get("entities", {}),
            "original_text": text
        }
    
    async def _ai_detect(self, text: str, context: Dict) -> Dict:
        """Use AI for intent detection"""
        
        prompt = self.prompt_engine.render_template(
            "intent_detection",
            query=text,
            context=json.dumps(context)
        )
        
        model = self.model_registry.select_model(
            ModelCapability.INTENT_DETECTION,
            language="en"
        )
        
        response = await model.generate(prompt)
        
        try:
            result = json.loads(response.text)
            return result
        except:
            return {
                "intent": "general",
                "confidence": 0.3,
                "entities": {}
            }
2.4 Response Generation
python
# whatsapp/response_generator.py
from typing import Dict, List, Optional
from datetime import datetime

class ResponseGenerator:
    def __init__(self):
        self.template_engine = TemplateEngine()
        self.ai_processor = AIProcessor()
    
    async def generate_search_response(
        self,
        user_id: str,
        query: str,
        results: List[Dict],
        intent: Dict
    ) -> Dict:
        """Generate search response"""
        
        if not results:
            return {
                "text": self._get_no_results_message(query),
                "type": "text",
                "buttons": [
                    {"label": "Modify Search", "action": "modify_search"},
                    {"label": "Clear Filters", "action": "clear_filters"}
                ]
            }
        
        # Get top results
        top_results = results[:5]
        
        # Format results
        message = self._format_results(top_results, results)
        
        # Generate buttons
        buttons = self._generate_search_buttons(results)
        
        return {
            "text": message,
            "type": "text",
            "buttons": buttons,
            "metadata": {
                "total_count": len(results),
                "query": query
            }
        }
    
    def _format_results(self, top_results: List[Dict], all_results: List[Dict]) -> str:
        """Format search results"""
        
        if not top_results:
            return "I couldn't find any opportunities matching your criteria. Would you like to try different filters?"
        
        message = "🔍 Here's what I found:\n\n"
        
        for i, result in enumerate(top_results, 1):
            message += f"{i}. *{result.get('title', 'Untitled')}*\n"
            
            if result.get('domain') == 'jobs':
                message += f"   Company: {result.get('company', {}).get('name', 'Unknown')}\n"
                message += f"   Location: {result.get('location', {}).get('country', 'Unknown')}\n"
                if result.get('salary'):
                    message += f"   Salary: {result.get('salary', {}).get('min', 'N/A')} - {result.get('salary', {}).get('max', 'N/A')} {result.get('salary', {}).get('currency', 'USD')}\n"
                if result.get('visa_sponsorship'):
                    message += "   ✅ Visa Sponsorship Available\n"
            
            elif result.get('domain') == 'real_estate':
                message += f"   Type: {result.get('property_type', 'Unknown')}\n"
                message += f"   Location: {result.get('location', {}).get('city', 'Unknown')}\n"
                message += f"   Price: {result.get('price', 'N/A')} {result.get('currency', 'USD')}\n"
                if result.get('bedrooms'):
                    message += f"   Bedrooms: {result.get('bedrooms')}\n"
            
            elif result.get('domain') == 'vehicles':
                message += f"   Make/Model: {result.get('make', 'Unknown')} {result.get('model', 'Unknown')}\n"
                message += f"   Year: {result.get('year', 'Unknown')}\n"
                message += f"   Price: {result.get('price', 'N/A')} {result.get('currency', 'USD')}\n"
            
            message += f"   Match Score: {int(result.get('match_score', 0) * 100)}%\n\n"
        
        if len(all_results) > 5:
            message += f"✨ *And {len(all_results) - 5} more results available*\n"
            message += "   Use filters to narrow down your search.\n\n"
        
        message += "Would you like to view more details or save any of these opportunities?"
        
        return message
    
    def _generate_search_buttons(self, results: List[Dict]) -> List[Dict]:
        """Generate interactive buttons for search response"""
        
        buttons = []
        
        # Add domain-specific actions
        if results:
            domain = results[0].get('domain')
            if domain == 'jobs':
                buttons.append({"label": "Filter by Salary", "action": "filter_salary"})
                buttons.append({"label": "Filter by Location", "action": "filter_location"})
            elif domain == 'real_estate':
                buttons.append({"label": "Filter by Price", "action": "filter_price"})
                buttons.append({"label": "Filter by Location", "action": "filter_location"})
        
        buttons.append({"label": "Save This Search", "action": "save_search"})
        buttons.append({"label": "Need Help?", "action": "help"})
        
        return buttons
    
    def _get_no_results_message(self, query: str) -> str:
        """Get message for no results"""
        return (
            f"I couldn't find any opportunities matching '{query}'. 😅\n\n"
            "Here are some suggestions:\n"
            "• Try different keywords\n"
            "• Broaden your search criteria\n"
            "• Check if you have any filters applied\n"
            "• Search in a different domain\n\n"
            "What would you like to try next?"
        )
    
    async def generate_filter_response(
        self,
        user_id: str,
        filters: Dict,
        results: List[Dict]
    ) -> Dict:
        """Generate filter response"""
        
        if not results:
            return {
                "text": f"I applied your filters: {filters}\n\n" + 
                        "But I couldn't find any matches. Try adjusting your filters.",
                "type": "text",
                "buttons": [
                    {"label": "Clear Filters", "action": "clear_filters"},
                    {"label": "Modify Filters", "action": "modify_filters"}
                ]
            }
        
        message = "✅ I've applied your filters and found some great matches!\n\n"
        message += self._format_results(results[:5], results)
        
        return {
            "text": message,
            "type": "text",
            "buttons": [
                {"label": "Save Search", "action": "save_search"},
                {"label": "Clear Filters", "action": "clear_filters"},
                {"label": "More Results", "action": "more_results"}
            ]
        }
3. Session Management
3.1 Session Manager
python
# whatsapp/session_manager.py
from typing import Dict, Optional, List
from datetime import datetime, timedelta

class Session:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.messages: List[Dict] = []
        self.context: Dict = {}
        self.filters: Dict = {}
        self.saved_searches: List[Dict] = []
        self.last_activity: datetime = datetime.utcnow()
        self.state: str = "idle"
        self.intent_history: List[str] = []
        
    def add_message(self, role: str, content: str):
        """Add message to session"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep last 50 messages
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]
        
        self.last_activity = datetime.utcnow()
    
    def update_filters(self, filters: Dict):
        """Update search filters"""
        self.filters.update(filters)
    
    def get_filters(self) -> Dict:
        """Get current filters"""
        return self.filters
    
    def get_context(self) -> Dict:
        """Get session context"""
        return {
            "messages": self.messages[-10:],
            "filters": self.filters,
            "saved_searches": self.saved_searches[-5:],
            "state": self.state,
            "intent_history": self.intent_history[-5:]
        }
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session expired"""
        elapsed = (datetime.utcnow() - self.last_activity).total_seconds() / 60
        return elapsed > timeout_minutes

class SessionManager:
    def __init__(self, cache_service):
        self.cache_service = cache_service
        self.sessions: Dict[str, Session] = {}
        self.timeout_minutes = 30
    
    async def get_session(self, user_id: str) -> Session:
        """Get or create session"""
        
        # Check memory cache
        if user_id in self.sessions:
            session = self.sessions[user_id]
            if not session.is_expired(self.timeout_minutes):
                return session
        
        # Check Redis cache
        session_data = await self.cache_service.get(f"whatsapp_session:{user_id}")
        if session_data:
            session = self._deserialize(session_data)
            self.sessions[user_id] = session
            return session
        
        # Create new session
        session = Session(user_id)
        self.sessions[user_id] = session
        await self._save_session(user_id, session)
        return session
    
    async def save_session(self, session: Session):
        """Save session"""
        self.sessions[session.user_id] = session
        await self._save_session(session.user_id, session)
    
    async def _save_session(self, user_id: str, session: Session):
        """Save session to Redis"""
        session_data = self._serialize(session)
        await self.cache_service.set(
            f"whatsapp_session:{user_id}",
            session_data,
            ttl=self.timeout_minutes * 60
        )
    
    def _serialize(self, session: Session) -> Dict:
        """Serialize session"""
        return {
            "user_id": session.user_id,
            "messages": session.messages,
            "context": session.context,
            "filters": session.filters,
            "saved_searches": session.saved_searches,
            "last_activity": session.last_activity.isoformat(),
            "state": session.state,
            "intent_history": session.intent_history
        }
    
    def _deserialize(self, data: Dict) -> Session:
        """Deserialize session"""
        session = Session(data["user_id"])
        session.messages = data.get("messages", [])
        session.context = data.get("context", {})
        session.filters = data.get("filters", {})
        session.saved_searches = data.get("saved_searches", [])
        session.last_activity = datetime.fromisoformat(data["last_activity"])
        session.state = data.get("state", "idle")
        session.intent_history = data.get("intent_history", [])
        return session
4. Interactive Components
4.1 Quick Replies & Buttons
python
# whatsapp/interactive.py
from typing import Dict, List, Optional

class InteractiveMessageBuilder:
    def __init__(self):
        self.message = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual"
        }
    
    def build_text_response(self, text: str, buttons: List[Dict] = None) -> Dict:
        """Build text response with optional buttons"""
        response = {
            "type": "text",
            "text": {"body": text}
        }
        
        if buttons:
            # Add interactive buttons
            response["type"] = "interactive"
            response["interactive"] = {
                "type": "button",
                "body": {"text": text},
                "action": {
                    "buttons": []
                }
            }
            
            for button in buttons[:3]:  # Max 3 buttons
                response["interactive"]["action"]["buttons"].append({
                    "type": "reply",
                    "reply": {
                        "id": button.get("action", "action"),
                        "title": button.get("label", "Action")
                    }
                })
        
        return response
    
    def build_list_response(self, text: str, sections: List[Dict]) -> Dict:
        """Build interactive list response"""
        return {
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": text},
                "action": {
                    "button": "View Options",
                    "sections": sections
                }
            }
        }
    
    def build_catalog_response(self, text: str, products: List[Dict]) -> Dict:
        """Build product catalog response"""
        return {
            "type": "interactive",
            "interactive": {
                "type": "product_list",
                "body": {"text": text},
                "action": {
                    "catalog_id": "catalog_id",
                    "sections": [
                        {
                            "title": "Opportunities",
                            "products": [
                                {
                                    "product_retailer_id": p.get("id"),
                                    "product_image_url": p.get("image_url"),
                                    "product_title": p.get("title"),
                                    "product_description": p.get("description"),
                                    "product_price": p.get("price")
                                }
                                for p in products[:10]
                            ]
                        }
                    ]
                }
            }
        }
    
    def build_media_response(
        self,
        media_type: str,
        media_url: str,
        caption: str = None
    ) -> Dict:
        """Build media response"""
        response = {
            "type": media_type,
            media_type: {
                "link": media_url
            }
        }
        
        if caption:
            response[media_type]["caption"] = caption
        
        return response
4.2 Template Engine
python
# whatsapp/template_engine.py
from typing import Dict, List, Optional
from jinja2 import Environment, FileSystemLoader

class WhatsAppTemplateEngine:
    def __init__(self, template_dir: str = "templates/whatsapp"):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.templates = {
            "welcome": "welcome.txt",
            "help": "help.txt",
            "search_results": "search_results.txt",
            "opportunity_detail": "opportunity_detail.txt",
            "notification": "notification.txt",
            "filter_applied": "filter_applied.txt",
            "no_results": "no_results.txt",
            "save_confirmation": "save_confirmation.txt",
            "settings": "settings.txt"
        }
    
    def render(self, template_name: str, **kwargs) -> str:
        """Render a template with variables"""
        
        template_file = self.templates.get(template_name)
        if not template_file:
            raise ValueError(f"Template not found: {template_name}")
        
        template = self.env.get_template(template_file)
        return template.render(**kwargs)
    
    def render_opportunity(self, opportunity: Dict) -> str:
        """Render opportunity details"""
        
        domain = opportunity.get("domain", "general")
        
        if domain == "jobs":
            return self._render_job(opportunity)
        elif domain == "real_estate":
            return self._render_real_estate(opportunity)
        elif domain == "vehicles":
            return self._render_vehicle(opportunity)
        else:
            return self._render_general(opportunity)
    
    def _render_job(self, job: Dict) -> str:
        """Render job opportunity"""
        
        return f"""
*{job.get('title', 'Position')}*
Company: {job.get('company', {}).get('name', 'Unknown')}
Location: {job.get('location', {}).get('country', 'Unknown')}
Salary: {job.get('salary', {}).get('min', 'N/A')} - {job.get('salary', {}).get('max', 'N/A')} {job.get('salary', {}).get('currency', 'USD')}

{job.get('description', 'No description available')[:500]}

✅ Visa Sponsorship: {'Yes' if job.get('visa_sponsorship') else 'No'}
💼 Experience: {job.get('experience_level', 'Not specified')}
🎓 Education: {job.get('education_level', 'Not specified')}
🔗 Apply: {job.get('application_url', 'Link not available')}

Match Score: {int(job.get('match_score', 0) * 100)}%
        """
    
    def _render_real_estate(self, property: Dict) -> str:
        """Render real estate opportunity"""
        
        return f"""
*{property.get('title', 'Property')}*
Type: {property.get('property_type', 'Unknown')}
Location: {property.get('location', {}).get('city', 'Unknown')}
Price: {property.get('price', 'N/A')} {property.get('currency', 'USD')}

🏠 Bedrooms: {property.get('bedrooms', 'N/A')}
🚿 Bathrooms: {property.get('bathrooms', 'N/A')}
📐 Area: {property.get('area_sqft', 'N/A')} sqft
🛋️ Furnished: {'Yes' if property.get('furnished') else 'No'}

{property.get('description', 'No description available')[:300]}

Match Score: {int(property.get('match_score', 0) * 100)}%
        """
    
    def _render_vehicle(self, vehicle: Dict) -> str:
        """Render vehicle opportunity"""
        
        return f"""
*{vehicle.get('make', 'Unknown')} {vehicle.get('model', 'Unknown')}*
Year: {vehicle.get('year', 'Unknown')}
Price: {vehicle.get('price', 'N/A')} {vehicle.get('currency', 'USD')}

📍 Mileage: {vehicle.get('mileage', 'N/A')} km
⚙️ Transmission: {vehicle.get('transmission', 'Unknown')}
⛽ Fuel: {vehicle.get('fuel_type', 'Unknown')}
🎨 Color: {vehicle.get('color', 'Unknown')}
🔄 Condition: {vehicle.get('condition', 'Unknown')}

{vehicle.get('description', 'No description available')[:300]}

Match Score: {int(vehicle.get('match_score', 0) * 100)}%
        """
5. Rate Limiting
python
# whatsapp/rate_limiter.py
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio

class WhatsAppRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.limits = {
            "user": {"max": 100, "period": 60},  # 100 messages per minute per user
            "global": {"max": 1000, "period": 60},  # 1000 messages per minute globally
            "api": {"max": 10, "period": 1}  # 10 API calls per second
        }
    
    async def check_rate_limit(self, user_id: str, type: str = "user") -> bool:
        """Check if rate limit exceeded"""
        
        if type not in self.limits:
            return True
        
        limit = self.limits[type]
        key = f"whatsapp_rate_limit:{type}:{user_id if type == 'user' else 'global'}"
        
        count = await self.redis.get(key) or 0
        
        if count >= limit["max"]:
            return False
        
        # Increment counter
        pipeline = self.redis.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, limit["period"])
        await pipeline.execute()
        
        return True
    
    async def wait_for_rate_limit(self, user_id: str, type: str = "user") -> bool:
        """Wait until rate limit available"""
        
        while True:
            if await self.check_rate_limit(user_id, type):
                return True
            
            # Wait and retry
            await asyncio.sleep(1)
    
    def get_rate_limit_info(self, user_id: str, type: str = "user") -> Dict:
        """Get rate limit information"""
        
        limit = self.limits.get(type)
        if not limit:
            return {}
        
        key = f"whatsapp_rate_limit:{type}:{user_id if type == 'user' else 'global'}"
        
        remaining = limit["max"] - (self.redis.get(key) or 0)
        
        return {
            "max": limit["max"],
            "remaining": max(0, remaining),
            "period": limit["period"],
            "reset_in": self.redis.ttl(key) or 0
        }

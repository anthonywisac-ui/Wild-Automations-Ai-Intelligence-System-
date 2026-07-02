1. Prompt Engineering Overview
1.1 Objectives
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROMPT ENGINEERING OBJECTIVES                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. ACCURACY                                                                │
│     - Ensure factual correctness                                           │
│     - Minimize hallucinations                                              │
│     - Validate outputs against schemas                                     │
│                                                                             │
│  2. CONSISTENCY                                                             │
│     - Consistent output format                                             │
│     - Reliable structured data extraction                                  │
│     - Reproducible results                                                 │
│                                                                             │
│  3. EFFICIENCY                                                              │
│     - Minimize token usage                                                 │
│     - Optimize prompt length                                               │
│     - Balance detail with cost                                             │
│                                                                             │
│  4. PERSONALIZATION                                                         │
│     - User context integration                                             │
│     - Domain-specific knowledge                                            │
│     - Preference adaptation                                                │
│                                                                             │
│  5. SCALABILITY                                                             │
│     - Template-based design                                                │
│     - Version controlled                                                   │
│     - A/B testable                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

1.2 Prompt Types

Prompt Types:
  
  System Prompts:
    Purpose: Define AI behavior and constraints
    Scope: Global/context-level
    Examples:
      - "You are an AI assistant for opportunity intelligence"
      - "Always maintain a professional and helpful tone"
      - "Only use provided information; do not hallucinate"
    
  Task Prompts:
    Purpose: Specific task instructions
    Scope: Per request
    Examples:
      - "Extract job information from the following text"
      - "Generate a search response based on these results"
      - "Normalize this opportunity data"
    
  Context Prompts:
    Purpose: Provide relevant background
    Scope: Per conversation/session
    Examples:
      - "User preferences: [preferences]"
      - "Previous interaction: [history]"
      - "Current session: [session_data]"
    
  Format Prompts:
    Purpose: Define output structure
    Scope: Per request
    Examples:
      - "Return JSON with fields: title, company, location"
      - "Format response as WhatsApp message"
      - "Use markdown for formatting"
    
  Few-Shot Prompts:
    Purpose: Provide examples
    Scope: Per request
    Examples:
      - "Example 1: [example_data]"
      - "Example 2: [example_data]"
      - "Follow these examples"

2. Prompt Templates
2.1 Intent Detection Prompt
You are an intent detection system for WildAutomations AI Opportunity Intelligence Platform.

SYSTEM CONTEXT:
- Platform helps users find opportunities (jobs, real estate, vehicles, education, etc.)
- Users ask questions in natural language
- Support multiple domains and complex queries

TASK:
Analyze the user query and identify:
1. Primary intent
2. Secondary intents (if any)
3. Relevant domains
4. Key entities
5. Confidence score

INTENTS:
- SEARCH: Looking for opportunities
- FILTER: Refining search results
- SAVE: Bookmarking opportunities
- COMPARE: Comparing options
- EXPLAIN: Asking about details
- NOTIFY: Setting up alerts
- HELP: Requesting assistance
- SETTINGS: Managing preferences

DOMAINS:
- JOBS: Employment opportunities
- REAL_ESTATE: Properties for sale/rent
- VEHICLES: Cars and other vehicles
- EDUCATION: Universities, programs
- IMMIGRATION: Visa, residency
- SCHOLARSHIPS: Educational funding
- AUCTIONS: Bidding opportunities
- BUSINESS: Tenders, grants

OUTPUT FORMAT:
{
    "intent": "SEARCH",
    "secondary_intents": ["FILTER"],
    "domains": ["JOBS", "IMMIGRATION"],
    "entities": {
        "job_title": "Data Scientist",
        "location": "Germany",
        "visa_sponsorship": true
    },
    "confidence": 0.95,
    "suggestions": [
        "Consider adding filters for salary range",
        "Try searching for 'Machine Learning Engineer' as well"
    ]
}

USER QUERY:
{query}

USER CONTEXT:
{context}

HISTORICAL INTERACTIONS:
{history}

RULES:
1. Always include confidence score
2. Extract all relevant entities
3. Consider context for ambiguous queries
4. If uncertain, note in suggestions

BEGIN ANALYSIS:
2.2 Entity Extraction Prompt
You are an entity extraction system for WildAutomations AI Opportunity Intelligence Platform.

SYSTEM CONTEXT:
- Extract structured information from unstructured text
- Support multiple domains with domain-specific schemas
- Validate extracted data for consistency

DOMAIN: {domain}

SCHEMA:
{schema}

TASK:
Extract entities from the following text and map to the schema.

TEXT:
{text}

SOURCE:
{source}

RULES:
1. Extract ALL entities that match the schema
2. Use exact text spans when possible
3. Handle abbreviations and variations
4. Set confidence scores for each entity
5. Flag uncertain extractions

OUTPUT FORMAT:
{
    "entities": {
        "field1": {
            "value": "extracted_value",
            "span": [10, 25],
            "confidence": 0.95
        }
    },
    "metadata": {
        "total_entities": 5,
        "extraction_time": 0.12,
        "model": "gemini-pro"
    },
    "warnings": [
        "Missing field: company_name"
    ]
}

EXAMPLES:
{examples}

BEGIN EXTRACTION:
2.3 Response Generation Prompt
You are an AI assistant for WildAutomations AI Opportunity Intelligence Platform.

ROLE:
- Helpful, professional, and conversational
- Provide accurate, relevant information
- Guide users to better opportunities

USER QUERY:
{query}

INTENT DETECTED:
{intent}

USER CONTEXT:
{context}

USER PROFILE:
{profile}

SEARCH RESULTS:
{results}

TASK:
Generate a response that:
1. Directly answers the user's query
2. Highlights the most relevant opportunities
3. Provides actionable insights
4. Suggests next steps
5. Maintains context awareness

RESPONSE GUIDELINES:
- For SEARCH: Summarize results, highlight top 3, suggest refinements
- For FILTER: Apply filters, show updated results, suggest more filters
- For SAVE: Confirm save, suggest similar opportunities
- For COMPARE: Compare features, provide recommendations
- For EXPLAIN: Explain in simple terms, provide examples
- For NOTIFY: Confirm alert setup, suggest adjustments
- For HELP: List capabilities, provide examples

FORMAT:
- WhatsApp: Concise, plain text, use emojis
- Web: Rich text, include details, structured

DELIVERY CHANNEL:
{channel}

RULES:
1. Be concise but informative
2. Use bullet points for readability
3. Include match scores
4. Suggest follow-up actions
5. Maintain professional tone

BEGIN RESPONSE:
2.4 Opportunity Normalization Prompt

You are an opportunity normalization system for WildAutomations AI Opportunity Intelligence Platform.

SYSTEM CONTEXT:
- Normalize raw data from various sources
- Convert to standard domain schema
- Ensure data quality and consistency

DOMAIN: {domain}

SOURCE: {source}

RAW DATA:
{raw_data}

SCHEMA:
{schema}

TASK:
Normalize the raw data according to the schema.

NORMALIZATION RULES:
1. Map source fields to schema fields
2. Convert dates to ISO 8601 UTC
3. Normalize currencies to ISO 4217
4. Clean and validate text fields
5. Handle missing fields gracefully
6. Set confidence scores
7. Flag quality issues

OUTPUT FORMAT:
{
    "normalized": {
        "field1": "normalized_value",
        "field2": 123
    },
    "quality_score": 0.92,
    "warnings": ["Missing field: salary_min"],
    "source_mappings": {
        "source_field1": "schema_field1",
        "source_field2": "schema_field2"
    },
    "confidence": 0.88,
    "metadata": {
        "normalization_time": 0.15,
        "model": "claude-3-sonnet"
    }
}

EXAMPLES:
{examples}

BEGIN NORMALIZATION:

3. Prompt Optimization
3.1 Token Optimization
# prompt_optimizer.py
from typing import Dict, List, Optional
import tiktoken

class PromptOptimizer:
    def __init__(self, model: str = "gpt-4"):
        self.encoder = tiktoken.encoding_for_model(model)
        self.max_tokens = {
            "gpt-4": 8192,
            "gpt-3.5-turbo": 4096,
            "gemini-pro": 32000,
            "claude-3-sonnet": 200000
        }
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoder.encode(text))
    
    def optimize_prompt(self, prompt: str, target_tokens: int = None) -> str:
        """Optimize prompt to fit token limit"""
        current_tokens = self.count_tokens(prompt)
        
        if target_tokens is None:
            target_tokens = self.max_tokens.get("gpt-4", 4096)
        
        if current_tokens <= target_tokens:
            return prompt
        
        # Strategies to reduce tokens
        # 1. Remove comments
        prompt = self._remove_comments(prompt)
        
        # 2. Shorten instructions
        prompt = self._shorten_instructions(prompt)
        
        # 3. Compress examples
        prompt = self._compress_examples(prompt)
        
        # 4. Remove redundant whitespace
        prompt = self._remove_whitespace(prompt)
        
        # 5. Abbreviate common terms
        prompt = self._abbreviate_terms(prompt)
        
        # Check if token count is still high
        if self.count_tokens(prompt) > target_tokens:
            # Remove less important sections
            prompt = self._remove_sections(prompt, target_tokens)
        
        return prompt
    
    def _remove_comments(self, prompt: str) -> str:
        """Remove comments from prompt"""
        lines = prompt.split('\n')
        filtered = [line for line in lines if not line.strip().startswith('//')]
        return '\n'.join(filtered)
    
    def _shorten_instructions(self, prompt: str) -> str:
        """Shorten instruction sections"""
        # Look for long instruction blocks
        # Replace with concise version
        return prompt
    
    def _compress_examples(self, prompt: str) -> str:
        """Compress examples"""
        # Keep only the most relevant examples
        # Reduce example verbosity
        return prompt
    
    def _remove_whitespace(self, prompt: str) -> str:
        """Remove unnecessary whitespace"""
        lines = prompt.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        return '\n'.join(lines)
    
    def _abbreviate_terms(self, prompt: str) -> str:
        """Abbreviate common terms"""
        abbreviations = {
            "opportunity": "opp",
            "sponsorship": "sponsor",
            "requirements": "reqs",
            "preferences": "prefs",
            "experience": "exp",
            "education": "edu",
            "immigration": "imm"
        }
        
        for term, abbr in abbreviations.items():
            prompt = prompt.replace(term, abbr)
        
        return prompt
    
    def _remove_sections(self, prompt: str, target_tokens: int) -> str:
        """Remove less important sections"""
        # Priority order of sections to keep
        sections = prompt.split('\n\n')
        
        # Keep first section (usually most important)
        optimized = [sections[0]]
        
        # Add sections until token limit reached
        for section in sections[1:]:
            if self.count_tokens('\n\n'.join(optimized + [section])) <= target_tokens:
                optimized.append(section)
            else:
                break
        
        return '\n\n'.join(optimized)
3.2 A/B Testing Framework

# prompt_testing.py
from typing import Dict, List, Optional
from dataclasses import dataclass
import random

@dataclass
class PromptTest:
    name: str
    prompts: List[str]
    variants: List[Dict]
    metrics: List[str]

class PromptTestingFramework:
    def __init__(self, ai_service):
        self.ai_service = ai_service
        self.results = {}
    
    def run_ab_test(self, test: PromptTest, test_data: List[Dict]) -> Dict:
        """Run A/B test on prompt variants"""
        
        results = {variant: [] for variant in test.variants}
        
        for data in test_data:
            # Randomly assign to variant
            variant = random.choice(test.variants)
            
            # Get prompt for variant
            prompt = self._get_prompt_for_variant(test, variant, data)
            
            # Execute
            response = self.ai_service.generate(prompt)
            
            # Evaluate
            scores = self._evaluate_response(response, test.metrics)
            results[variant].append(scores)
        
        # Calculate statistics
        stats = self._calculate_stats(results)
        
        return {
            'test_name': test.name,
            'variants': test.variants,
            'statistics': stats,
            'winner': self._determine_winner(stats)
        }
    
    def _get_prompt_for_variant(self, test: PromptTest, variant: Dict, data: Dict) -> str:
        """Get prompt for specific variant"""
        # Replace placeholders with data
        prompt = test.prompts[0]  # Base prompt
        
        for key, value in variant.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        
        for key, value in data.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        
        return prompt
    
    def _evaluate_response(self, response: Dict, metrics: List[str]) -> Dict:
        """Evaluate response quality"""
        scores = {}
        
        for metric in metrics:
            if metric == 'accuracy':
                scores['accuracy'] = self._calculate_accuracy(response)
            elif metric == 'relevance':
                scores['relevance'] = self._calculate_relevance(response)
            elif metric == 'completeness':
                scores['completeness'] = self._calculate_completeness(response)
            elif metric == 'format_compliance':
                scores['format_compliance'] = self._validate_format(response)
            elif metric == 'tone':
                scores['tone'] = self._check_tone(response)
            elif metric == 'length':
                scores['length'] = self._check_length(response)
        
        return scores
4. Prompt Versioning
4.1 Version Control
# prompt_versioning.py
from typing import Dict, List, Optional
from datetime import datetime
import json
import hashlib

class PromptVersion:
    def __init__(self, name: str, content: str, version: str):
        self.name = name
        self.content = content
        self.version = version
        self.hash = hashlib.sha256(content.encode()).hexdigest()
        self.created_at = datetime.utcnow()
        self.metadata = {
            'tokens': self._count_tokens(content),
            'type': self._detect_type(content),
            'variables': self._extract_variables(content)
        }
    
    def _count_tokens(self, content: str) -> int:
        """Count tokens in prompt"""
        # Use tiktoken
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4")
        return len(enc.encode(content))
    
    def _detect_type(self, content: str) -> str:
        """Detect prompt type"""
        if 'intent' in content.lower():
            return 'intent_detection'
        elif 'extract' in content.lower():
            return 'entity_extraction'
        elif 'normalize' in content.lower():
            return 'normalization'
        elif 'response' in content.lower():
            return 'response_generation'
        else:
            return 'general'
    
    def _extract_variables(self, content: str) -> List[str]:
        """Extract template variables"""
        import re
        pattern = r'\{([^{}]+)\}'
        return re.findall(pattern, content)

class PromptVersioning:
    def __init__(self):
        self.versions: Dict[str, List[PromptVersion]] = {}
    
    def add_version(self, name: str, content: str, version: str):
        """Add new version of prompt"""
        if name not in self.versions:
            self.versions[name] = []
        
        # Check if version exists
        for existing in self.versions[name]:
            if existing.version == version:
                raise ValueError(f"Version {version} already exists for {name}")
        
        prompt_version = PromptVersion(name, content, version)
        self.versions[name].append(prompt_version)
    
    def get_version(self, name: str, version: str = None) -> Optional[PromptVersion]:
        """Get prompt version"""
        if name not in self.versions:
            return None
        
        if version is None:
            # Get latest version
            return self.versions[name][-1]
        
        for prompt_version in self.versions[name]:
            if prompt_version.version == version:
                return prompt_version
        
        return None
    
    def compare_versions(self, name: str, version1: str, version2: str) -> Dict:
        """Compare two prompt versions"""
        prompt1 = self.get_version(name, version1)
        prompt2 = self.get_version(name, version2)
        
        if not prompt1 or not prompt2:
            raise ValueError("Version not found")
        
        # Calculate differences
        diff = {
            'content_changed': prompt1.content != prompt2.content,
            'token_diff': prompt2.metadata['tokens'] - prompt1.metadata['tokens'],
            'variable_diff': set(prompt2.metadata['variables']) - set(prompt1.metadata['variables']),
            'similarity': self._calculate_similarity(prompt1.content, prompt2.content)
        }
        
        return diff
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        # Use Jaccard similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0


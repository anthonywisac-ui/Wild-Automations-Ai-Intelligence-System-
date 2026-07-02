import asyncio
import json
import logging
import random
from typing import Any, Dict, List, Optional, Callable, Awaitable
from string import Template
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class AIConfig:
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-haiku-4-5-20251001"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    default_provider: str = "passthrough"
    max_retries: int = 3
    timeout: int = 60
    temperature: float = 0.7


class PromptTemplate:
    def __init__(self, template: str, variables: Dict[str, str]):
        """
        Args:
            template: The prompt template with placeholders like $var.
            variables: Mapping of variable names to their descriptions/sources.
        """
        self.template = Template(template)
        self.variables = variables

    def render(self, context: Dict[str, Any]) -> str:
        """Inject dynamic values into the template."""
        return self.template.safe_substitute(context)


class AIProcessor:
    def __init__(
        self,
        config: AIConfig,
        templates: Dict[str, PromptTemplate],
        cleaning_funcs: Optional[Dict[str, Callable[[Dict], Dict]]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        concurrency: int = 5,
    ):
        self.config = config
        self.templates = templates
        self.cleaning_funcs = cleaning_funcs or {}
        self.output_schema = output_schema or {"subject": "", "body": ""}
        self.concurrency = concurrency
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._running = False
        self.results: asyncio.Queue = asyncio.Queue()

    async def add_job(self, bot_name: str, raw_data: Dict[str, Any]) -> None:
        """Add a new job to the processing queue."""
        await self._queue.put({"bot": bot_name, "raw": raw_data})

    async def start(self) -> None:
        """Start the processing workers."""
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker())
            for _ in range(self.concurrency)
        ]

    async def stop(self) -> None:
        """Stop all workers gracefully."""
        self._running = False
        await self._queue.join()
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    async def _worker(self) -> None:
        """Main worker loop processing jobs from the queue."""
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                result = await self._process_job(job)
                await self.results.put(result)
            except Exception as e:
                logger.error(f"Job failed: {e}", exc_info=True)
            finally:
                self._queue.task_done()

    async def _process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single job: clean, render, call LLM, parse output."""
        bot_name = job["bot"]
        raw_data = job["raw"]

        # Clean raw data
        clean_func = self.cleaning_funcs.get(bot_name, self._default_clean)
        cleaned = await self._run_async(clean_func, raw_data)

        # Render prompt
        template = self.templates.get(bot_name)
        if template is None:
            raise ValueError(f"No template found for bot: {bot_name}")

        # Build context from cleaned data
        context = {var: cleaned.get(var, "") for var in template.variables}
        prompt = template.render(context)

        # Call LLM
        response_text = await self._call_llm_with_retry(prompt)

        # Parse structured output
        structured = self._parse_output(response_text)
        return {
            "bot": bot_name,
            "raw": raw_data,
            "cleaned": cleaned,
            "prompt": prompt,
            "response": response_text,
            "structured": structured,
        }

    @staticmethod
    async def _run_async(func: Callable, *args, **kwargs) -> Any:
        """Run a sync or async function consistently."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run sync in thread to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)

    @staticmethod
    def _default_clean(data: Dict[str, Any]) -> Dict[str, Any]:
        """Default cleaning: extract string values."""
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = v.strip()
            elif v is not None:
                result[k] = str(v)
            else:
                result[k] = ""
        return result

    async def _call_llm_with_retry(self, prompt: str) -> str:
        """Call LLM with retries based on config."""
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                return await self._call_llm(prompt)
            except Exception as e:
                last_exception = e
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.warning(f"LLM call failed (attempt {attempt+1}): {e}. Retry in {wait:.2f}s")
                await asyncio.sleep(wait)
        raise RuntimeError(f"All LLM retries failed: {last_exception}")

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM provider based on configuration."""
        provider = self.config.default_provider.lower()
        if provider == "passthrough":
            return await self._call_passthrough(prompt)
        elif provider == "openai":
            return await self._call_openai(prompt)
        elif provider == "anthropic":
            return await self._call_anthropic(prompt)
        elif provider == "ollama":
            return await self._call_ollama(prompt)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _call_passthrough(self, prompt: str) -> str:
        """Format directly from prompt into a clean WhatsApp alert without LLM."""
        fields = {}
        for line in prompt.split("\n"):
            line = line.strip()
            for key in ("Bot", "Region", "Listing"):
                if line.startswith(f"{key}:"):
                    fields[key] = line[len(key)+1:].strip()
        listing = fields.get("Listing", "").strip()
        bot = fields.get("Bot", "Alert").strip()
        region = fields.get("Region", "").strip()
        subject = f"🔔 {bot}"
        body = f"*{bot}*\n📍 {region}\n\n{listing}" if listing else f"*{bot}*\n📍 {region}"
        return json.dumps({"subject": subject, "body": body})

    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI ChatCompletion API."""
        try:
            import openai as _openai
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        client = _openai.AsyncOpenAI(api_key=self.config.openai_api_key)
        try:
            resp = await client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are an assistant that returns structured JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                timeout=self.config.timeout,
            )
            return resp.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI error: {e}") from e

    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        async with httpx.AsyncClient(timeout=self.config.timeout, verify=False) as client:
            try:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.config.anthropic_api_key or "",
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.config.anthropic_model,
                        "max_tokens": 512,
                        "messages": [{"role": "user", "content": prompt}],
                        "system": "You are an assistant that returns structured JSON.",
                    },
                )
                resp.raise_for_status()
                return resp.json()["content"][0]["text"]
            except Exception as e:
                raise RuntimeError(f"Anthropic error: {e}") from e

    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama generate endpoint."""
        async with httpx.AsyncClient(timeout=self.config.timeout, verify=False) as client:
            payload = {
                "model": self.config.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self.config.temperature},
            }
            try:
                resp = await client.post(f"{self.config.ollama_base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
            except Exception as e:
                raise RuntimeError(f"Ollama error: {e}") from e

    def _parse_output(self, text: str) -> Dict[str, Any]:
        """Parse LLM response into structured dict according to output_schema."""
        # Try to extract JSON from markdown code blocks
        text = text.strip()
        if text.startswith("```") and "```" in text[3:]:
            # Extract content between first and last triple backticks
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1]  # Take content inside the first block
                # Remove language spec if present
                if "\n" in text:
                    text = text.split("\n", 1)[1]

        # Try to parse JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                # Validate against schema (ensure required keys exist)
                for key in self.output_schema.keys():
                    if key not in data:
                        data[key] = self.output_schema[key]
                return data
        except json.JSONDecodeError:
            # Fallback: treat as plain text and fill body
            return {"subject": "", "body": text}

        # If not dict, wrap in body
        return {"subject": "", "body": str(text)}
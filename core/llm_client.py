"""
Unified multi-provider LLM client.

Every supported provider exposes an OpenAI-compatible /chat/completions
endpoint, so one httpx code path serves them all — just a different base_url,
API key, and default model. The active provider is auto-detected from whichever
API key is present in the environment, in priority order.

Supported (env key names accepted, first match wins):
    GROQ      GROQ_API_KEY / GROQ_API / GROQ
    GEMINI    GEMINI_API_KEY / GEMINI / GOOGLE_API_KEY
    MISTRAL   MISTRAL_API_KEY / MISTRAL
    CEREBRAS  CEREBRAS_API_KEY / CEREBRAS
    OPENAI    OPENAI_API_KEY
    OLLAMA    OLLAMA_HOST / OLLAMA (local, no key needed if reachable)

Usage:
    from core.llm_client import get_llm
    llm = get_llm()                 # None if no provider available
    if llm:
        text = await llm.complete("summarize: ...", max_tokens=120)
        print(llm.provider, llm.model)
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

# provider -> (env key candidates, base_url, default model, needs_key)
_PROVIDERS = {
    "openrouter": (
        ["OPENROUTER_API_KEY", "OPENROUTER"],
        "https://openrouter.ai/api/v1",
        # override with LLM_MODEL, e.g. perplexity/sonar, google/gemini-2.0-flash-001
        "google/gemini-flash-1.5",
        True,
    ),
    "perplexity": (
        ["PERPLEXITY_API_KEY", "PERPLEXITY"],
        "https://api.perplexity.ai",
        "sonar",
        True,
    ),
    "groq": (
        ["GROQ_API_KEY", "GROQ_API", "GROQ"],
        "https://api.groq.com/openai/v1",
        "llama-3.3-70b-versatile",
        True,
    ),
    "gemini": (
        ["GEMINI_API_KEY", "GEMINI", "GOOGLE_API_KEY"],
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-2.0-flash",
        True,
    ),
    "mistral": (
        ["MISTRAL_API_KEY", "MISTRAL"],
        "https://api.mistral.ai/v1",
        "mistral-small-latest",
        True,
    ),
    "cerebras": (
        ["CEREBRAS_API_KEY", "CEREBRAS"],
        "https://api.cerebras.ai/v1",
        "llama-3.3-70b",
        True,
    ),
    "openai": (
        ["OPENAI_API_KEY"],
        "https://api.openai.com/v1",
        "gpt-4o-mini",
        True,
    ),
    "github": (
        ["GITHUB_TOKEN", "GITHUB_API_KEY"],
        "https://models.inference.ai.azure.com",
        "meta/Llama-4-Scout-17B-16E-Instruct",
        True,
    ),
    "github2": (
        ["GITHUB_TOKEN_2"],
        "https://models.inference.ai.azure.com",
        "deepseek/DeepSeek-V3-0324",
        True,
    ),
    "github3": (
        ["GITHUB_TOKEN_3"],
        "https://models.inference.ai.azure.com",
        "openai/gpt-4o",
        True,
    ),
    "ollama": (
        ["OLLAMA_HOST", "OLLAMA"],
        None,  # resolved from env or localhost default
        "llama3",
        False,
    ),
}

# Detection priority (fast + free first)
_PRIORITY = ["groq", "cerebras", "gemini", "mistral", "github", "openai", "ollama"]

_PLACEHOLDERS = {"", "your_key", "changeme", "xxx", "none"}


def _env_val(candidates: List[str]) -> Optional[str]:
    for name in candidates:
        val = os.getenv(name)
        if val and val.strip().lower() not in _PLACEHOLDERS:
            return val.strip()
    return None


class LLMClient:
    def __init__(self, provider: str, base_url: str, api_key: Optional[str], model: str):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = os.getenv("LLM_MODEL") or model

    async def complete(self, prompt: str, *, system: str = "You are a concise assistant.",
                       max_tokens: int = 160, temperature: float = 0.4, timeout: int = 30) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return (data["choices"][0]["message"]["content"] or "").strip()


def detect_provider() -> Optional[LLMClient]:
    """Return an LLMClient for the first available provider, or None.
    LLM_PROVIDER env forces a specific one (groq/openrouter/perplexity/gemini/…)."""
    forced = (os.getenv("LLM_PROVIDER") or "").lower().strip()
    order = ([forced] if forced in _PROVIDERS else []) + \
        ["groq", "openrouter", "gemini", "cerebras", "mistral", "perplexity",
         "github", "github2", "github3", "openai", "ollama"]
    seen = set()
    for prov in order:
        if prov in seen or prov not in _PROVIDERS:
            continue
        seen.add(prov)
        candidates, base_url, model, needs_key = _PROVIDERS[prov]
        key = _env_val(candidates)
        if needs_key:
            if not key:
                continue
            return LLMClient(prov, base_url, key, model)
        else:
            # ollama: only if a host is configured (avoid hanging on localhost)
            host = key or os.getenv("OLLAMA_HOST")
            if host:
                base = host if host.startswith("http") else f"http://{host}"
                return LLMClient(prov, f"{base}/v1", None, model)
    return None


def _all_clients() -> List["LLMClient"]:
    """Every configured provider, in priority order — used for fallback."""
    forced = (os.getenv("LLM_PROVIDER") or "").lower().strip()
    order = ([forced] if forced in _PROVIDERS else []) + \
        ["groq", "openrouter", "gemini", "cerebras", "mistral", "perplexity",
         "github", "github2", "github3", "openai", "ollama"]
    seen, clients = set(), []
    for prov in order:
        if prov in seen or prov not in _PROVIDERS:
            continue
        seen.add(prov)
        candidates, base_url, model, needs_key = _PROVIDERS[prov]
        key = _env_val(candidates)
        if needs_key and key:
            clients.append(LLMClient(prov, base_url, key, model))
        elif not needs_key:
            host = key or os.getenv("OLLAMA_HOST")
            if host:
                base = host if host.startswith("http") else f"http://{host}"
                clients.append(LLMClient(prov, f"{base}/v1", None, model))
    return clients


class MultiLLM:
    """Tries each configured provider in turn — if one errors / rate-limits, the
    next one answers. So all the user's keys act as redundancy and the LLM never
    silently falls back to keyword matching."""

    def __init__(self, clients: List["LLMClient"]):
        self.clients = clients
        self.provider = "+".join(c.provider for c in clients) or "none"
        self.model = clients[0].model if clients else ""

    async def complete(self, *args, **kwargs) -> str:
        last = None
        for c in self.clients:
            try:
                out = await c.complete(*args, **kwargs)
                if out and out.strip():
                    return out
            except Exception as exc:
                last = exc
                logger.info("llm_client: %s failed (%s) → next", c.provider, exc)
        if last:
            raise last
        raise RuntimeError("no LLM provider available")


_LLM_SINGLETON: Optional["MultiLLM"] = None
_LLM_RESOLVED = False


def get_llm() -> Optional["MultiLLM"]:
    global _LLM_SINGLETON, _LLM_RESOLVED
    if not _LLM_RESOLVED:
        clients = _all_clients()
        _LLM_SINGLETON = MultiLLM(clients) if clients else None
        _LLM_RESOLVED = True
        if _LLM_SINGLETON:
            logger.info("llm_client: chain = %s", _LLM_SINGLETON.provider)
        else:
            logger.info("llm_client: no LLM provider key found")
    return _LLM_SINGLETON

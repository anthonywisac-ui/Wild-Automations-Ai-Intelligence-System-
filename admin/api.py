import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GeminiQATester:
    """Backend QA helper for scraper workflows and AI pipeline sanity checks."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    def _static_snapshot(self) -> Dict[str, Any]:
        issues: List[str] = []
        fixes: List[str] = []

        ai_provider = (os.getenv("AI_PROVIDER") or "passthrough").lower()
        if ai_provider == "gemini" and not self.api_key:
            issues.append("AI_PROVIDER=gemini is set but GEMINI_API_KEY is missing.")
            fixes.append("Set GEMINI_API_KEY or GOOGLE_API_KEY in the environment before starting the backend.")

        if not os.getenv("AI_PROVIDER"):
            issues.append("AI_PROVIDER is not configured; the backend will fall back to passthrough mode.")
            fixes.append("Set AI_PROVIDER=gemini to enable Gemini-assisted QA and summarization.")

        try:
            from config.bot_manifests import bot_manifest
            bots = bot_manifest.get("bots", [])
            if not bots:
                issues.append("No bot manifests were loaded from config/bot_manifests.py.py.")
                fixes.append("Validate the bot manifest and ensure each bot has at least one portal config.")
        except Exception as exc:  # pragma: no cover
            issues.append(f"Bot manifest could not be loaded: {exc}")
            fixes.append("Check config/bot_manifests.py.py and confirm the path and manifest structure are valid.")
            bots = []

        portal_count = 0
        for bot in bots:
            try:
                from config.bot_manifests import iter_bot_portal_configs
                portal_cfgs = list(iter_bot_portal_configs(bot))
                portal_count += len(portal_cfgs)
                for portal_name, portal_config in portal_cfgs:
                    source = portal_config.get("source")
                    if not source:
                        issues.append(f"Bot '{bot.get('bot_name')}' portal '{portal_name}' is missing a source definition.")
                        fixes.append(f"Set a valid 'source' for '{portal_name}' so the scraper can resolve the correct crawler.")
            except Exception as exc:  # pragma: no cover
                issues.append(f"Portal validation failed while inspecting bot manifests: {exc}")
                fixes.append("Fix the portal manifest and re-run backend QA.")

        return {
            "ai_provider": ai_provider,
            "gemini_configured": bool(self.api_key),
            "bots_detected": len(bots),
            "portal_count": portal_count,
            "issues": issues,
            "fixes": fixes,
        }

    async def _chat(self, prompt: str) -> str:
        if not self.api_key:
            return ""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }

        import httpx
        async with httpx.AsyncClient(timeout=60, verify=False) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                params={"key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("candidates"):
                return ""
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            return "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()

    async def run_backend_qa(self) -> Dict[str, Any]:
        snapshot = self._static_snapshot()
        system_status = "ok" if not snapshot["issues"] else "warning"

        if not self.api_key:
            return {
                "status": system_status,
                "provider": "gemini",
                "gemini_configured": False,
                "qa_summary": "Gemini API key not present; static backend QA completed without AI analysis.",
                "issues": snapshot["issues"],
                "fixes": snapshot["fixes"],
                "checks": {
                    "ai_provider": snapshot["ai_provider"],
                    "bots_detected": snapshot["bots_detected"],
                    "portal_count": snapshot["portal_count"],
                },
            }

        prompt = (
            "You are a senior Python backend QA engineer. Review the following backend configuration and "
            "suggest the exact fixes for any problems. Keep your answer as valid JSON with keys: "
            "status, summary, issues, fixes.\n\n"
            f"Data:\n{json.dumps(snapshot, indent=2, default=str)}\n"
            "Return only JSON."
        )

        q_response = await self._chat(prompt)
        parsed: Dict[str, Any] = {"status": "ok", "summary": "Gemini QA passed.", "issues": [], "fixes": []}

        if q_response:
            try:
                cleaned = q_response.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.strip("`")
                    if cleaned.lower().startswith("json"):
                        cleaned = cleaned[4:]
                parsed = json.loads(cleaned)
            except Exception:
                logger.warning("Gemini QA response was not valid JSON; using fallback summary.")

        parsed["issues"] = list(parsed.get("issues", [])) + snapshot["issues"]
        parsed["fixes"] = list(parsed.get("fixes", [])) + snapshot["fixes"]
        parsed["provider"] = "gemini"
        parsed["gemini_configured"] = True
        parsed["checks"] = {
            "ai_provider": snapshot["ai_provider"],
            "bots_detected": snapshot["bots_detected"],
            "portal_count": snapshot["portal_count"],
        }
        parsed["status"] = parsed.get("status", "ok") if parsed.get("issues") is None else parsed.get("status", "warning")
        return parsed


__all__ = ["GeminiQATester"]

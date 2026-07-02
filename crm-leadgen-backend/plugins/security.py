# Inspired By: common security patterns
# Feature: Security utilities for plugins (API key, scopes)
# Reason: Enforce authorization and input sanitisation
# ============================================================

from typing import Optional, List
import logging
from functools import wraps
from ..exceptions import AuthorizationError
from ..config import get_settings

logger = logging.getLogger(__name__)

def require_scope(required_scope: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            scopes = kwargs.get("scopes", [])
            if not scopes:
                if args and hasattr(args[0], "context") and hasattr(args[0].context, "scopes"):
                    scopes = args[0].context.scopes
            if required_scope not in scopes:
                raise AuthorizationError(f"Missing required scope: {required_scope}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def validate_api_key(api_key: str) -> bool:
    settings = get_settings()
    valid_keys = getattr(settings, "plugin_api_keys", [])
    return api_key in valid_keys

def sanitize_input(data: dict) -> dict:
    forbidden = ["__proto__", "constructor", "prototype"]
    return {k: v for k, v in data.items() if k not in forbidden}

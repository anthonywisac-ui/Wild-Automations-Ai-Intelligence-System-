# Inspired By: langchain-ai/langgraph
# Repository: https://github.com/langchain-ai/langgraph
# Feature: Base exception with code, details, and cause tracking
# Reason: Consistent error structure for logging and API responses
# ============================================================

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PlatformException(Exception):
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None) -> None:
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        super().__init__(message)
        logger.debug("Exception: %s - %s", self.code, self.message, extra={"details": self.details}, exc_info=cause)

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class ConfigurationError(PlatformException):
    pass


class ValidationError(PlatformException):
    pass


class NotFoundError(PlatformException):
    pass


class ConflictError(PlatformException):
    pass

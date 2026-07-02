# Inspired By: FastAPI exception handling patterns
# Repository: https://fastapi.tiangolo.com/
# Feature: API-specific exceptions with HTTP status codes
# Reason: Seamless integration with FastAPI exception handlers
# ============================================================

from .base import PlatformException


class APIError(PlatformException):
    status_code: int = 500


class AuthenticationError(APIError):
    status_code = 401


class AuthorizationError(APIError):
    status_code = 403


class BadRequestError(APIError):
    status_code = 400


class TooManyRequestsError(APIError):
    status_code = 429

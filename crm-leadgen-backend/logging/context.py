# Inspired By: langchain-ai/langgraph
# Repository: https://github.com/langchain-ai/langgraph
# Feature: Context managers for tenant/user/correlation IDs
# Reason: Propagate context across async boundaries for traceability
# ============================================================

import contextlib
from contextvars import ContextVar
from typing import Optional, Dict
from uuid import uuid4

from .structlogger import set_correlation_id, get_correlation_id

_tenant_id_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
_user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class LogContext:
    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        set_correlation_id(correlation_id)

    @staticmethod
    def get_correlation_id() -> Optional[str]:
        return get_correlation_id()

    @staticmethod
    def generate_correlation_id() -> str:
        return str(uuid4())

    @staticmethod
    def set_tenant_id(tenant_id: str) -> None:
        _tenant_id_var.set(tenant_id)

    @staticmethod
    def get_tenant_id() -> Optional[str]:
        return _tenant_id_var.get()

    @staticmethod
    def set_user_id(user_id: str) -> None:
        _user_id_var.set(user_id)

    @staticmethod
    def get_user_id() -> Optional[str]:
        return _user_id_var.get()

    @staticmethod
    def get_all() -> Dict[str, Optional[str]]:
        return {
            "correlation_id": get_correlation_id(),
            "tenant_id": _tenant_id_var.get(),
            "user_id": _user_id_var.get(),
        }


@contextlib.asynccontextmanager
async def log_context(correlation_id: Optional[str] = None, tenant_id: Optional[str] = None, user_id: Optional[str] = None):
    old_correlation = get_correlation_id()
    old_tenant = _tenant_id_var.get()
    old_user = _user_id_var.get()
    if correlation_id is None:
        correlation_id = str(uuid4())
    try:
        set_correlation_id(correlation_id)
        if tenant_id is not None:
            _tenant_id_var.set(tenant_id)
        if user_id is not None:
            _user_id_var.set(user_id)
        yield
    finally:
        if old_correlation is not None:
            set_correlation_id(old_correlation)
        else:
            set_correlation_id(None)
        if old_tenant is not None:
            _tenant_id_var.set(old_tenant)
        else:
            _tenant_id_var.set(None)
        if old_user is not None:
            _user_id_var.set(old_user)
        else:
            _user_id_var.set(None)


def set_tenant_id(tenant_id: str) -> None:
    _tenant_id_var.set(tenant_id)

def get_tenant_id() -> Optional[str]:
    return _tenant_id_var.get()

def set_user_id(user_id: str) -> None:
    _user_id_var.set(user_id)

def get_user_id() -> Optional[str]:
    return _user_id_var.get()

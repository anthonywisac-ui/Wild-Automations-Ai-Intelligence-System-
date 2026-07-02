# Inspired By: browser-use/browser-use
# Repository: https://github.com/browser-use/browser-use
# Feature: Structured JSON logger with correlation IDs and context
# Reason: Consistent log format for aggregators and observability platforms
# ============================================================

import logging, json, sys
from typing import Any, Optional
from datetime import datetime, timezone
from contextvars import ContextVar

_correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

def get_correlation_id() -> Optional[str]:
    return _correlation_id_var.get()

def set_correlation_id(correlation_id: str) -> None:
    _correlation_id_var.set(correlation_id)

class JSONFormatter(logging.Formatter):
    def __init__(self, ensure_ascii: bool = False) -> None:
        super().__init__()
        self.ensure_ascii = ensure_ascii

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "correlation_id": get_correlation_id() or "-",
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry.update(record.extra)
        return json.dumps(log_entry, ensure_ascii=self.ensure_ascii)

class StructuredLogger:
    def __init__(self, name: str, level: Optional[int] = None) -> None:
        self._logger = logging.getLogger(name)
        from ..config import get_settings
        settings = get_settings()
        level = level or settings.logging.get_log_level()
        self._logger.setLevel(level)
        if not self._logger.handlers:
            self._configure_handlers()

    def _configure_handlers(self) -> None:
        from ..config import get_settings
        settings = get_settings()
        formatter = JSONFormatter(ensure_ascii=settings.logging.json_ensure_ascii)
        if settings.logging.enable_console:
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(formatter)
            self._logger.addHandler(console)
        if settings.logging.enable_file and settings.logging.file_path:
            from logging.handlers import TimedRotatingFileHandler
            fh = TimedRotatingFileHandler(settings.logging.file_path, when="D", interval=1, backupCount=settings.logging.file_retention)
            fh.setFormatter(formatter)
            self._logger.addHandler(fh)

    def _log(self, level: int, msg: str, **kwargs) -> None:
        extra = kwargs.pop("extra", {})
        if self._logger.isEnabledFor(level):
            extra.setdefault("correlation_id", get_correlation_id() or "-")
            self._logger.log(level, msg, extra=extra, **kwargs)

    def debug(self, msg, **kwargs): self._log(logging.DEBUG, msg, **kwargs)
    def info(self, msg, **kwargs): self._log(logging.INFO, msg, **kwargs)
    def warning(self, msg, **kwargs): self._log(logging.WARNING, msg, **kwargs)
    def error(self, msg, **kwargs): self._log(logging.ERROR, msg, **kwargs)
    def critical(self, msg, **kwargs): self._log(logging.CRITICAL, msg, **kwargs)
    def exception(self, msg, **kwargs): self._log(logging.ERROR, msg, exc_info=True, **kwargs)

    def bind(self, **kwargs) -> "StructuredLogger":
        child = StructuredLogger(self._logger.name)
        child._logger = logging.LoggerAdapter(self._logger, kwargs)
        return child

def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)

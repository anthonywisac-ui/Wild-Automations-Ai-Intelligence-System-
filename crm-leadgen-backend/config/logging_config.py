# Inspired By: browser-use/browser-use
# Repository: https://github.com/browser-use/browser-use
# Feature: Structured logging configuration
# Reason: JSON logging for production observability
# ============================================================

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Literal
import logging


class LoggingSettings(BaseSettings):
    model_config = {"env_prefix": "CRM_LOG_", "case_sensitive": False, "extra": "ignore"}

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field("INFO")
    format: Literal["json", "text"] = Field("json")
    json_ensure_ascii: bool = Field(False)
    enable_console: bool = Field(True)
    enable_file: bool = Field(False)
    file_path: Optional[str] = Field("logs/app.log")
    file_rotation: str = Field("1 day")
    file_retention: int = Field(7)

    def get_log_level(self) -> int:
        return getattr(logging, self.level.upper(), logging.INFO)

# Inspired By: browser-use/browser-use
# Repository: https://github.com/browser-use/browser-use
# Feature: Environment-based configuration with Pydantic Settings
# Reason: Type‑safe config loading with validation and environment prefix
# ============================================================

from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, field_validator
import logging

from .database import DatabaseSettings, RedisSettings, ElasticsearchSettings
from .logging_config import LoggingSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CRM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field("AI Sales Intelligence Platform")
    app_version: str = Field("0.1.0")
    environment: str = Field("development")
    debug: bool = False

    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8000)
    api_secret_key: SecretStr = Field(...)

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    elasticsearch: ElasticsearchSettings = Field(default_factory=ElasticsearchSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    plugin_dirs: List[str] = Field(
        default=["plugins/scrapers", "plugins/channels", "plugins/enrichers"]
    )
    default_request_timeout: int = Field(30)
    scraping_timeout: int = Field(120)
    rate_limit_per_tenant: int = Field(100)
    rate_limit_global: int = Field(1000)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v

    def is_development(self) -> bool:
        return self.environment == "development"

    def is_production(self) -> bool:
        return self.environment == "production"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        logger.info("Settings loaded for environment: %s", _settings.environment)
    return _settings

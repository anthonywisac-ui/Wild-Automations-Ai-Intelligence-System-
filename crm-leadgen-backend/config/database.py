# Inspired By: crawl4AI's configuration pattern
# Repository: https://github.com/unclecode/crawl4AI
# Feature: Nested database configuration models
# Reason: Clean separation of concerns for different datastores
# ============================================================

from typing import Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    model_config = {"env_prefix": "CRM_DB_", "case_sensitive": False, "extra": "ignore"}

    host: str = Field("localhost")
    port: int = Field(5432)
    user: str = Field("postgres")
    password: SecretStr = Field(SecretStr("postgres"))
    database: str = Field("crm")
    pool_size: int = Field(10)
    max_overflow: int = Field(20)
    pool_timeout: int = Field(30)
    pool_recycle: int = Field(3600)
    echo: bool = Field(False)

    @property
    def async_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}"

    @property
    def sync_dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}"


class RedisSettings(BaseSettings):
    model_config = {"env_prefix": "CRM_REDIS_", "case_sensitive": False, "extra": "ignore"}

    host: str = Field("localhost")
    port: int = Field(6379)
    password: Optional[SecretStr] = Field(None)
    db: int = Field(0)
    decode_responses: bool = Field(True)
    max_connections: int = Field(10)
    retry_on_timeout: bool = Field(True)

    @property
    def url(self) -> str:
        auth = f":{self.password.get_secret_value()}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class ElasticsearchSettings(BaseSettings):
    model_config = {"env_prefix": "CRM_ES_", "case_sensitive": False, "extra": "ignore"}

    hosts: list[str] = Field(["http://localhost:9200"])
    username: Optional[str] = Field(None)
    password: Optional[SecretStr] = Field(None)
    verify_certs: bool = Field(True)
    timeout: int = Field(30)
    max_retries: int = Field(3)
    retry_on_timeout: bool = Field(True)

    @field_validator("hosts", mode="before")
    @classmethod
    def parse_hosts(cls, v):
        if isinstance(v, str):
            return [h.strip() for h in v.split(",") if h.strip()]
        return v

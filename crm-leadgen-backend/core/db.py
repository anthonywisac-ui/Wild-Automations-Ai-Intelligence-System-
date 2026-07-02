# Inspired By: SQLAlchemy async patterns
# Feature: Async database client with connection pooling
# Reason: Production-ready PostgreSQL access
# ============================================================

from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from ..config import get_settings
from ..exceptions import DatabaseError

logger = logging.getLogger(__name__)

Base = declarative_base()

class DatabaseClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.dsn = settings.database.async_dsn
        self.pool_size = settings.database.pool_size
        self.max_overflow = settings.database.max_overflow
        self.pool_timeout = settings.database.pool_timeout
        self.echo = settings.database.echo
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None

    async def initialize(self) -> None:
        try:
            self._engine = create_async_engine(self.dsn, pool_size=self.pool_size, max_overflow=self.max_overflow, pool_timeout=self.pool_timeout, pool_pre_ping=True, echo=self.echo)
            self._session_factory = async_sessionmaker(self._engine, class_=AsyncSession, expire_on_commit=False)
            logger.info("Database client initialized")
        except Exception as e:
            raise DatabaseError(f"Database initialization failed: {e}", cause=e)

    async def shutdown(self) -> None:
        if self._engine:
            await self._engine.dispose()
            logger.info("Database engine disposed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if self._session_factory is None:
            raise DatabaseError("Database client not initialized")
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise DatabaseError(f"Database operation failed: {e}", cause=e)
            finally:
                await session.close()

    async def get_session(self) -> AsyncSession:
        if self._session_factory is None:
            raise DatabaseError("Database client not initialized")
        return self._session_factory()

_db_client: Optional[DatabaseClient] = None

def get_db_client() -> DatabaseClient:
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client

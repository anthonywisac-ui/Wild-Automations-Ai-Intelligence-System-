# Inspired By: Conversation queries
# Feature: Conversation repository
# Reason: Manage conversations and messages
# ============================================================

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base import BaseRepository
from ..models import Conversation, Message
from ..logging import get_logger

logger = get_logger(__name__)

class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Conversation, session)

    async def get_by_lead(self, lead_id: UUID, limit: int = 50) -> List[Conversation]:
        return await self.list(lead_id=lead_id, limit=limit)

    async def get_by_external_id(self, external_id: str, channel: str) -> Optional[Conversation]:
        try:
            stmt = select(Conversation).where(Conversation.external_id == external_id, Conversation.channel == channel)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get conversation by external_id %s: %s", external_id, e)
            raise

    async def add_message(self, conversation_id: UUID, sender_type: str, content: str, sender_id: Optional[str] = None, content_type: str = "text", metadata: Optional[dict] = None) -> Message:
        try:
            message = Message(
                conversation_id=conversation_id,
                sender_type=sender_type,
                sender_id=sender_id,
                content=content,
                content_type=content_type,
                metadata=metadata or {},
            )
            self.session.add(message)
            await self.session.flush()
            await self.session.refresh(message)
            return message
        except Exception as e:
            logger.error("Failed to add message to conversation %s: %s", conversation_id, e)
            raise

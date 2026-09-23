from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from domain.chat.classifier import classify_intent
from domain.chat.handlers import (
    handle_greeting,
    handle_linear_read,
    handle_linear_write,
    handle_simple_retrieval,
)
from domain.council import run_council
from domain.schemas.chat import ChatIntent, ChatResponse
from domain.schemas.common import ActorContext


async def route_message(
    session_id: UUID,
    message: str,
    actor: ActorContext,
    db: AsyncSession,
    intent: ChatIntent | None = None,
) -> ChatResponse:
    resolved_intent = intent or await classify_intent(message)

    if resolved_intent == ChatIntent.GREETING:
        return await handle_greeting(session_id, message)
    if resolved_intent == ChatIntent.SIMPLE_RETRIEVAL:
        return await handle_simple_retrieval(session_id, message, actor, db)
    if resolved_intent == ChatIntent.STRATEGIC_SESSION:
        return await run_council(session_id, message)
    if resolved_intent == ChatIntent.LINEAR_READ:
        return await handle_linear_read(session_id, message)
    if resolved_intent == ChatIntent.LINEAR_WRITE:
        return await handle_linear_write(session_id, message)

    return await handle_simple_retrieval(session_id, message, actor, db)

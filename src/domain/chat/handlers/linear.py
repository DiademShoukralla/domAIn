from uuid import UUID

from domain.schemas.chat import ChatIntent, ChatResponse, ResponseKind


async def handle_linear_read(session_id: UUID, message: str) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        content="Linear read request identified, not yet implemented.",
        classified_intent=ChatIntent.LINEAR_READ,
        response_kind=ResponseKind.STUB_NOT_IMPLEMENTED,
    )


async def handle_linear_write(session_id: UUID, message: str) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        content="Linear write request identified, not yet implemented.",
        classified_intent=ChatIntent.LINEAR_WRITE,
        response_kind=ResponseKind.STUB_NOT_IMPLEMENTED,
    )

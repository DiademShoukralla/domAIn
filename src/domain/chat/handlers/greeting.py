from uuid import UUID

from domain.schemas.chat import ChatIntent, ResponseKind, RoutedChatResponse


async def handle_greeting(session_id: UUID, message: str) -> RoutedChatResponse:
    normalized = message.strip().lower()
    if normalized in {"hi", "hello", "hey", "howdy"}:
        content = "Hello! Ask me about the knowledge layer, or bring a strategic question for the council."
    elif "thank" in normalized:
        content = "You're welcome. I'm here whenever you need an answer or a council review."
    else:
        content = (
            "Hi there. I can answer knowledge questions or route strategic reviews to the council."
        )

    return RoutedChatResponse(
        session_id=session_id,
        content=content,
        classified_intent=ChatIntent.GREETING,
        response_kind=ResponseKind.DIRECT_ANSWER,
    )

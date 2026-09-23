from uuid import UUID

from domain.schemas.chat import ChatIntent, ChatResponse, ResponseKind


async def run_council(session_id: UUID, message: str) -> ChatResponse:
    """Pass 3 replaces this stub with the full orchestrator-worker council graph."""
    return ChatResponse(
        session_id=session_id,
        content=(
            "Your question has been classified as strategic and handed off to the decision council. "
            "Council synthesis is not yet available in this environment."
        ),
        classified_intent=ChatIntent.STRATEGIC_SESSION,
        response_kind=ResponseKind.COUNCIL_PENDING_HANDOFF,
    )

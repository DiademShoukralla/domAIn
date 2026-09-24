from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from domain.council.graph import council_graph
from domain.council.status import StatusQueue, emit_supervisor_status
from domain.schemas.chat import ChatIntent, ResponseKind, RoutedChatResponse
from domain.schemas.common import ActorContext, ReviewRequest


async def run_council(
    session_id: UUID,
    message: str,
    actor: ActorContext,
    db: AsyncSession,
    *,
    status_queue: StatusQueue | None = None,
) -> RoutedChatResponse:
    request = ReviewRequest(query=message, project_id=actor.project_id)
    await emit_supervisor_status(status_queue, session_id, "waiting_on_council")
    result = await council_graph.ainvoke(
        {
            "request": request,
            "actor": actor,
            "session_id": session_id,
            "status_queue": status_queue,
            "persona_opinions": [],
            "decision": None,
        }
    )
    decision = result["decision"]
    if decision is None:
        raise RuntimeError("Council graph completed without a decision")

    return RoutedChatResponse(
        session_id=session_id,
        content=decision.synthesis,
        classified_intent=ChatIntent.STRATEGIC_SESSION,
        response_kind=ResponseKind.COUNCIL_RESULT,
        council_decision=decision,
    )

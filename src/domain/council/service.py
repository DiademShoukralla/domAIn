from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from domain.council.graph import council_graph
from domain.schemas.chat import ChatIntent, ChatResponse, ResponseKind
from domain.schemas.common import ActorContext, ReviewRequest


async def run_council(
    session_id: UUID,
    message: str,
    actor: ActorContext,
    db: AsyncSession,
) -> ChatResponse:
    request = ReviewRequest(query=message, project_id=actor.project_id)
    result = await council_graph.ainvoke(
        {
            "request": request,
            "actor": actor,
            "persona_opinions": [],
            "decision": None,
        }
    )
    decision = result["decision"]
    if decision is None:
        raise RuntimeError("Council graph completed without a decision")

    return ChatResponse(
        session_id=session_id,
        content=decision.synthesis,
        classified_intent=ChatIntent.STRATEGIC_SESSION,
        response_kind=ResponseKind.COUNCIL_RESULT,
        council_decision=decision,
    )

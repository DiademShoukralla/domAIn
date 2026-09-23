import asyncio
from typing import Literal
from uuid import UUID

from domain.schemas.chat import ChatStatusUpdate

StatusQueue = asyncio.Queue[ChatStatusUpdate | None]
STATUS_QUEUE_SENTINEL: None = None

SupervisorStatus = Literal["alerting_council", "waiting_on_council", "council_deliberating"]
PersonaStatus = Literal[
    "pondering",
    "researching",
    "giving_recommendation",
    "recommendation_ready",
]


async def emit_status(queue: StatusQueue | None, update: ChatStatusUpdate) -> None:
    if queue is not None:
        await queue.put(update)


async def emit_supervisor_status(
    queue: StatusQueue | None,
    session_id: UUID,
    status: SupervisorStatus,
) -> None:
    await emit_status(
        queue,
        ChatStatusUpdate(session_id=session_id, scope="supervisor", status=status),
    )


async def emit_persona_status(
    queue: StatusQueue | None,
    session_id: UUID,
    persona: str,
    status: PersonaStatus,
) -> None:
    await emit_status(
        queue,
        ChatStatusUpdate(
            session_id=session_id,
            scope="persona",
            persona=persona,
            status=status,
        ),
    )

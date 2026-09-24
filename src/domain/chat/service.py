from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.chat.classifier import classify_intent
from domain.chat.router import route_message
from domain.council.status import STATUS_QUEUE_SENTINEL, StatusQueue
from domain.db.models import ChatMessage, WriteBackProposal
from domain.schemas.chat import (
    ChatIntent,
    ChatMessageOut,
    ChatResponse,
    ChatRole,
    ResponseKind,
)
from domain.schemas.common import ActorContext, Citation, CouncilDecision
from domain.writeback.service import to_proposal_out


def _citation_payload(citations: list[Citation]) -> list[dict[str, object]]:
    return [citation.model_dump(mode="json") for citation in citations]


async def _persist_message(
    db: AsyncSession,
    *,
    session_id: UUID,
    actor: ActorContext,
    role: ChatRole,
    content: str,
    classified_intent: ChatIntent | None = None,
    response_kind: ResponseKind | None = None,
    citations: list[Citation] | None = None,
    council_decision: CouncilDecision | None = None,
) -> ChatMessage:
    record = ChatMessage(
        session_id=session_id,
        user_id=actor.user_id,
        project_id=actor.project_id,
        role=role.value,
        content=content,
        classified_intent=classified_intent.value if classified_intent else None,
        response_kind=response_kind.value if response_kind else None,
        citations=_citation_payload(citations or []),
        council_decision=council_decision.model_dump(mode="json") if council_decision else None,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


def _to_message_out(
    record: ChatMessage,
    proposal: WriteBackProposal | None = None,
) -> ChatMessageOut:
    citations = [Citation.model_validate(item) for item in record.citations]
    council_decision = (
        CouncilDecision.model_validate(record.council_decision)
        if record.council_decision is not None
        else None
    )
    write_back_proposal = to_proposal_out(proposal) if proposal is not None else None
    return ChatMessageOut(
        id=record.id,
        session_id=record.session_id,
        role=ChatRole(record.role),
        content=record.content,
        classified_intent=ChatIntent(record.classified_intent)
        if record.classified_intent
        else None,
        response_kind=ResponseKind(record.response_kind) if record.response_kind else None,
        citations=citations,
        council_decision=council_decision,
        write_back_proposal=write_back_proposal,
        created_at=record.created_at,
    )


async def process_message(
    db: AsyncSession,
    session_id: UUID,
    content: str,
    actor: ActorContext,
    intent: ChatIntent | None = None,
    *,
    status_queue: StatusQueue | None = None,
) -> ChatResponse:
    resolved_intent = intent or await classify_intent(content)

    await _persist_message(
        db,
        session_id=session_id,
        actor=actor,
        role=ChatRole.USER,
        content=content,
        classified_intent=resolved_intent,
    )

    try:
        response = await route_message(
            session_id,
            content,
            actor,
            db,
            intent=resolved_intent,
            status_queue=status_queue,
        )
    finally:
        if status_queue is not None:
            await status_queue.put(STATUS_QUEUE_SENTINEL)

    assistant_record = await _persist_message(
        db,
        session_id=session_id,
        actor=actor,
        role=ChatRole.ASSISTANT,
        content=response.content,
        classified_intent=response.classified_intent,
        response_kind=response.response_kind,
        citations=response.citations,
        council_decision=response.council_decision,
    )
    return ChatResponse(id=assistant_record.id, **response.model_dump())


async def get_session_messages(
    db: AsyncSession,
    session_id: UUID,
    actor: ActorContext,
) -> list[ChatMessageOut]:
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == actor.user_id,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    records = result.scalars().all()
    if not records:
        return []

    message_ids = [record.id for record in records]
    proposals_result = await db.execute(
        select(WriteBackProposal).where(WriteBackProposal.chat_message_id.in_(message_ids))
    )
    proposals_by_message_id = {
        proposal.chat_message_id: proposal for proposal in proposals_result.scalars().all()
    }

    return [_to_message_out(record, proposals_by_message_id.get(record.id)) for record in records]

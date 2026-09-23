from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.db.models import ChatMessage, WriteBackProposal
from domain.permissions import can_access
from domain.schemas.chat import ResponseKind
from domain.schemas.common import ActorContext, CouncilDecision
from domain.schemas.writeback import (
    WriteBackFeedbackEntry,
    WriteBackPlan,
    WriteBackProposalOut,
    WriteBackProposalStatus,
)
from domain.writeback.planner import classify_write_back_plan


def _parse_council_decision(record: ChatMessage) -> CouncilDecision:
    if record.council_decision is None:
        raise HTTPException(status_code=400, detail="Council message has no council decision")
    return CouncilDecision.model_validate(record.council_decision)


def _feedback_strings(proposal: WriteBackProposal) -> list[str]:
    return [str(entry["feedback"]) for entry in proposal.feedback_history]


def _to_proposal_out(proposal: WriteBackProposal) -> WriteBackProposalOut:
    feedback_history = [
        WriteBackFeedbackEntry.model_validate(entry) for entry in proposal.feedback_history
    ]
    return WriteBackProposalOut(
        id=proposal.id,
        chat_message_id=proposal.chat_message_id,
        user_id=proposal.user_id,
        plan=WriteBackPlan.model_validate(proposal.plan),
        feedback_history=feedback_history,
        status=WriteBackProposalStatus(proposal.status),
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
        executed_at=proposal.executed_at,
    )


async def _get_council_message(
    db: AsyncSession,
    message_id: UUID,
    actor: ActorContext,
) -> ChatMessage:
    message = await db.get(ChatMessage, message_id)
    if message is None or not can_access(
        actor.user_id, actor.project_id, message.user_id, message.project_id
    ):
        raise HTTPException(status_code=404, detail="Chat message not found")
    if message.response_kind != ResponseKind.COUNCIL_RESULT.value:
        raise HTTPException(status_code=400, detail="Message is not a council result")
    return message


async def create_write_back_proposal(
    db: AsyncSession,
    message_id: UUID,
    actor: ActorContext,
) -> WriteBackProposalOut:
    message = await _get_council_message(db, message_id, actor)
    council_decision = _parse_council_decision(message)

    existing = await db.execute(
        select(WriteBackProposal).where(WriteBackProposal.chat_message_id == message_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Write-back proposal already exists")

    plan = await classify_write_back_plan(council_decision)
    proposal = WriteBackProposal(
        chat_message_id=message_id,
        user_id=actor.user_id,
        plan=plan.model_dump(mode="json"),
        feedback_history=[],
        status=WriteBackProposalStatus.PROPOSED.value,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return _to_proposal_out(proposal)


async def refine_write_back_proposal(
    db: AsyncSession,
    proposal_id: UUID,
    feedback: str,
    actor: ActorContext,
) -> WriteBackProposalOut:
    proposal = await db.get(WriteBackProposal, proposal_id)
    if proposal is None or not can_access(actor.user_id, actor.project_id, proposal.user_id, None):
        raise HTTPException(status_code=404, detail="Write-back proposal not found")
    if proposal.status != WriteBackProposalStatus.PROPOSED.value:
        raise HTTPException(status_code=400, detail="Proposal is not open for refinement")

    message = await db.get(ChatMessage, proposal.chat_message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Chat message not found")
    council_decision = _parse_council_decision(message)

    feedback_history = _feedback_strings(proposal)
    feedback_history.append(feedback)
    plan = await classify_write_back_plan(council_decision, feedback_history=feedback_history)

    history_entry = WriteBackFeedbackEntry(
        feedback=feedback,
        created_at=datetime.now(UTC),
    )
    updated_history = [*proposal.feedback_history, history_entry.model_dump(mode="json")]
    proposal.plan = plan.model_dump(mode="json")
    proposal.feedback_history = updated_history
    await db.commit()
    await db.refresh(proposal)
    return _to_proposal_out(proposal)

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.middleware import get_actor
from domain.db.session import get_db
from domain.schemas.common import ActorContext
from domain.schemas.writeback import WriteBackProposalOut, WriteBackProposalRefine
from domain.writeback.service import create_write_back_proposal, refine_write_back_proposal

router = APIRouter(tags=["write-back"])


@router.post(
    "/chat/messages/{message_id}/write-back",
    response_model=WriteBackProposalOut,
    status_code=201,
)
async def propose_write_back(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> WriteBackProposalOut:
    return await create_write_back_proposal(db, message_id, actor)


@router.patch("/write-back-proposals/{proposal_id}", response_model=WriteBackProposalOut)
async def refine_proposal(
    proposal_id: UUID,
    payload: WriteBackProposalRefine,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> WriteBackProposalOut:
    return await refine_write_back_proposal(db, proposal_id, payload.feedback, actor)

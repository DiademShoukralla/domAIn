from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.middleware import get_actor
from domain.db.session import get_db
from domain.retrieval.service import retrieve
from domain.schemas.common import ActorContext
from domain.schemas.retrieval import RetrievalRequest, RetrievalResponse

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/query", response_model=RetrievalResponse)
async def query_retrieval(
    payload: RetrievalRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> RetrievalResponse:
    project_id = payload.project_id or actor.project_id
    return await retrieve(
        session=db,
        query=payload.query,
        actor_user_id=actor.user_id,
        actor_project_id=project_id,
        top_k=payload.top_k,
    )

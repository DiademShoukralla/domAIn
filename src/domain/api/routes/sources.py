from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.middleware import get_actor
from domain.db.models import Connection, KnowledgeSource, Provider, SourceStatus, SourceType
from domain.db.session import async_session_factory, get_db
from domain.ingestion.pipeline import index_knowledge_source
from domain.permissions import can_access
from domain.schemas.common import ActorContext
from domain.schemas.sources import (
    KnowledgeSourceCreate,
    KnowledgeSourceListResponse,
    KnowledgeSourceRead,
)

router = APIRouter(prefix="/sources", tags=["sources"])


def _validate_source_type_for_connection(source_type: SourceType, provider: Provider) -> None:
    if source_type == SourceType.GITHUB_REPO and provider != Provider.GITHUB:
        raise HTTPException(
            status_code=400, detail="github_repo sources require a GitHub connection"
        )
    if source_type == SourceType.LINEAR and provider != Provider.LINEAR:
        raise HTTPException(status_code=400, detail="linear sources require a Linear connection")


async def _run_index(source_id: UUID) -> None:
    async with async_session_factory() as session:
        await index_knowledge_source(session, source_id)


@router.get("", response_model=KnowledgeSourceListResponse)
async def list_sources(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> KnowledgeSourceListResponse:
    result = await db.execute(select(KnowledgeSource))
    sources = [
        source
        for source in result.scalars().all()
        if can_access(actor.user_id, actor.project_id, source.user_id, source.project_id)
    ]
    return KnowledgeSourceListResponse(
        sources=[KnowledgeSourceRead.model_validate(item) for item in sources]
    )


@router.post("", response_model=KnowledgeSourceRead, status_code=201)
async def create_source(
    payload: KnowledgeSourceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> KnowledgeSourceRead:
    connection = await db.get(Connection, payload.connection_id)
    if connection is None or not can_access(
        actor.user_id, actor.project_id, connection.user_id, None
    ):
        raise HTTPException(status_code=404, detail="Connection not found")

    _validate_source_type_for_connection(payload.source_type, connection.provider)

    source = KnowledgeSource(
        user_id=actor.user_id,
        project_id=payload.project_id or actor.project_id,
        source_type=payload.source_type,
        external_ref=payload.external_ref,
        connection_id=payload.connection_id,
        name=payload.name,
        status=SourceStatus.PENDING,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    background_tasks.add_task(_run_index, source.id)
    return KnowledgeSourceRead.model_validate(source)


@router.get("/{source_id}", response_model=KnowledgeSourceRead)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> KnowledgeSourceRead:
    source = await db.get(KnowledgeSource, source_id)
    if source is None or not can_access(
        actor.user_id, actor.project_id, source.user_id, source.project_id
    ):
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    return KnowledgeSourceRead.model_validate(source)


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> None:
    source = await db.get(KnowledgeSource, source_id)
    if source is None or not can_access(
        actor.user_id, actor.project_id, source.user_id, source.project_id
    ):
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    await db.delete(source)
    await db.commit()


@router.post("/{source_id}/refresh", response_model=KnowledgeSourceRead)
async def refresh_source(
    source_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> KnowledgeSourceRead:
    source = await db.get(KnowledgeSource, source_id)
    if source is None or not can_access(
        actor.user_id, actor.project_id, source.user_id, source.project_id
    ):
        raise HTTPException(status_code=404, detail="Knowledge source not found")

    source.status = SourceStatus.PENDING
    source.status_message = "Queued for re-indexing"
    await db.commit()
    await db.refresh(source)
    background_tasks.add_task(_run_index, source.id)
    return KnowledgeSourceRead.model_validate(source)

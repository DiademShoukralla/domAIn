from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.middleware import get_actor
from domain.connections.available_sources import (
    ProviderRequestError,
    fetch_github_installation_repositories,
    fetch_linear_teams,
    load_existing_sources_by_ref,
    mark_already_added,
)
from domain.db.models import Connection, Provider
from domain.db.session import get_db
from domain.oauth.linear import get_linear_access_token
from domain.permissions import can_access
from domain.schemas.available_sources import AvailableSourcesResponse
from domain.schemas.common import ActorContext
from domain.schemas.connections import ConnectionListResponse, ConnectionRead

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=ConnectionListResponse)
async def list_connections(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> ConnectionListResponse:
    result = await db.execute(select(Connection))
    connections = [
        connection
        for connection in result.scalars().all()
        if can_access(actor.user_id, actor.project_id, connection.user_id, None)
    ]
    return ConnectionListResponse(
        connections=[ConnectionRead.model_validate(item) for item in connections]
    )


@router.get("/{connection_id}", response_model=ConnectionRead)
async def get_connection(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> ConnectionRead:
    connection = await db.get(Connection, connection_id)
    if connection is None or not can_access(
        actor.user_id, actor.project_id, connection.user_id, None
    ):
        raise HTTPException(status_code=404, detail="Connection not found")
    return ConnectionRead.model_validate(connection)


@router.get("/{connection_id}/available-sources", response_model=AvailableSourcesResponse)
async def list_available_sources(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> AvailableSourcesResponse:
    connection = await db.get(Connection, connection_id)
    if connection is None or not can_access(
        actor.user_id, actor.project_id, connection.user_id, None
    ):
        raise HTTPException(status_code=404, detail="Connection not found")

    existing = await load_existing_sources_by_ref(db, connection_id, actor)

    provider = connection.provider
    installation_id = connection.installation_id
    linear_access_token: str | None = None
    if provider == Provider.LINEAR:
        if not connection.access_token:
            raise HTTPException(
                status_code=403,
                detail="Linear connection is missing an access token. Reconnect Linear.",
            )
        linear_access_token = await get_linear_access_token(db, connection)

    await db.commit()

    try:
        if provider == Provider.GITHUB:
            if not installation_id:
                raise HTTPException(
                    status_code=403,
                    detail="GitHub connection is missing an installation. Reconnect GitHub.",
                )
            items = await fetch_github_installation_repositories(installation_id)
        elif provider == Provider.LINEAR:
            assert linear_access_token is not None
            items = await fetch_linear_teams(linear_access_token)
        else:
            raise HTTPException(status_code=502, detail="Unsupported connection provider")
    except ProviderRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return AvailableSourcesResponse(
        provider=provider,
        items=mark_already_added(items, existing),
    )


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> None:
    connection = await db.get(Connection, connection_id)
    if connection is None or not can_access(
        actor.user_id, actor.project_id, connection.user_id, None
    ):
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(connection)
    await db.commit()

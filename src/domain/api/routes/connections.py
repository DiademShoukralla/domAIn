from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.middleware import get_actor
from domain.db.models import Connection
from domain.db.session import get_db
from domain.permissions import can_access
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

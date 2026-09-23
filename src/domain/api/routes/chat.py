import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket, WebSocketDisconnect

from domain.auth.api_key import validate_api_key
from domain.auth.middleware import get_actor
from domain.chat.service import get_session_messages, process_message
from domain.council.status import STATUS_QUEUE_SENTINEL, StatusQueue
from domain.db.session import async_session_factory, get_db
from domain.schemas.chat import ChatHistoryResponse, ChatMessageIn, ChatResponse
from domain.schemas.common import ActorContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


async def _resolve_actor_from_api_key(api_key: str) -> ActorContext | None:
    async with async_session_factory() as session:
        identity = await validate_api_key(session, api_key)
    if identity is None:
        return None
    user_id, project_id = identity
    return ActorContext(user_id=user_id, project_id=project_id)


async def _cleanup_pipeline_task(task: asyncio.Task[ChatResponse] | None) -> None:
    if task is not None and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@router.websocket("/ws")
async def chat_websocket(
    websocket: WebSocket,
    api_key: str | None = Query(default=None),
) -> None:
    if not api_key:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing API key")
        return

    actor = await _resolve_actor_from_api_key(api_key)
    if actor is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid API key")
        return

    await websocket.accept()
    active_pipeline_task: asyncio.Task[ChatResponse] | None = None
    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            message = ChatMessageIn.model_validate(payload)
            status_queue: StatusQueue = asyncio.Queue()

            async def run_message_pipeline() -> ChatResponse:
                async with async_session_factory() as session:
                    try:
                        return await process_message(
                            db=session,
                            session_id=message.session_id,
                            content=message.content,
                            actor=actor,
                            status_queue=status_queue,
                        )
                    except asyncio.CancelledError:
                        await session.invalidate()
                        raise

            try:
                active_pipeline_task = asyncio.create_task(run_message_pipeline())
                while True:
                    update = await status_queue.get()
                    if update is STATUS_QUEUE_SENTINEL:
                        break
                    await websocket.send_text(update.model_dump_json())

                response = await active_pipeline_task
                await websocket.send_text(response.model_dump_json())
            finally:
                await _cleanup_pipeline_task(active_pipeline_task)
                active_pipeline_task = None
    except asyncio.CancelledError:
        await _cleanup_pipeline_task(active_pipeline_task)
        raise
    except WebSocketDisconnect:
        await _cleanup_pipeline_task(active_pipeline_task)
        return
    except Exception:
        await _cleanup_pipeline_task(active_pipeline_task)
        logger.exception("WebSocket chat handler failed")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal error")


@router.get("/sessions/{session_id}/messages", response_model=ChatHistoryResponse)
async def list_session_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> ChatHistoryResponse:
    messages = await get_session_messages(db, session_id, actor)
    return ChatHistoryResponse(session_id=session_id, messages=messages)

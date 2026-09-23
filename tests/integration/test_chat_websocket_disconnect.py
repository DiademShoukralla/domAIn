import asyncio
import json
import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from sqlalchemy import text
from starlette.websockets import WebSocket, WebSocketDisconnect

from domain.auth.api_key import ensure_bootstrap_api_key
from domain.config import get_settings
from domain.db.session import async_session_factory
from domain.main import app
from domain.schemas.chat import ChatIntent, ChatStatusUpdate, ResponseKind
from domain.schemas.common import ActorContext, CouncilDecision, PersonaOpinion, Verdict


async def _idle_in_transaction_count() -> int:
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT count(*)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND state = 'idle in transaction'
                  AND pid != pg_backend_pid()
                """
            )
        )
        return int(result.scalar_one())


async def _wait_for_no_idle_transactions(*, timeout_seconds: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if await _idle_in_transaction_count() == 0:
            return
        await asyncio.sleep(0.05)
    count = await _idle_in_transaction_count()
    pytest.fail(f"Expected no idle-in-transaction connections, found {count}")


@pytest.mark.asyncio
async def test_websocket_disconnect_cleans_up_pipeline_db_session(db_session) -> None:
    session_id = uuid4()
    settings = get_settings()
    await ensure_bootstrap_api_key(db_session)

    async def slow_run_council(
        council_session_id: object,
        message: str,
        actor: ActorContext,
        db: object,
        *,
        status_queue: asyncio.Queue | None = None,
    ):
        from domain.schemas.chat import ChatIntent, ChatResponse

        if status_queue is not None:
            await status_queue.put(
                ChatStatusUpdate(
                    session_id=council_session_id,
                    scope="supervisor",
                    status="waiting_on_council",
                )
            )
            await status_queue.put(
                ChatStatusUpdate(
                    session_id=council_session_id,
                    scope="supervisor",
                    status="council_deliberating",
                )
            )
        await asyncio.Event().wait()
        return ChatResponse(
            session_id=council_session_id,
            content="unused",
            classified_intent=ChatIntent.STRATEGIC_SESSION,
            response_kind=ResponseKind.COUNCIL_RESULT,
            council_decision=CouncilDecision(
                persona_opinions=[
                    PersonaOpinion(
                        persona="ux",
                        verdict=Verdict.COMMENT,
                        reasoning="unused",
                        citations=[],
                    )
                ],
                overall_verdict=Verdict.COMMENT,
                synthesis="unused",
            ),
        )

    original_send_text = WebSocket.send_text
    send_calls = 0

    async def send_text_disconnect_on_second(self: WebSocket, data: str) -> None:
        nonlocal send_calls
        await original_send_text(self, data)
        send_calls += 1
        if send_calls >= 2:
            raise WebSocketDisconnect(code=1000)

    with (
        patch("domain.chat.service.classify_intent", new_callable=AsyncMock) as classify_mock,
        patch("domain.chat.router.run_council", side_effect=slow_run_council),
        patch.object(WebSocket, "send_text", send_text_disconnect_on_second),
    ):
        classify_mock.return_value = ChatIntent.STRATEGIC_SESSION

        transport = ASGIWebSocketTransport(app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with aconnect_ws(
                f"http://test/chat/ws?api_key={settings.bootstrap_api_key}",
                client,
            ) as ws:
                await ws.send_text(
                    json.dumps({"session_id": str(session_id), "content": "Review this proposal"})
                )
                first_status = json.loads(await ws.receive_text())
                assert first_status["status"] == "alerting_council"

    await db_session.commit()
    await _wait_for_no_idle_transactions()
    assert await _idle_in_transaction_count() == 0

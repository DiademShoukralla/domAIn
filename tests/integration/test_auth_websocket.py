import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from domain.auth.api_key import ensure_bootstrap_api_key
from domain.auth.browser_session import create_browser_session, revoke_browser_session
from domain.config import get_settings
from domain.db.models import User
from domain.main import app
from domain.schemas.chat import ChatIntent, ResponseKind


def _ws_headers(**extra: str) -> dict[str, str]:
    return {"Origin": "http://test", **extra}


@pytest.mark.asyncio
async def test_websocket_accepts_session_cookie_with_allowed_origin(db_session) -> None:
    user = User(github_id=999002, login="ws-user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    raw_token, _record = await create_browser_session(db_session, user.id)

    settings = get_settings()
    with patch("domain.chat.service.classify_intent", new_callable=AsyncMock) as classify_mock:
        classify_mock.return_value = ChatIntent.GREETING
        transport = ASGIWebSocketTransport(app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with aconnect_ws(
                "http://test/chat/ws",
                client,
                headers={
                    **_ws_headers(),
                    "Cookie": f"{settings.session_cookie_name}={raw_token}",
                },
            ) as ws:
                await ws.send_text(json.dumps({"session_id": str(uuid4()), "content": "ping"}))
                frame = json.loads(await ws.receive_text())
                assert frame["classified_intent"] == ChatIntent.GREETING.value
                assert frame["response_kind"] == ResponseKind.DIRECT_ANSWER.value
                assert frame["id"]


@pytest.mark.asyncio
async def test_websocket_rejects_missing_cookie() -> None:
    transport = ASGIWebSocketTransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(Exception):
            async with aconnect_ws(
                "http://test/chat/ws",
                client,
                headers=_ws_headers(),
            ):
                pass


@pytest.mark.asyncio
async def test_websocket_rejects_revoked_session(db_session) -> None:
    user = User(github_id=999003, login="revoked-user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    raw_token, _record = await create_browser_session(db_session, user.id)
    await revoke_browser_session(db_session, raw_token)

    settings = get_settings()
    transport = ASGIWebSocketTransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(Exception):
            async with aconnect_ws(
                "http://test/chat/ws",
                client,
                headers={
                    **_ws_headers(),
                    "Cookie": f"{settings.session_cookie_name}={raw_token}",
                },
            ):
                pass


@pytest.mark.asyncio
async def test_websocket_rejects_wrong_origin(db_session) -> None:
    user = User(github_id=999004, login="origin-user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    raw_token, _record = await create_browser_session(db_session, user.id)
    settings = get_settings()

    transport = ASGIWebSocketTransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(Exception):
            async with aconnect_ws(
                "http://test/chat/ws",
                client,
                headers={
                    "Origin": "http://evil.example",
                    "Cookie": f"{settings.session_cookie_name}={raw_token}",
                },
            ):
                pass


@pytest.mark.asyncio
async def test_websocket_accepts_api_key_without_origin(db_session) -> None:
    await ensure_bootstrap_api_key(db_session)
    settings = get_settings()
    with patch("domain.chat.service.classify_intent", new_callable=AsyncMock) as classify_mock:
        classify_mock.return_value = ChatIntent.GREETING
        transport = ASGIWebSocketTransport(app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with aconnect_ws(
                "http://test/chat/ws",
                client,
                headers={"X-API-Key": settings.bootstrap_api_key},
            ) as ws:
                await ws.send_text(json.dumps({"session_id": str(uuid4()), "content": "ping"}))
                frame = json.loads(await ws.receive_text())
                assert frame["classified_intent"] == ChatIntent.GREETING.value
                assert frame["response_kind"] == ResponseKind.DIRECT_ANSWER.value
                assert frame["id"]


@pytest.mark.asyncio
async def test_websocket_still_accepts_api_key_with_allowed_origin(db_session) -> None:
    await ensure_bootstrap_api_key(db_session)
    settings = get_settings()
    with patch("domain.chat.service.classify_intent", new_callable=AsyncMock) as classify_mock:
        classify_mock.return_value = ChatIntent.GREETING
        transport = ASGIWebSocketTransport(app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with aconnect_ws(
                "http://test/chat/ws",
                client,
                headers={
                    **_ws_headers(),
                    "X-API-Key": settings.bootstrap_api_key,
                },
            ) as ws:
                await ws.send_text(json.dumps({"session_id": str(uuid4()), "content": "ping"}))
                frame = json.loads(await ws.receive_text())
                assert frame["classified_intent"] == ChatIntent.GREETING.value
                assert frame["response_kind"] == ResponseKind.DIRECT_ANSWER.value
                assert frame["id"]

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from starlette.testclient import TestClient

from domain.config import get_settings
from domain.main import app
from domain.schemas.chat import ChatIntent, ResponseKind


@pytest.mark.asyncio
async def test_chat_history_persists_messages(db_session) -> None:
    session_id = uuid4()
    settings = get_settings()

    with (
        patch("domain.chat.router.classify_intent", new_callable=AsyncMock) as classify_mock,
        patch("domain.chat.handlers.retrieval.retrieve", new_callable=AsyncMock) as retrieve_mock,
        patch(
            "domain.chat.handlers.retrieval.get_retrieval_answer_model",
        ) as model_factory_mock,
    ):
        classify_mock.return_value = ChatIntent.GREETING

        transport = ASGIWebSocketTransport(app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with aconnect_ws(
                f"http://test/chat/ws?api_key={settings.bootstrap_api_key}",
                client,
            ) as ws:
                await ws.send_text(
                    json.dumps({"session_id": str(session_id), "content": "Hello there"})
                )
                response = json.loads(await ws.receive_text())

            assert response["classified_intent"] == ChatIntent.GREETING.value
            assert response["response_kind"] == ResponseKind.DIRECT_ANSWER.value
            retrieve_mock.assert_not_called()
            model_factory_mock.assert_not_called()

            history = await client.get(
                f"/chat/sessions/{session_id}/messages",
                headers={"X-API-Key": settings.bootstrap_api_key},
            )
            assert history.status_code == 200
            payload = history.json()
            assert len(payload["messages"]) == 2
            assert payload["messages"][0]["role"] == "user"
            assert payload["messages"][1]["role"] == "assistant"


def test_websocket_rejects_missing_api_key() -> None:
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/chat/ws"):
            pass


def test_websocket_rejects_invalid_api_key() -> None:
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/chat/ws?api_key=not-a-real-key"):
            pass

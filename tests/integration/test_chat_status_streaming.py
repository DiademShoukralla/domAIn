import asyncio
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from domain.auth.api_key import ensure_bootstrap_api_key
from domain.config import get_settings
from domain.main import app
from domain.schemas.chat import ChatIntent, ResponseKind
from domain.schemas.common import (
    ActorContext,
    CouncilDecision,
    PersonaOpinion,
    Verdict,
)


def _make_opinion(persona: str) -> PersonaOpinion:
    return PersonaOpinion(
        persona=persona,
        verdict=Verdict.COMMENT,
        reasoning=f"{persona} reasoning",
        citations=[],
    )


@pytest.mark.asyncio
async def test_websocket_streams_status_frames_before_final_response(db_session) -> None:
    session_id = uuid4()
    settings = get_settings()
    decision = CouncilDecision(
        persona_opinions=[
            _make_opinion("ux"),
            _make_opinion("dev_experience"),
            _make_opinion("business"),
        ],
        overall_verdict=Verdict.COMMENT,
        synthesis="Proceed with caution.",
    )

    async def fake_run_council(
        session_id: object,
        message: str,
        actor: ActorContext,
        db: object,
        *,
        status_queue: asyncio.Queue | None = None,
    ):
        from domain.schemas.chat import ChatIntent, ChatResponse, ResponseKind

        if status_queue is not None:
            from domain.schemas.chat import ChatStatusUpdate

            await status_queue.put(
                ChatStatusUpdate(
                    session_id=session_id,
                    scope="supervisor",
                    status="waiting_on_council",
                )
            )
            await status_queue.put(
                ChatStatusUpdate(
                    session_id=session_id,
                    scope="persona",
                    persona="ux",
                    status="recommendation_ready",
                )
            )
            await status_queue.put(
                ChatStatusUpdate(
                    session_id=session_id,
                    scope="supervisor",
                    status="council_deliberating",
                )
            )
        return ChatResponse(
            session_id=session_id,
            content=decision.synthesis,
            classified_intent=ChatIntent.STRATEGIC_SESSION,
            response_kind=ResponseKind.COUNCIL_RESULT,
            council_decision=decision,
        )

    with (
        patch("domain.chat.service.classify_intent", new_callable=AsyncMock) as classify_mock,
        patch("domain.chat.router.run_council", side_effect=fake_run_council),
    ):
        classify_mock.return_value = ChatIntent.STRATEGIC_SESSION
        await ensure_bootstrap_api_key(db_session)

        transport = ASGIWebSocketTransport(app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with aconnect_ws(
                f"http://test/chat/ws?api_key={settings.bootstrap_api_key}",
                client,
            ) as ws:
                await ws.send_text(
                    json.dumps({"session_id": str(session_id), "content": "Review this proposal"})
                )

                frames: list[dict[str, object]] = []
                while True:
                    frame = json.loads(await ws.receive_text())
                    frames.append(frame)
                    if "response_kind" in frame:
                        break

    status_frames = [frame for frame in frames if "scope" in frame]
    final_frame = frames[-1]

    assert len(status_frames) == 4
    assert status_frames[0]["status"] == "alerting_council"
    assert status_frames[1]["status"] == "waiting_on_council"
    assert status_frames[2]["persona"] == "ux"
    assert status_frames[3]["status"] == "council_deliberating"
    assert final_frame["response_kind"] == ResponseKind.COUNCIL_RESULT.value
    assert final_frame["classified_intent"] == ChatIntent.STRATEGIC_SESSION.value

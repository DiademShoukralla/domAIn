"""Regression: write-back must work on a live council result id from the WebSocket frame."""

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
from domain.schemas.writeback import WriteBackPlan


def _sample_council_decision() -> CouncilDecision:
    return CouncilDecision(
        persona_opinions=[
            PersonaOpinion(
                persona="ux",
                verdict=Verdict.REQUEST_CHANGES,
                reasoning="Needs clearer acceptance criteria",
                citations=[],
            )
        ],
        overall_verdict=Verdict.REQUEST_CHANGES,
        synthesis="Request changes to clarify scope",
    )


def _sample_plan() -> WriteBackPlan:
    return WriteBackPlan(
        needs_doc_update=True,
        doc_target="new",
        existing_doc_path=None,
        new_doc_slug="council-scope",
        needs_roadmap_item=False,
    )


@pytest.mark.asyncio
async def test_live_council_response_id_allows_immediate_write_back(db_session) -> None:
    """Use the WebSocket final frame id to propose write-back without a history reload."""
    session_id = uuid4()
    settings = get_settings()
    decision = _sample_council_decision()

    async def fake_run_council(
        session_id: object,
        message: str,
        actor: ActorContext,
        db: object,
        *,
        status_queue: object | None = None,
    ):
        from domain.schemas.chat import ChatIntent, ResponseKind, RoutedChatResponse

        return RoutedChatResponse(
            session_id=session_id,
            content=decision.synthesis,
            classified_intent=ChatIntent.STRATEGIC_SESSION,
            response_kind=ResponseKind.COUNCIL_RESULT,
            council_decision=decision,
        )

    with (
        patch("domain.chat.service.classify_intent", new_callable=AsyncMock) as classify_mock,
        patch("domain.chat.router.run_council", side_effect=fake_run_council),
        patch(
            "domain.writeback.service.classify_write_back_plan",
            new_callable=AsyncMock,
        ) as classify_plan_mock,
    ):
        classify_mock.return_value = ChatIntent.STRATEGIC_SESSION
        classify_plan_mock.return_value = _sample_plan()
        await ensure_bootstrap_api_key(db_session)

        transport = ASGIWebSocketTransport(app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with aconnect_ws(
                f"http://test/chat/ws?api_key={settings.bootstrap_api_key}",
                client,
            ) as ws:
                await ws.send_text(
                    json.dumps(
                        {
                            "session_id": str(session_id),
                            "content": "Should we ship feature X?",
                        }
                    )
                )

                final_frame: dict[str, object] | None = None
                while True:
                    frame = json.loads(await ws.receive_text())
                    if "response_kind" in frame:
                        final_frame = frame
                        break

            assert final_frame is not None
            assert final_frame["response_kind"] == ResponseKind.COUNCIL_RESULT.value
            message_id = final_frame["id"]
            assert message_id

            write_back_response = await client.post(
                f"/chat/messages/{message_id}/write-back",
                headers={"X-API-Key": settings.bootstrap_api_key},
            )

        assert write_back_response.status_code == 201
        payload = write_back_response.json()
        assert payload["chat_message_id"] == message_id
        assert payload["status"] == "proposed"
        assert payload["plan"]["new_doc_slug"] == "council-scope"

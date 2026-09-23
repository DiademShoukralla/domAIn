from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from domain.chat.router import route_message
from domain.schemas.chat import ChatIntent, ResponseKind
from domain.schemas.common import ActorContext


@pytest.mark.asyncio
async def test_route_greeting_does_not_call_retrieval() -> None:
    actor = ActorContext(user_id=uuid4())
    session_id = uuid4()

    with patch("domain.chat.router.handle_simple_retrieval", new_callable=AsyncMock) as retrieval_mock:
        response = await route_message(
            session_id=session_id,
            message="Hello!",
            actor=actor,
            db=AsyncMock(),
            intent=ChatIntent.GREETING,
        )

    retrieval_mock.assert_not_called()
    assert response.classified_intent == ChatIntent.GREETING
    assert response.response_kind == ResponseKind.DIRECT_ANSWER


@pytest.mark.asyncio
async def test_route_strategic_session_hands_off_to_council() -> None:
    actor = ActorContext(user_id=uuid4())
    session_id = uuid4()

    response = await route_message(
        session_id=session_id,
        message="Review this proposal",
        actor=actor,
        db=AsyncMock(),
        intent=ChatIntent.STRATEGIC_SESSION,
    )

    assert response.classified_intent == ChatIntent.STRATEGIC_SESSION
    assert response.response_kind == ResponseKind.COUNCIL_PENDING_HANDOFF


@pytest.mark.asyncio
async def test_route_linear_stubs_return_not_implemented() -> None:
    actor = ActorContext(user_id=uuid4())
    session_id = uuid4()

    read_response = await route_message(
        session_id=session_id,
        message="Show Linear issue 1",
        actor=actor,
        db=AsyncMock(),
        intent=ChatIntent.LINEAR_READ,
    )
    write_response = await route_message(
        session_id=session_id,
        message="Update Linear issue 1",
        actor=actor,
        db=AsyncMock(),
        intent=ChatIntent.LINEAR_WRITE,
    )

    assert read_response.response_kind == ResponseKind.STUB_NOT_IMPLEMENTED
    assert write_response.response_kind == ResponseKind.STUB_NOT_IMPLEMENTED

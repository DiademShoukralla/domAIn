from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from domain.auth.api_key import ensure_bootstrap_api_key
from domain.config import get_settings
from domain.db.models import ChatMessage
from domain.main import app
from domain.schemas.chat import ChatIntent, ResponseKind
from domain.schemas.common import CouncilDecision, PersonaOpinion, Verdict
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
        needs_roadmap_item=True,
    )


@pytest.mark.asyncio
async def test_create_and_refine_write_back_proposal(db_session) -> None:
    settings = get_settings()
    await ensure_bootstrap_api_key(db_session)

    message = ChatMessage(
        session_id=uuid4(),
        user_id=settings.default_user_id,
        project_id=None,
        role="assistant",
        content="Council result",
        classified_intent=ChatIntent.STRATEGIC_SESSION.value,
        response_kind=ResponseKind.COUNCIL_RESULT.value,
        citations=[],
        council_decision=_sample_council_decision().model_dump(mode="json"),
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    initial_plan = _sample_plan()
    refined_plan = WriteBackPlan(
        needs_doc_update=True,
        doc_target="new",
        existing_doc_path=None,
        new_doc_slug="council-scope-refined",
        needs_roadmap_item=False,
    )

    with patch(
        "domain.writeback.service.classify_write_back_plan",
        new_callable=AsyncMock,
    ) as classify_mock:
        classify_mock.side_effect = [initial_plan, refined_plan]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post(
                f"/chat/messages/{message.id}/write-back",
                headers={"X-API-Key": settings.bootstrap_api_key},
            )
            assert create_response.status_code == 201
            created = create_response.json()
            assert created["plan"]["new_doc_slug"] == "council-scope"
            assert created["status"] == "proposed"
            assert created["feedback_history"] == []

            refine_response = await client.patch(
                f"/write-back-proposals/{created['id']}",
                headers={"X-API-Key": settings.bootstrap_api_key},
                json={"feedback": "Skip the roadmap item"},
            )
            assert refine_response.status_code == 200
            refined = refine_response.json()
            assert refined["id"] == created["id"]
            assert refined["plan"]["new_doc_slug"] == "council-scope-refined"
            assert refined["plan"]["needs_roadmap_item"] is False
            assert len(refined["feedback_history"]) == 1
            assert refined["feedback_history"][0]["feedback"] == "Skip the roadmap item"

            duplicate_response = await client.post(
                f"/chat/messages/{message.id}/write-back",
                headers={"X-API-Key": settings.bootstrap_api_key},
            )
            assert duplicate_response.status_code == 409


@pytest.mark.asyncio
async def test_write_back_requires_council_result(db_session) -> None:
    settings = get_settings()
    await ensure_bootstrap_api_key(db_session)

    message = ChatMessage(
        session_id=uuid4(),
        user_id=settings.default_user_id,
        project_id=None,
        role="assistant",
        content="Not a council result",
        classified_intent=ChatIntent.GREETING.value,
        response_kind=ResponseKind.DIRECT_ANSWER.value,
        citations=[],
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/chat/messages/{message.id}/write-back",
            headers={"X-API-Key": settings.bootstrap_api_key},
        )
        assert response.status_code == 400

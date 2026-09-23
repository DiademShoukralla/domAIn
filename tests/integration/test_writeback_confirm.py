from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from domain.auth.api_key import ensure_bootstrap_api_key
from domain.config import get_settings
from domain.db.models import (
    ChatMessage,
    Connection,
    KnowledgeSource,
    Provider,
    SourceStatus,
    SourceType,
    WriteBackProposal,
)
from domain.main import app
from domain.schemas.chat import ChatIntent, ChatRole, ResponseKind
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


@pytest.fixture
async def writeback_fixtures(db_session):
    settings = get_settings()
    await ensure_bootstrap_api_key(db_session)

    user_message = ChatMessage(
        session_id=uuid4(),
        user_id=settings.default_user_id,
        project_id=None,
        role=ChatRole.USER.value,
        content="Should we ship feature X?",
        classified_intent=ChatIntent.STRATEGIC_SESSION.value,
        response_kind=None,
        citations=[],
    )
    council_message = ChatMessage(
        session_id=user_message.session_id,
        user_id=settings.default_user_id,
        project_id=None,
        role=ChatRole.ASSISTANT.value,
        content="Council result",
        classified_intent=ChatIntent.STRATEGIC_SESSION.value,
        response_kind=ResponseKind.COUNCIL_RESULT.value,
        citations=[],
        council_decision=_sample_council_decision().model_dump(mode="json"),
    )
    db_session.add(user_message)
    db_session.add(council_message)
    await db_session.commit()
    await db_session.refresh(council_message)

    github_connection = Connection(
        user_id=settings.default_user_id,
        provider=Provider.GITHUB,
        installation_id="12345",
        external_account_id="12345",
        external_account_name="test-user",
    )
    linear_connection = Connection(
        user_id=settings.default_user_id,
        provider=Provider.LINEAR,
        access_token="encrypted-token",
        external_account_id="linear-user",
        external_account_name="Linear User",
    )
    db_session.add(github_connection)
    db_session.add(linear_connection)
    await db_session.commit()
    await db_session.refresh(github_connection)
    await db_session.refresh(linear_connection)

    github_source = KnowledgeSource(
        user_id=settings.default_user_id,
        project_id=None,
        source_type=SourceType.GITHUB_REPO,
        external_ref="owner/repo",
        connection_id=github_connection.id,
        name="Test Repo",
        status=SourceStatus.READY,
    )
    linear_source = KnowledgeSource(
        user_id=settings.default_user_id,
        project_id=None,
        source_type=SourceType.LINEAR,
        external_ref="team-uuid",
        connection_id=linear_connection.id,
        name="Test Team",
        status=SourceStatus.READY,
    )
    db_session.add(github_source)
    db_session.add(linear_source)
    await db_session.commit()

    return {
        "settings": settings,
        "council_message": council_message,
    }


@pytest.mark.asyncio
async def test_confirm_new_doc_and_linear_executes_and_marks_executed(
    db_session,
    writeback_fixtures,
) -> None:
    settings = writeback_fixtures["settings"]
    council_message = writeback_fixtures["council_message"]
    plan = WriteBackPlan(
        needs_doc_update=True,
        doc_target="new",
        existing_doc_path=None,
        new_doc_slug="council-scope",
        needs_roadmap_item=True,
    )
    proposal = WriteBackProposal(
        chat_message_id=council_message.id,
        user_id=settings.default_user_id,
        project_id=None,
        plan=plan.model_dump(mode="json"),
        feedback_history=[],
        status="proposed",
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)

    with (
        patch(
            "domain.writeback.service._execute_github_doc_write",
            new=AsyncMock(return_value="https://github.com/owner/repo/pull/1"),
        ) as github_mock,
        patch(
            "domain.writeback.service._execute_linear_roadmap_write",
            new=AsyncMock(return_value="https://linear.app/issue/DIDI-1"),
        ) as linear_mock,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/write-back-proposals/{proposal.id}/confirm",
                headers={"X-API-Key": settings.bootstrap_api_key},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "executed"
    assert payload["executed_at"] is not None
    github_mock.assert_awaited_once()
    linear_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_existing_doc_plan_passes_existing_path(
    db_session,
    writeback_fixtures,
) -> None:
    settings = writeback_fixtures["settings"]
    council_message = writeback_fixtures["council_message"]
    plan = WriteBackPlan(
        needs_doc_update=True,
        doc_target="existing",
        existing_doc_path="docs/adr/0002-tech-stack.md",
        new_doc_slug=None,
        needs_roadmap_item=False,
    )
    proposal = WriteBackProposal(
        chat_message_id=council_message.id,
        user_id=settings.default_user_id,
        project_id=None,
        plan=plan.model_dump(mode="json"),
        feedback_history=[],
        status="proposed",
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)

    with patch(
        "domain.writeback.service._execute_github_doc_write",
        new=AsyncMock(return_value="https://github.com/owner/repo/pull/2"),
    ) as github_mock:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/write-back-proposals/{proposal.id}/confirm",
                headers={"X-API-Key": settings.bootstrap_api_key},
            )

    assert response.status_code == 200
    call_kwargs = github_mock.await_args.kwargs
    assert call_kwargs["plan"].doc_target == "existing"
    assert call_kwargs["plan"].existing_doc_path == "docs/adr/0002-tech-stack.md"


@pytest.mark.asyncio
async def test_confirm_rejects_second_execution(db_session, writeback_fixtures) -> None:
    settings = writeback_fixtures["settings"]
    council_message = writeback_fixtures["council_message"]
    plan = WriteBackPlan(
        needs_doc_update=False,
        doc_target=None,
        existing_doc_path=None,
        new_doc_slug=None,
        needs_roadmap_item=True,
    )
    proposal = WriteBackProposal(
        chat_message_id=council_message.id,
        user_id=settings.default_user_id,
        project_id=None,
        plan=plan.model_dump(mode="json"),
        feedback_history=[],
        status="proposed",
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)

    with patch(
        "domain.writeback.service._execute_linear_roadmap_write",
        new=AsyncMock(return_value="https://linear.app/issue/DIDI-2"),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                f"/write-back-proposals/{proposal.id}/confirm",
                headers={"X-API-Key": settings.bootstrap_api_key},
            )
            second = await client.post(
                f"/write-back-proposals/{proposal.id}/confirm",
                headers={"X-API-Key": settings.bootstrap_api_key},
            )

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["detail"] == "Proposal is not open for confirmation"


@pytest.mark.asyncio
async def test_confirm_leaves_status_proposed_on_partial_failure(
    db_session,
    writeback_fixtures,
) -> None:
    settings = writeback_fixtures["settings"]
    council_message = writeback_fixtures["council_message"]
    plan = WriteBackPlan(
        needs_doc_update=True,
        doc_target="new",
        existing_doc_path=None,
        new_doc_slug="council-scope",
        needs_roadmap_item=True,
    )
    proposal = WriteBackProposal(
        chat_message_id=council_message.id,
        user_id=settings.default_user_id,
        project_id=None,
        plan=plan.model_dump(mode="json"),
        feedback_history=[],
        status="proposed",
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)

    with (
        patch(
            "domain.writeback.service._execute_github_doc_write",
            new=AsyncMock(return_value="https://github.com/owner/repo/pull/3"),
        ),
        patch(
            "domain.writeback.service._execute_linear_roadmap_write",
            new=AsyncMock(side_effect=RuntimeError("Linear failed after GitHub branch created")),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/write-back-proposals/{proposal.id}/confirm",
                headers={"X-API-Key": settings.bootstrap_api_key},
            )

    assert response.status_code == 500
    refreshed = await db_session.get(WriteBackProposal, proposal.id)
    assert refreshed is not None
    assert refreshed.status == "proposed"
    assert refreshed.executed_at is None

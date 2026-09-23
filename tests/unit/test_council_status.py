import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from domain.council.graph import council_graph
from domain.council.personas import PERSONA_IDS, PersonaOpinionOutput, run_persona
from domain.council.service import run_council
from domain.council.status import STATUS_QUEUE_SENTINEL
from domain.schemas.chat import ChatIntent, ResponseKind
from domain.schemas.common import (
    ActorContext,
    Citation,
    CouncilDecision,
    PersonaOpinion,
    ReviewRequest,
    Verdict,
)


def _make_opinion(persona: str) -> PersonaOpinion:
    return PersonaOpinion(
        persona=persona,
        verdict=Verdict.COMMENT,
        reasoning=f"{persona} reasoning",
        citations=[
            Citation(
                document_id=f"doc-{persona}",
                chunk_index=0,
                knowledge_source_id=uuid4(),
                excerpt="excerpt",
            )
        ],
    )


def _make_decision(opinions: list[PersonaOpinion]) -> CouncilDecision:
    return CouncilDecision(
        persona_opinions=opinions,
        overall_verdict=Verdict.COMMENT,
        synthesis="The council recommends proceeding with caution.",
    )


async def _collect_statuses(
    queue: asyncio.Queue,
    *,
    expected_count: int | None = None,
    wait_for_sentinel: bool = False,
) -> list[dict[str, object]]:
    statuses: list[dict[str, object]] = []
    while True:
        if expected_count is not None and len(statuses) >= expected_count and not wait_for_sentinel:
            break
        item = await queue.get()
        if item is STATUS_QUEUE_SENTINEL:
            break
        statuses.append(item.model_dump(mode="json"))
    return statuses


@pytest.mark.asyncio
async def test_run_persona_emits_lifecycle_statuses_in_order() -> None:
    actor = ActorContext(user_id=uuid4())
    session_id = uuid4()
    queue: asyncio.Queue = asyncio.Queue()
    request = ReviewRequest(query="Should we ship this?")

    with (
        patch(
            "domain.council.personas.retrieve",
            new_callable=AsyncMock,
            return_value=type("Retrieval", (), {"chunks": []})(),
        ),
        patch("domain.council.personas.get_persona_model") as model_factory_mock,
    ):
        model = AsyncMock()
        model.ainvoke = AsyncMock(
            return_value=PersonaOpinionOutput(
                verdict=Verdict.APPROVE,
                reasoning="Looks good",
            )
        )
        model_factory_mock.return_value.with_structured_output.return_value = model

        await run_persona(
            persona="ux",
            request=request,
            actor=actor,
            db=AsyncMock(),
            session_id=session_id,
            status_queue=queue,
        )

    statuses = await _collect_statuses(queue, expected_count=4)
    assert [item["status"] for item in statuses] == [
        "pondering",
        "researching",
        "giving_recommendation",
        "recommendation_ready",
    ]
    assert all(item["scope"] == "persona" and item["persona"] == "ux" for item in statuses)
    assert all(item["session_id"] == str(session_id) for item in statuses)


@pytest.mark.asyncio
async def test_council_graph_emits_council_deliberating_from_chair() -> None:
    actor = ActorContext(user_id=uuid4())
    session_id = uuid4()
    queue: asyncio.Queue = asyncio.Queue()
    request = ReviewRequest(query="Should we migrate chunking to semantic splitting?")

    async def fake_run_persona(
        persona: str,
        request: ReviewRequest,
        actor: ActorContext,
        db: object,
        *,
        session_id: object,
        status_queue: object,
    ) -> PersonaOpinion:
        return _make_opinion(persona)

    opinions = [_make_opinion(persona) for persona in PERSONA_IDS]

    with (
        patch("domain.council.graph.run_persona", side_effect=fake_run_persona),
        patch(
            "domain.council.graph.synthesize_decision",
            new_callable=AsyncMock,
            return_value=_make_decision(opinions),
        ),
    ):
        await council_graph.ainvoke(
            {
                "request": request,
                "actor": actor,
                "session_id": session_id,
                "status_queue": queue,
                "persona_opinions": [],
                "decision": None,
            }
        )

    statuses = await _collect_statuses(queue, expected_count=1)
    supervisor_statuses = [item["status"] for item in statuses if item["scope"] == "supervisor"]
    persona_statuses = [item for item in statuses if item["scope"] == "persona"]

    assert supervisor_statuses == ["council_deliberating"]
    assert len(persona_statuses) == 0


@pytest.mark.asyncio
async def test_run_council_emits_waiting_on_council_before_graph() -> None:
    actor = ActorContext(user_id=uuid4())
    session_id = uuid4()
    queue: asyncio.Queue = asyncio.Queue()
    opinions = [_make_opinion(persona) for persona in PERSONA_IDS]
    decision = _make_decision(opinions)

    with patch(
        "domain.council.service.council_graph.ainvoke",
        new_callable=AsyncMock,
        return_value={"decision": decision, "persona_opinions": opinions},
    ):
        response = await run_council(
            session_id=session_id,
            message="Review this proposal",
            actor=actor,
            db=AsyncMock(),
            status_queue=queue,
        )

    statuses = await _collect_statuses(queue, expected_count=1)
    assert statuses[0]["scope"] == "supervisor"
    assert statuses[0]["status"] == "waiting_on_council"
    assert response.response_kind == ResponseKind.COUNCIL_RESULT
    assert response.classified_intent == ChatIntent.STRATEGIC_SESSION

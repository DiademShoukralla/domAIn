from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from domain.council.graph import council_graph
from domain.council.personas import PERSONA_IDS
from domain.council.service import run_council
from domain.schemas.chat import ResponseKind
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


@pytest.mark.asyncio
async def test_council_graph_invokes_all_three_personas() -> None:
    actor = ActorContext(user_id=uuid4())
    request = ReviewRequest(query="Should we migrate chunking to semantic splitting?")
    invoked_personas: list[str] = []

    async def fake_run_persona(
        persona: str,
        request: ReviewRequest,
        actor: ActorContext,
        db: object,
        *,
        session_id: object,
        status_queue: object = None,
    ) -> PersonaOpinion:
        invoked_personas.append(persona)
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
        result = await council_graph.ainvoke(
            {
                "request": request,
                "actor": actor,
                "session_id": uuid4(),
                "persona_opinions": [],
                "decision": None,
            }
        )

    assert sorted(invoked_personas) == sorted(PERSONA_IDS)
    decision = result["decision"]
    assert decision is not None
    assert len(decision.persona_opinions) == 3
    assert {opinion.persona for opinion in decision.persona_opinions} == set(PERSONA_IDS)
    CouncilDecision.model_validate(decision)


@pytest.mark.asyncio
async def test_run_council_returns_council_result_response() -> None:
    actor = ActorContext(user_id=uuid4())
    session_id = uuid4()
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
        )

    assert response.response_kind == ResponseKind.COUNCIL_RESULT
    assert response.council_decision is not None
    assert response.council_decision.synthesis == decision.synthesis
    assert len(response.council_decision.persona_opinions) == 3

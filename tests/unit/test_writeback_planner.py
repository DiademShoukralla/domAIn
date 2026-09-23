from uuid import uuid4

from domain.schemas.common import Citation, CouncilDecision, PersonaOpinion, Verdict
from domain.schemas.writeback import WriteBackPlan
from domain.writeback.planner import (
    WriteBackPlanClassification,
    _merge_plan,
    select_existing_doc_path,
)


def _citation(document_id: str) -> Citation:
    return Citation(
        document_id=document_id,
        chunk_index=0,
        knowledge_source_id=uuid4(),
        excerpt="excerpt",
    )


def _council_decision(*document_ids: str) -> CouncilDecision:
    citations = [_citation(document_id) for document_id in document_ids]
    return CouncilDecision(
        persona_opinions=[
            PersonaOpinion(
                persona="ux",
                verdict=Verdict.APPROVE,
                reasoning="Looks good",
                citations=citations,
            )
        ],
        overall_verdict=Verdict.APPROVE,
        synthesis="Approved",
    )


def test_select_existing_doc_path_picks_most_cited() -> None:
    decision = CouncilDecision(
        persona_opinions=[
            PersonaOpinion(
                persona="ux",
                verdict=Verdict.APPROVE,
                reasoning="one",
                citations=[_citation("docs/a.md"), _citation("docs/a.md")],
            ),
            PersonaOpinion(
                persona="dev",
                verdict=Verdict.COMMENT,
                reasoning="two",
                citations=[_citation("docs/b.md")],
            ),
        ],
        overall_verdict=Verdict.APPROVE,
        synthesis="Approved",
    )
    assert select_existing_doc_path(decision) == "docs/a.md"


def test_select_existing_doc_path_returns_none_without_citations() -> None:
    decision = CouncilDecision(
        persona_opinions=[
            PersonaOpinion(
                persona="ux",
                verdict=Verdict.APPROVE,
                reasoning="none",
                citations=[],
            )
        ],
        overall_verdict=Verdict.APPROVE,
        synthesis="Approved",
    )
    assert select_existing_doc_path(decision) is None


def test_merge_plan_uses_existing_doc_from_citations() -> None:
    decision = _council_decision("docs/adr/0002-tech-stack.md")
    classification = WriteBackPlanClassification(
        needs_doc_update=True,
        doc_target="new",
        new_doc_slug="ignored-slug",
        needs_roadmap_item=False,
    )
    plan = _merge_plan(classification, decision)
    assert plan == WriteBackPlan(
        needs_doc_update=True,
        doc_target="existing",
        existing_doc_path="docs/adr/0002-tech-stack.md",
        new_doc_slug=None,
        needs_roadmap_item=False,
    )


def test_merge_plan_falls_back_to_new_doc_slug_without_citations() -> None:
    decision = _council_decision()
    classification = WriteBackPlanClassification(
        needs_doc_update=True,
        doc_target="new",
        new_doc_slug="council-write-back",
        needs_roadmap_item=True,
    )
    plan = _merge_plan(classification, decision)
    assert plan == WriteBackPlan(
        needs_doc_update=True,
        doc_target="new",
        existing_doc_path=None,
        new_doc_slug="council-write-back",
        needs_roadmap_item=True,
    )

from collections import Counter
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from domain.llm.factory import get_supervisor_model
from domain.schemas.common import CouncilDecision
from domain.schemas.writeback import WriteBackPlan

PLANNER_SYSTEM_PROMPT = """You are the domAIn write-back planner. Given a council decision and optional operator feedback, classify what knowledge-layer updates are needed.

Return:
- needs_doc_update: whether business docs, ADRs, or PRD content should be updated
- needs_roadmap_item: whether a Linear roadmap item should be created or updated
- doc_target: "existing" when an indexed doc should be amended, "new" only when no cited doc fits (null when needs_doc_update is false)
- new_doc_slug: kebab-case slug for a new doc (only when doc_target is "new"; null otherwise)

Do not invent file paths. The system selects existing_doc_path from citation frequency separately."""


class WriteBackPlanClassification(BaseModel):
    needs_doc_update: bool = Field(description="Whether indexed docs should be updated.")
    doc_target: Literal["existing", "new"] | None = Field(
        default=None,
        description="Whether to amend an existing doc or create a new one.",
    )
    new_doc_slug: str | None = Field(
        default=None,
        description="Kebab-case slug for a new doc when doc_target is new.",
    )
    needs_roadmap_item: bool = Field(description="Whether a Linear roadmap item is needed.")


def select_existing_doc_path(council_decision: CouncilDecision) -> str | None:
    """Pick the most-cited document_id across persona opinions."""
    counts: Counter[str] = Counter()
    for opinion in council_decision.persona_opinions:
        for citation in opinion.citations:
            counts[citation.document_id] += 1
    if not counts:
        return None
    document_id, _ = counts.most_common(1)[0]
    return document_id


def _merge_plan(
    classification: WriteBackPlanClassification,
    council_decision: CouncilDecision,
) -> WriteBackPlan:
    existing_doc_path: str | None = None
    doc_target: Literal["existing", "new"] | None = None
    new_doc_slug: str | None = None

    if classification.needs_doc_update:
        cited_path = select_existing_doc_path(council_decision)
        if cited_path is not None:
            doc_target = "existing"
            existing_doc_path = cited_path
        else:
            doc_target = "new"
            new_doc_slug = classification.new_doc_slug

    return WriteBackPlan(
        needs_doc_update=classification.needs_doc_update,
        doc_target=doc_target,
        existing_doc_path=existing_doc_path,
        new_doc_slug=new_doc_slug,
        needs_roadmap_item=classification.needs_roadmap_item,
    )


def _format_feedback_block(feedback_history: list[str]) -> str:
    if not feedback_history:
        return ""
    lines = ["Operator feedback history:"]
    for index, feedback in enumerate(feedback_history, start=1):
        lines.append(f"{index}. {feedback}")
    return "\n".join(lines) + "\n\n"


async def classify_write_back_plan(
    council_decision: CouncilDecision,
    feedback_history: list[str] | None = None,
) -> WriteBackPlan:
    feedback_history = feedback_history or []
    model = get_supervisor_model().with_structured_output(WriteBackPlanClassification)
    human_content = (
        f"{_format_feedback_block(feedback_history)}"
        f"Council synthesis: {council_decision.synthesis}\n"
        f"Overall verdict: {council_decision.overall_verdict.value}\n"
        f"Persona opinions:\n"
    )
    for opinion in council_decision.persona_opinions:
        human_content += f"- {opinion.persona} ({opinion.verdict.value}): {opinion.reasoning}\n"

    result = await model.ainvoke(
        [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=human_content),
        ]
    )
    if isinstance(result, WriteBackPlanClassification):
        classification = result
    else:
        classification = WriteBackPlanClassification.model_validate(result)
    return _merge_plan(classification, council_decision)

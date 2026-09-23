from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from domain.council.status import StatusQueue, emit_persona_status
from domain.llm.factory import get_persona_model
from domain.retrieval.service import retrieve
from domain.schemas.common import ActorContext, Citation, PersonaOpinion, ReviewRequest, Verdict
from domain.schemas.retrieval import RetrievedChunk

PERSONA_IDS: tuple[str, ...] = ("ux", "dev_experience", "business")

PERSONA_SYSTEM_PROMPTS: dict[str, str] = {
    "ux": (
        "You are the UX/end-user persona on a decision council. Evaluate proposals from the "
        "perspective of end-user experience, clarity, and usability. Write in first person. "
        "Ground your reasoning in the provided knowledge context when available. Choose a verdict: "
        "approve, request_changes, or comment."
    ),
    "dev_experience": (
        "You are the developer experience persona on a decision council. Evaluate proposals from "
        "the perspective of implementation ergonomics, maintainability, and developer workflow. "
        "Write in first person. Ground your reasoning in the provided knowledge context when "
        "available. Choose a verdict: approve, request_changes, or comment."
    ),
    "business": (
        "You are the business/product persona on a decision council. Evaluate proposals from the "
        "perspective of product value, scope, risk, and roadmap fit. Write in first person. "
        "Ground your reasoning in the provided knowledge context when available. Choose a verdict: "
        "approve, request_changes, or comment."
    ),
}


class PersonaOpinionOutput(BaseModel):
    verdict: Verdict
    reasoning: str


def _build_context(chunks: list[RetrievedChunk]) -> str:
    sections: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        heading = " > ".join(chunk.heading_hierarchy) if chunk.heading_hierarchy else "Untitled"
        sections.append(
            f"[{index}] document_id={chunk.document_id} chunk_index={chunk.chunk_index}\n"
            f"heading: {heading}\n"
            f"{chunk.content}"
        )
    return "\n\n".join(sections)


def _build_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    citations: list[Citation] = []
    for chunk in chunks:
        excerpt = chunk.content[:240] + ("..." if len(chunk.content) > 240 else "")
        citations.append(
            Citation(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                knowledge_source_id=chunk.knowledge_source_id,
                excerpt=excerpt,
            )
        )
    return citations


async def run_persona(
    persona: str,
    request: ReviewRequest,
    actor: ActorContext,
    db: AsyncSession,
    *,
    session_id: UUID,
    status_queue: StatusQueue | None = None,
) -> PersonaOpinion:
    if persona not in PERSONA_SYSTEM_PROMPTS:
        raise ValueError(f"Unknown persona: {persona}")

    await emit_persona_status(status_queue, session_id, persona, "pondering")

    await emit_persona_status(status_queue, session_id, persona, "researching")
    retrieval = await retrieve(
        session=db,
        query=request.query,
        actor_user_id=actor.user_id,
        actor_project_id=actor.project_id,
    )
    context = (
        _build_context(retrieval.chunks) if retrieval.chunks else "No indexed knowledge found."
    )
    citations = _build_citations(retrieval.chunks)

    await emit_persona_status(status_queue, session_id, persona, "giving_recommendation")
    model = get_persona_model().with_structured_output(PersonaOpinionOutput)
    output = await model.ainvoke(
        [
            SystemMessage(content=PERSONA_SYSTEM_PROMPTS[persona]),
            HumanMessage(
                content=(
                    f"Review request:\n{request.query}\n\n"
                    f"Knowledge context:\n{context}\n\n"
                    "Provide your verdict and reasoning:"
                )
            ),
        ]
    )
    if not isinstance(output, PersonaOpinionOutput):
        output = PersonaOpinionOutput.model_validate(output)

    await emit_persona_status(status_queue, session_id, persona, "recommendation_ready")
    return PersonaOpinion(
        persona=persona,
        verdict=output.verdict,
        reasoning=output.reasoning,
        citations=citations,
    )

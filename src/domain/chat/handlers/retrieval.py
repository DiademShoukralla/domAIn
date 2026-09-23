from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from domain.llm.factory import get_retrieval_answer_model
from domain.retrieval.service import retrieve
from domain.schemas.chat import ChatIntent, ChatResponse, ResponseKind
from domain.schemas.common import ActorContext, Citation
from domain.schemas.retrieval import RetrievedChunk

RETRIEVAL_SYSTEM_PROMPT = """You answer questions using only the provided knowledge-layer context.
Be concise and factual. If the context is insufficient, say so clearly.
Do not invent facts that are not supported by the context."""


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


async def handle_simple_retrieval(
    session_id: UUID,
    message: str,
    actor: ActorContext,
    db: AsyncSession,
) -> ChatResponse:
    retrieval = await retrieve(
        session=db,
        query=message,
        actor_user_id=actor.user_id,
        actor_project_id=actor.project_id,
    )

    if not retrieval.chunks:
        content = (
            "I could not find indexed knowledge that answers that question yet. "
            "Try connecting a source or rephrasing the query."
        )
        return ChatResponse(
            session_id=session_id,
            content=content,
            classified_intent=ChatIntent.SIMPLE_RETRIEVAL,
            response_kind=ResponseKind.DIRECT_ANSWER,
        )

    context = _build_context(retrieval.chunks)
    model = get_retrieval_answer_model()
    answer = await model.ainvoke(
        [
            SystemMessage(content=RETRIEVAL_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Question:\n{message}\n\nKnowledge context:\n{context}\n\nAnswer:"
            ),
        ]
    )
    content = answer.content if isinstance(answer.content, str) else str(answer.content)
    citations = _build_citations(retrieval.chunks)

    return ChatResponse(
        session_id=session_id,
        content=content,
        classified_intent=ChatIntent.SIMPLE_RETRIEVAL,
        response_kind=ResponseKind.DIRECT_ANSWER,
        citations=citations,
    )

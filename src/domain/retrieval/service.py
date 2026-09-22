from typing import Any
from uuid import UUID

from sqlalchemy import Row, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.config import get_settings
from domain.db.models import Chunk, KnowledgeSource, SourceStatus
from domain.ingestion.embedder import embed_query
from domain.permissions import can_access
from domain.retrieval.coverage import coverage_check
from domain.retrieval.rrf import RankedResult, reciprocal_rank_fusion
from domain.schemas.retrieval import RetrievalResponse, RetrievedChunk


async def _accessible_source_ids(
    session: AsyncSession,
    actor_user_id: UUID,
    actor_project_id: UUID | None,
) -> list[UUID]:
    result = await session.execute(
        select(KnowledgeSource).where(KnowledgeSource.status == SourceStatus.READY)
    )
    sources = result.scalars().all()
    return [
        source.id
        for source in sources
        if can_access(actor_user_id, actor_project_id, source.user_id, source.project_id)
    ]


async def retrieve(
    session: AsyncSession,
    query: str,
    actor_user_id: UUID,
    actor_project_id: UUID | None = None,
    top_k: int | None = None,
) -> RetrievalResponse:
    settings = get_settings()
    limit = top_k or settings.retrieval_top_k
    source_ids = await _accessible_source_ids(session, actor_user_id, actor_project_id)
    if not source_ids:
        coverage = coverage_check(query, [], settings.coverage_min_score)
        return RetrievalResponse(
            query=query,
            chunks=[],
            coverage_sufficient=coverage.sufficient,
            coverage_score=coverage.score,
            expanded=False,
        )

    query_embedding = await embed_query(query)
    embedding_literal = "[" + ",".join(str(value) for value in query_embedding) + "]"

    vector_sql = text(
        """
        SELECT id, knowledge_source_id, document_id, chunk_index, content, heading_hierarchy
        FROM chunks
        WHERE knowledge_source_id = ANY(:source_ids)
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
        """
    )
    keyword_sql = text(
        """
        SELECT id, knowledge_source_id, document_id, chunk_index, content, heading_hierarchy
        FROM chunks
        WHERE knowledge_source_id = ANY(:source_ids)
          AND content_tsv @@ plainto_tsquery('english', :query)
        ORDER BY ts_rank(content_tsv, plainto_tsquery('english', :query)) DESC
        LIMIT :limit
        """
    )

    vector_result = await session.execute(
        vector_sql,
        {"source_ids": source_ids, "embedding": embedding_literal, "limit": limit},
    )
    keyword_result = await session.execute(
        keyword_sql,
        {"source_ids": source_ids, "query": query, "limit": limit},
    )

    vector_rows = vector_result.fetchall()
    keyword_rows = keyword_result.fetchall()

    vector_ranked = [
        RankedResult(chunk_id=row.id, rank=index + 1) for index, row in enumerate(vector_rows)
    ]
    keyword_ranked = [
        RankedResult(chunk_id=row.id, rank=index + 1) for index, row in enumerate(keyword_rows)
    ]

    def build_row_lookup() -> dict[UUID, Row[Any]]:
        lookup: dict[UUID, Row[Any]] = {row.id: row for row in vector_rows}
        lookup.update({row.id: row for row in keyword_rows})
        return lookup

    fused = reciprocal_rank_fusion([vector_ranked, keyword_ranked], k=settings.rrf_k)
    expanded = False
    row_lookup = build_row_lookup()

    def fused_texts(result_limit: int) -> list[str]:
        return [
            row_lookup[chunk_id].content
            for chunk_id, _, _ in fused[:result_limit]
            if chunk_id in row_lookup
        ]

    coverage = coverage_check(query, fused_texts(limit), settings.coverage_min_score)
    if not coverage.sufficient and limit < 50:
        expanded_limit = min(limit * 2, 50)
        expanded = True
        vector_result = await session.execute(
            vector_sql,
            {"source_ids": source_ids, "embedding": embedding_literal, "limit": expanded_limit},
        )
        keyword_result = await session.execute(
            keyword_sql,
            {"source_ids": source_ids, "query": query, "limit": expanded_limit},
        )
        vector_rows = vector_result.fetchall()
        keyword_rows = keyword_result.fetchall()
        vector_ranked = [
            RankedResult(chunk_id=row.id, rank=index + 1) for index, row in enumerate(vector_rows)
        ]
        keyword_ranked = [
            RankedResult(chunk_id=row.id, rank=index + 1) for index, row in enumerate(keyword_rows)
        ]
        fused = reciprocal_rank_fusion([vector_ranked, keyword_ranked], k=settings.rrf_k)
        row_lookup = build_row_lookup()
        coverage = coverage_check(query, fused_texts(expanded_limit), settings.coverage_min_score)

    chunks: list[RetrievedChunk] = []
    for chunk_id, score, rank_meta in fused[:limit]:
        row = row_lookup.get(chunk_id)
        if row is None:
            chunk = await session.get(Chunk, chunk_id)
            if chunk is None:
                continue
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    knowledge_source_id=chunk.knowledge_source_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    heading_hierarchy=chunk.heading_hierarchy,
                    rrf_score=score,
                    vector_rank=rank_meta.get("vector_rank"),
                    keyword_rank=rank_meta.get("keyword_rank"),
                )
            )
        else:
            chunks.append(
                RetrievedChunk(
                    chunk_id=row.id,
                    knowledge_source_id=row.knowledge_source_id,
                    document_id=row.document_id,
                    chunk_index=row.chunk_index,
                    content=row.content,
                    heading_hierarchy=row.heading_hierarchy,
                    rrf_score=score,
                    vector_rank=rank_meta.get("vector_rank"),
                    keyword_rank=rank_meta.get("keyword_rank"),
                )
            )

    return RetrievalResponse(
        query=query,
        chunks=chunks,
        coverage_sufficient=coverage.sufficient,
        coverage_score=coverage.score,
        expanded=expanded,
    )

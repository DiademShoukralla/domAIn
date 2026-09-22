import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.crypto import decrypt_token
from domain.db.models import Chunk, Connection, KnowledgeSource, SourceStatus, SourceType
from domain.ingestion.adapters.github import fetch_github_repo_documents
from domain.ingestion.adapters.linear import fetch_linear_team_documents
from domain.ingestion.chunking import chunk_text
from domain.ingestion.embedder import embed_documents

logger = logging.getLogger(__name__)


async def index_knowledge_source(session: AsyncSession, source_id: UUID) -> None:
    source = await session.get(KnowledgeSource, source_id)
    if source is None:
        return

    connection = await session.get(Connection, source.connection_id)
    if connection is None:
        source.status = SourceStatus.ERROR
        source.status_message = "Connection not found"
        await session.commit()
        return

    source.status = SourceStatus.INDEXING
    source.status_message = "Indexing in progress"
    await session.commit()

    try:
        access_token = decrypt_token(connection.access_token)
        if source.source_type == SourceType.GITHUB_REPO:
            documents = await fetch_github_repo_documents(access_token, source.external_ref)
        elif source.source_type == SourceType.LINEAR:
            documents = await fetch_linear_team_documents(access_token, source.external_ref)
        else:
            raise ValueError(f"Unsupported source type: {source.source_type}")

        await session.execute(delete(Chunk).where(Chunk.knowledge_source_id == source.id))

        all_chunks: list[tuple[str, int, str, list[str]]] = []
        for document in documents:
            for chunk in chunk_text(document.document_id, document.content):
                all_chunks.append(
                    (chunk.document_id, chunk.chunk_index, chunk.content, chunk.heading_hierarchy)
                )

        if not all_chunks:
            source.status = SourceStatus.READY
            source.status_message = "No indexable content found"
            source.last_indexed_at = datetime.now(tz=UTC)
            await session.commit()
            return

        batch_size = 32
        for start in range(0, len(all_chunks), batch_size):
            batch = all_chunks[start : start + batch_size]
            embeddings = await embed_documents([item[2] for item in batch])
            for (document_id, chunk_index, content, heading_hierarchy), embedding in zip(
                batch, embeddings, strict=True
            ):
                db_chunk = Chunk(
                    knowledge_source_id=source.id,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=content,
                    heading_hierarchy=heading_hierarchy,
                    embedding=embedding,
                )
                session.add(db_chunk)
            await session.flush()

        await session.execute(
            text(
                """
                UPDATE chunks
                SET content_tsv = to_tsvector('english', content)
                WHERE knowledge_source_id = :source_id
                """
            ),
            {"source_id": source.id},
        )

        source.status = SourceStatus.READY
        source.status_message = None
        source.last_indexed_at = datetime.now(tz=UTC)
        await session.commit()
    except Exception as exc:
        logger.exception("Indexing failed for source %s", source_id)
        await session.rollback()
        source = await session.get(KnowledgeSource, source_id)
        if source is not None:
            source.status = SourceStatus.ERROR
            source.status_message = str(exc)
            await session.commit()


async def schedule_index(session: AsyncSession, source_id: UUID) -> None:
    source = await session.get(KnowledgeSource, source_id)
    if source is None:
        return
    source.status = SourceStatus.PENDING
    source.status_message = "Queued for indexing"
    await session.commit()
    await index_knowledge_source(session, source_id)

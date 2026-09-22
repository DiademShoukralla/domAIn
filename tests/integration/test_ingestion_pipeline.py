from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import func, select

from domain.config import get_settings
from domain.crypto import encrypt_token
from domain.db.models import Chunk, Connection, KnowledgeSource, Provider, SourceStatus, SourceType
from domain.ingestion.adapters.types import FetchedDocument
from domain.ingestion.errors import GENERIC_INDEXING_FAILURE_MESSAGE, RECONNECT_WORKSPACE_MESSAGE
from domain.ingestion.pipeline import index_knowledge_source

USER_ID = get_settings().default_user_id
EMBEDDING_DIM = get_settings().embedding_dimensions


@pytest.fixture
def mock_embedding() -> list[float]:
    return [0.1] * EMBEDDING_DIM


@pytest.fixture
async def github_connection(db_session) -> Connection:
    connection = Connection(
        user_id=USER_ID,
        provider=Provider.GITHUB,
        access_token=encrypt_token("github-test-token"),
        refresh_token=None,
        token_expires_at=None,
        external_account_id="12345",
        external_account_name="test-user",
    )
    db_session.add(connection)
    await db_session.commit()
    await db_session.refresh(connection)
    return connection


@pytest.fixture
async def github_source(db_session, github_connection) -> KnowledgeSource:
    source = KnowledgeSource(
        user_id=USER_ID,
        project_id=None,
        source_type=SourceType.GITHUB_REPO,
        external_ref="owner/repo",
        connection_id=github_connection.id,
        name="Test Repo",
        status=SourceStatus.PENDING,
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


@pytest.mark.asyncio
async def test_indexing_pipeline_persists_chunks(db_session, github_source, mock_embedding) -> None:
    documents = [
        FetchedDocument(document_id="README.md", content="# Title\n\nHello from integration test."),
        FetchedDocument(document_id="docs/adr.md", content="## ADR\n\nArchitecture decisions."),
    ]

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [mock_embedding for _ in texts]

    with (
        patch(
            "domain.ingestion.pipeline.fetch_github_repo_documents",
            new=AsyncMock(return_value=documents),
        ),
        patch("domain.ingestion.pipeline.embed_documents", new=AsyncMock(side_effect=fake_embed)),
    ):
        await index_knowledge_source(db_session, github_source.id)

    refreshed = await db_session.get(KnowledgeSource, github_source.id)
    assert refreshed is not None
    assert refreshed.status == SourceStatus.READY
    assert refreshed.status_message is None
    assert refreshed.last_indexed_at is not None

    chunk_count = await db_session.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.knowledge_source_id == github_source.id)
    )
    assert chunk_count and chunk_count > 0

    chunk = await db_session.scalar(
        select(Chunk).where(Chunk.knowledge_source_id == github_source.id).limit(1)
    )
    assert chunk is not None
    assert len(chunk.embedding) == EMBEDDING_DIM
    assert chunk.content_tsv is not None


@pytest.mark.asyncio
async def test_indexing_pipeline_auth_failure_sets_actionable_message(
    db_session, github_source
) -> None:
    request = httpx.Request("GET", "https://api.github.com/repos/owner/repo/git/trees/main")
    response = httpx.Response(401, request=request)
    auth_error = httpx.HTTPStatusError("Unauthorized", request=request, response=response)

    with patch(
        "domain.ingestion.pipeline.fetch_github_repo_documents",
        new=AsyncMock(side_effect=auth_error),
    ):
        await index_knowledge_source(db_session, github_source.id)

    refreshed = await db_session.get(KnowledgeSource, github_source.id)
    assert refreshed is not None
    assert refreshed.status == SourceStatus.ERROR
    assert refreshed.status_message == RECONNECT_WORKSPACE_MESSAGE


@pytest.mark.asyncio
async def test_indexing_pipeline_generic_failure_sets_actionable_message(
    db_session, github_source
) -> None:
    with patch(
        "domain.ingestion.pipeline.fetch_github_repo_documents",
        new=AsyncMock(side_effect=RuntimeError("provider timeout")),
    ):
        await index_knowledge_source(db_session, github_source.id)

    refreshed = await db_session.get(KnowledgeSource, github_source.id)
    assert refreshed is not None
    assert refreshed.status == SourceStatus.ERROR
    assert refreshed.status_message == GENERIC_INDEXING_FAILURE_MESSAGE

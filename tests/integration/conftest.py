import subprocess
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from domain.db.models import APIKey, ChatMessage, Chunk, Connection, KnowledgeSource, WriteBackProposal
from domain.db.session import async_session_factory


@pytest.fixture(scope="session")
def apply_migrations() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


@pytest.fixture
async def db_session(apply_migrations: None) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
        await session.execute(delete(WriteBackProposal))
        await session.execute(delete(ChatMessage))
        await session.execute(delete(Chunk))
        await session.execute(delete(KnowledgeSource))
        await session.execute(delete(Connection))
        await session.execute(delete(APIKey))
        await session.commit()

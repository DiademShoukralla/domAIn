from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from domain.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        echo_pool="debug" if settings.database_echo_pool else False,
        pool_reset_on_return="rollback",
        connect_args={"server_settings": {"application_name": settings.database_application_name}},
    )


@lru_cache
def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


class _AsyncSessionFactoryProxy:
    """Lazy proxy so tests can set DATABASE_* env vars before the first DB use."""

    def __call__(self, *args: Any, **kwargs: Any) -> AsyncSession:
        return get_async_session_factory()(*args, **kwargs)


async_session_factory = _AsyncSessionFactoryProxy()


async def _rollback_if_needed(session: AsyncSession) -> None:
    if session.in_transaction():
        await session.rollback()


@asynccontextmanager
async def managed_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session_factory()() as session:
        try:
            yield session
        finally:
            await _rollback_if_needed(session)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session_factory()() as session:
        try:
            yield session
        finally:
            await _rollback_if_needed(session)


def list_database_session_sources() -> list[dict[str, str]]:
    """Inventory of session entry points (single shared engine + application_name)."""
    settings = get_settings()
    return [
        {
            "name": "domain.db.session.get_engine",
            "kind": "AsyncEngine",
            "application_name": settings.database_application_name,
            "notes": "Singleton via lru_cache; pool_reset_on_return=rollback",
        },
        {
            "name": "domain.db.session.get_async_session_factory",
            "kind": "async_sessionmaker",
            "application_name": settings.database_application_name,
            "notes": "All app/tests sessions use this factory",
        },
        {
            "name": "domain.db.session.get_db",
            "kind": "FastAPI dependency",
            "application_name": settings.database_application_name,
            "notes": "HTTP routes; rolls back open txn in finally",
        },
        {
            "name": "domain.db.session.managed_session",
            "kind": "context manager",
            "application_name": settings.database_application_name,
            "notes": "Short-lived work (auth, persist, retrieval)",
        },
        {
            "name": "domain.council.graph.persona_node",
            "kind": "managed async with factory",
            "application_name": settings.database_application_name,
            "notes": "Per-persona council retrieval; not used when run_council is mocked",
        },
        {
            "name": "LangGraph checkpointer",
            "kind": "none",
            "application_name": "n/a",
            "notes": "Council graph has no SQLAlchemy checkpointer in this repo",
        },
    ]

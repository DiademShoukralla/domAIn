from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from domain.api.routes import chat, connections, health, oauth, retrieval, sources
from domain.auth.api_key import ensure_bootstrap_api_key
from domain.auth.middleware import AuthMiddleware
from domain.db.session import async_session_factory


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with async_session_factory() as session:
        await ensure_bootstrap_api_key(session)
    yield


app = FastAPI(title="domAIn", version="0.1.0", lifespan=lifespan)
app.add_middleware(AuthMiddleware)

app.include_router(health.router)
app.include_router(oauth.router)
app.include_router(connections.router)
app.include_router(sources.router)
app.include_router(retrieval.router)
app.include_router(chat.router)

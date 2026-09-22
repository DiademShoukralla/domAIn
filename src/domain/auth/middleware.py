from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from domain.auth.api_key import validate_api_key
from domain.config import get_settings
from domain.db.session import async_session_factory
from domain.schemas.common import ActorContext

PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/oauth/github/authorize",
    "/oauth/github/callback",
    "/oauth/linear/authorize",
    "/oauth/linear/callback",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if path in PUBLIC_PATHS or path.startswith("/oauth/"):
            request.state.actor = ActorContext(user_id=get_settings().default_user_id)
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(status_code=401, content={"detail": "Missing X-API-Key header"})

        async with async_session_factory() as session:
            identity = await validate_api_key(session, api_key)
        if identity is None:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})

        user_id, project_id = identity
        request.state.actor = ActorContext(user_id=user_id, project_id=project_id)
        return await call_next(request)


def get_actor(request: Request) -> ActorContext:
    actor = getattr(request.state, "actor", None)
    if isinstance(actor, ActorContext):
        return actor
    return ActorContext(user_id=get_settings().default_user_id)

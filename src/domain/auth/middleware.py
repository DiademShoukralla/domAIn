from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from domain.auth.actor import resolve_actor
from domain.config import get_settings
from domain.schemas.common import ActorContext

PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/oauth/github/callback",
    "/oauth/linear/callback",
    "/auth/github/login",
    "/auth/github/callback",
    "/auth/access-denied",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if path in PUBLIC_PATHS:
            request.state.actor = ActorContext(user_id=get_settings().default_user_id)
            return await call_next(request)

        actor = await resolve_actor(request)
        if actor is None:
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

        request.state.actor = actor
        return await call_next(request)


def get_actor(request: Request) -> ActorContext:
    actor = getattr(request.state, "actor", None)
    if isinstance(actor, ActorContext):
        return actor
    return ActorContext(user_id=get_settings().default_user_id)

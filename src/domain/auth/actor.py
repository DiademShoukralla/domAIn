from starlette.requests import HTTPConnection

from domain.auth.api_key import validate_api_key
from domain.auth.browser_session import resolve_actor_from_session_token
from domain.config import get_settings
from domain.db.session import async_session_factory
from domain.schemas.common import ActorContext


async def resolve_actor(connection: HTTPConnection) -> ActorContext | None:
    actor, _via_session = await resolve_websocket_actor(connection)
    return actor


async def resolve_websocket_actor(
    connection: HTTPConnection,
) -> tuple[ActorContext | None, bool]:
    settings = get_settings()
    session_token = connection.cookies.get(settings.session_cookie_name)
    if session_token:
        async with async_session_factory() as session:
            session_actor = await resolve_actor_from_session_token(session, session_token)
        if session_actor is not None:
            return session_actor, True

    api_key = connection.headers.get("X-API-Key")
    if api_key:
        async with async_session_factory() as session:
            identity = await validate_api_key(session, api_key)
        if identity is not None:
            user_id, project_id = identity
            return ActorContext(user_id=user_id, project_id=project_id), False

    return None, False


def websocket_origin_allowed(origin: str | None) -> bool:
    if not origin:
        return False
    normalized = origin.rstrip("/")
    return normalized in get_settings().ws_allowed_origin_set

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from starlette.requests import Request

from domain.auth.actor import resolve_actor, websocket_origin_allowed
from domain.auth.api_key import ensure_bootstrap_api_key
from domain.auth.browser_session import create_browser_session, hash_session_token
from domain.config import get_settings
from domain.db.models import User
from domain.schemas.common import ActorContext


@pytest.mark.asyncio
async def test_resolve_actor_prefers_session_over_api_key(db_session) -> None:
    user = User(github_id=999001, login="session-user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    raw_token, _record = await create_browser_session(db_session, user.id)
    await ensure_bootstrap_api_key(db_session)
    settings = get_settings()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/sources",
        "headers": [
            (b"cookie", f"{settings.session_cookie_name}={raw_token}".encode()),
            (b"x-api-key", settings.bootstrap_api_key.encode()),
        ],
    }

    async def receive():
        return {"type": "http.request", "body": b""}

    request = Request(scope, receive)
    actor = await resolve_actor(request)
    assert actor == ActorContext(user_id=user.id)


@pytest.mark.asyncio
async def test_resolve_actor_treats_expired_session_as_unauthenticated(db_session) -> None:
    from domain.db.models import BrowserSession

    user = User(github_id=999005, login="expired-user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    raw_token = "expired-session-token"
    db_session.add(
        BrowserSession(
            user_id=user.id,
            token_hash=hash_session_token(raw_token),
            expires_at=datetime.now(tz=UTC) - timedelta(minutes=1),
        )
    )
    await db_session.commit()
    settings = get_settings()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/sources",
        "headers": [(b"cookie", f"{settings.session_cookie_name}={raw_token}".encode())],
    }

    async def receive():
        return {"type": "http.request", "body": b""}

    request = Request(scope, receive)
    assert await resolve_actor(request) is None


@pytest.mark.asyncio
async def test_resolve_actor_falls_back_to_api_key(db_session) -> None:
    await ensure_bootstrap_api_key(db_session)
    settings = get_settings()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/sources",
        "headers": [(b"x-api-key", settings.bootstrap_api_key.encode())],
    }

    async def receive():
        return {"type": "http.request", "body": b""}

    request = Request(scope, receive)
    actor = await resolve_actor(request)
    assert actor == ActorContext(user_id=settings.default_user_id)


@pytest.mark.asyncio
async def test_resolve_actor_returns_none_without_credentials() -> None:
    scope = {"type": "http", "method": "GET", "path": "/sources", "headers": []}

    async def receive():
        return {"type": "http.request", "body": b""}

    request = Request(scope, receive)
    assert await resolve_actor(request) is None


def test_websocket_origin_allowlist() -> None:
    with patch("domain.auth.actor.get_settings") as mock_settings:
        mock_settings.return_value.ws_allowed_origin_set = frozenset({"http://test"})
        assert websocket_origin_allowed("http://test") is True
        assert websocket_origin_allowed("http://evil.test") is False

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient

from uuid import UUID

from domain.api.routes import oauth as oauth_routes
from domain.auth import middleware as auth_middleware
from domain.auth.middleware import get_actor
from domain.config import get_settings
from domain.main import app
from domain.oauth.state import verify_oauth_state
from domain.schemas.common import ActorContext


@pytest.mark.asyncio
async def test_github_callback_rejects_forged_state() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/oauth/github/callback",
            params={"installation_id": "12345", "state": "forged-state-token"},
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OAuth state"


@pytest.mark.asyncio
async def test_linear_authorize_redirect_state_verifies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = UUID("00000000-0000-4000-8000-000000000002")
    settings = get_settings()
    patched = settings.model_copy(update={"linear_client_id": "test-linear-client-id"})
    monkeypatch.setattr(oauth_routes, "get_settings", lambda: patched)

    async def _resolve_actor(_connection: object) -> ActorContext:
        return ActorContext(user_id=user_id)

    monkeypatch.setattr(auth_middleware, "resolve_actor", _resolve_actor)

    async def _actor_override() -> ActorContext:
        return ActorContext(user_id=user_id)

    app.dependency_overrides[get_actor] = _actor_override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", follow_redirects=False
        ) as client:
            response = await client.get("/oauth/linear/authorize")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 307
    query = parse_qs(urlparse(response.headers["location"]).query)
    state = query["state"][0]
    assert verify_oauth_state(state) == user_id


@pytest.mark.asyncio
async def test_linear_callback_rejects_forged_state() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/oauth/linear/callback",
            params={"code": "fake-code", "state": "forged-state-token"},
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OAuth state"


@pytest.mark.asyncio
async def test_github_callback_redirects_to_frontend_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import UUID

    from domain.api.routes import oauth as oauth_routes

    user_id = UUID("00000000-0000-4000-8000-000000000001")
    monkeypatch.setattr(oauth_routes, "verify_oauth_state", lambda _state: user_id)

    async def _fetch_installation(_installation_id: str) -> dict[str, object]:
        return {"account": {"id": 1, "login": "test-user"}}

    monkeypatch.setattr(oauth_routes, "fetch_installation", _fetch_installation)

    async def _upsert_github_connection(_db, _user_id, _installation_id, _installation) -> None:
        return None

    monkeypatch.setattr(oauth_routes, "upsert_github_connection", _upsert_github_connection)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as client:
        response = await client.get(
            "/oauth/github/callback",
            params={"installation_id": "12345", "state": "valid-state-token"},
        )

    assert response.status_code == 307
    assert response.headers["location"].endswith(
        "/app/connections?provider=github&status=connected"
    )

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from domain.auth.signing import create_login_oauth_state
from domain.config import get_settings
from domain.main import app


@pytest.mark.asyncio
async def test_github_callback_allowlisted_creates_session_and_cookie(
    db_session, monkeypatch
) -> None:
    monkeypatch.setattr(
        "domain.api.routes.auth.is_github_id_allowed", lambda github_id: github_id == 12345
    )

    state = create_login_oauth_state()
    exchange_mock = AsyncMock(return_value="github-access-token")
    user_mock = AsyncMock(return_value={"id": 12345, "login": "didi"})

    monkeypatch.setattr("domain.api.routes.auth.exchange_github_user_code", exchange_mock)
    monkeypatch.setattr("domain.api.routes.auth.fetch_github_user", user_mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/auth/github/callback",
            params={"code": "test-code", "state": state},
            follow_redirects=False,
        )

    settings = get_settings()
    assert response.status_code == 307
    assert response.headers["location"].endswith("/app/")
    assert settings.session_cookie_name in response.cookies
    exchange_mock.assert_awaited_once_with("test-code")
    user_mock.assert_awaited_once_with("github-access-token")


@pytest.mark.asyncio
async def test_github_callback_not_allowlisted_sets_display_cookie(db_session, monkeypatch) -> None:
    monkeypatch.setattr("domain.api.routes.auth.is_github_id_allowed", lambda _github_id: False)

    state = create_login_oauth_state()
    monkeypatch.setattr(
        "domain.api.routes.auth.exchange_github_user_code",
        AsyncMock(return_value="github-access-token"),
    )
    monkeypatch.setattr(
        "domain.api.routes.auth.fetch_github_user",
        AsyncMock(return_value={"id": 99999, "login": "stranger"}),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/auth/github/callback",
            params={"code": "test-code", "state": state},
            follow_redirects=False,
        )

    settings = get_settings()
    assert response.status_code == 307
    assert response.headers["location"].endswith("/app/not-allowed")
    assert settings.session_cookie_name not in response.cookies
    assert settings.auth_display_cookie_name in response.cookies


def test_github_callback_rejects_bad_state() -> None:
    client = TestClient(app)
    response = client.get(
        "/auth/github/callback",
        params={"code": "test-code", "state": "not-valid"},
    )
    assert response.status_code == 400

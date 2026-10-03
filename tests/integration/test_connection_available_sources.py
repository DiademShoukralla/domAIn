from __future__ import annotations

from collections.abc import AsyncGenerator
from inspect import isawaitable
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from domain.auth.api_key import ensure_bootstrap_api_key
from domain.config import get_settings
from domain.crypto import encrypt_token
from domain.db.models import Connection, KnowledgeSource, Provider, SourceStatus, SourceType
from domain.db.session import get_db
from domain.main import app

USER_ID = get_settings().default_user_id
API_KEY_HEADERS = {"X-API-Key": "test-api-key"}


class _MockHttpxClient:
    def __init__(self, handler: Any) -> None:
        self._handler = handler

    async def __aenter__(self) -> _MockHttpxClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        result = self._handler("GET", url, kwargs)
        if isawaitable(result):
            return await result
        return result

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        result = self._handler("POST", url, kwargs)
        if isawaitable(result):
            return await result
        return result


def _github_repositories_handler(page_responses: dict[int, dict[str, Any]]):
    def handler(method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        assert method == "GET"
        assert url.endswith("/installation/repositories")
        page = kwargs.get("params", {}).get("page", 1)
        request = httpx.Request("GET", url)
        return httpx.Response(200, json=page_responses[page], request=request)

    return handler


@pytest.fixture
async def api_db(db_session):
    await ensure_bootstrap_api_key(db_session)
    await db_session.commit()
    return db_session


@pytest.fixture
async def github_connection(api_db) -> Connection:
    connection = Connection(
        user_id=USER_ID,
        provider=Provider.GITHUB,
        installation_id="installation-123",
        external_account_id="acct",
        external_account_name="github-user",
    )
    api_db.add(connection)
    await api_db.commit()
    await api_db.refresh(connection)
    return connection


@pytest.fixture
async def linear_connection(api_db) -> Connection:
    connection = Connection(
        user_id=USER_ID,
        provider=Provider.LINEAR,
        access_token=encrypt_token("linear-access-token"),
        external_account_id="linear-user",
        external_account_name="Linear User",
    )
    api_db.add(connection)
    await api_db.commit()
    await api_db.refresh(connection)
    return connection


@pytest.mark.asyncio
async def test_github_available_sources_paginates_and_marks_already_added(
    api_db, github_connection
) -> None:
    existing = KnowledgeSource(
        user_id=USER_ID,
        project_id=None,
        source_type=SourceType.GITHUB_REPO,
        external_ref="org/existing",
        connection_id=github_connection.id,
        name="org/existing",
        status=SourceStatus.READY,
    )
    api_db.add(existing)
    await api_db.commit()
    await api_db.refresh(existing)

    page_one_repos = [
        {
            "full_name": f"org/padding-{index}",
            "private": False,
            "updated_at": "2026-01-01T00:00:00Z",
        }
        for index in range(99)
    ]
    page_one_repos.insert(
        0,
        {
            "full_name": "org/existing",
            "private": True,
            "updated_at": "2026-01-01T00:00:00Z",
        },
    )
    page_responses = {
        1: {"total_count": 101, "repositories": page_one_repos},
        2: {
            "total_count": 101,
            "repositories": [
                {
                    "full_name": "org/new",
                    "private": False,
                    "updated_at": "2026-02-01T00:00:00Z",
                }
            ],
        },
    }

    with (
        patch(
            "domain.connections.available_sources.get_installation_access_token",
            new=AsyncMock(return_value="installation-token"),
        ),
        patch(
            "domain.connections.available_sources.httpx.AsyncClient",
            return_value=_MockHttpxClient(_github_repositories_handler(page_responses)),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/connections/{github_connection.id}/available-sources",
                headers=API_KEY_HEADERS,
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "github"
    assert len(payload["items"]) == 101

    by_ref = {item["external_ref"]: item for item in payload["items"]}
    assert by_ref["org/existing"]["already_added"] is True
    assert by_ref["org/existing"]["source_id"] == str(existing.id)
    assert by_ref["org/new"]["already_added"] is False
    assert by_ref["org/new"]["private"] is False


@pytest.mark.asyncio
async def test_linear_available_sources_lists_teams(linear_connection) -> None:
    def handler(method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        assert method == "POST"
        assert url == "https://api.linear.app/graphql"
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "data": {
                    "teams": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {"id": "team-1", "name": "Engineering", "key": "ENG"},
                            {"id": "team-2", "name": "Product", "key": "PRD"},
                        ],
                    }
                }
            },
            request=request,
        )

    with patch(
        "domain.connections.available_sources.httpx.AsyncClient",
        return_value=_MockHttpxClient(handler),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/connections/{linear_connection.id}/available-sources",
                headers=API_KEY_HEADERS,
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "linear"
    assert payload["items"] == [
        {
            "source_type": "linear",
            "external_ref": "team-1",
            "name": "Engineering",
            "private": None,
            "updated_at": None,
            "key": "ENG",
            "already_added": False,
            "source_id": None,
        },
        {
            "source_type": "linear",
            "external_ref": "team-2",
            "name": "Product",
            "private": None,
            "updated_at": None,
            "key": "PRD",
            "already_added": False,
            "source_id": None,
        },
    ]


@pytest.mark.asyncio
async def test_available_sources_returns_404_for_other_users_connection(
    api_db, github_connection
) -> None:
    other_connection = Connection(
        user_id=uuid4(),
        provider=Provider.GITHUB,
        installation_id="installation-999",
        external_account_id="other",
        external_account_name="other-user",
    )
    api_db.add(other_connection)
    await api_db.commit()
    await api_db.refresh(other_connection)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/connections/{other_connection.id}/available-sources",
            headers=API_KEY_HEADERS,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_github_provider_forbidden_maps_to_403(github_connection) -> None:
    def handler(method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        request = httpx.Request(method, url)
        return httpx.Response(403, request=request)

    with (
        patch(
            "domain.connections.available_sources.get_installation_access_token",
            new=AsyncMock(return_value="installation-token"),
        ),
        patch(
            "domain.connections.available_sources.httpx.AsyncClient",
            return_value=_MockHttpxClient(handler),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/connections/{github_connection.id}/available-sources",
                headers=API_KEY_HEADERS,
            )

    assert response.status_code == 403
    assert "Reconnect GitHub" in response.json()["detail"]


@pytest.mark.asyncio
async def test_github_provider_rate_limit_maps_to_429(github_connection) -> None:
    def handler(method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        request = httpx.Request(method, url)
        return httpx.Response(429, request=request)

    with (
        patch(
            "domain.connections.available_sources.get_installation_access_token",
            new=AsyncMock(return_value="installation-token"),
        ),
        patch(
            "domain.connections.available_sources.httpx.AsyncClient",
            return_value=_MockHttpxClient(handler),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/connections/{github_connection.id}/available-sources",
                headers=API_KEY_HEADERS,
            )

    assert response.status_code == 429
    assert response.json()["detail"] == "Provider rate limit exceeded. Try again shortly."


@pytest.mark.asyncio
async def test_github_token_exchange_404_maps_to_403(github_connection) -> None:
    request = httpx.Request(
        "POST",
        "https://api.github.com/app/installations/installation-123/access_tokens",
    )
    response = httpx.Response(404, request=request)
    token_error = httpx.HTTPStatusError("Not Found", request=request, response=response)

    with patch(
        "domain.connections.available_sources.get_installation_access_token",
        new=AsyncMock(side_effect=token_error),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            http_response = await client.get(
                f"/connections/{github_connection.id}/available-sources",
                headers=API_KEY_HEADERS,
            )

    assert http_response.status_code == 403
    assert "Reconnect GitHub" in http_response.json()["detail"]


@pytest.mark.asyncio
async def test_github_provider_timeout_maps_to_502(github_connection) -> None:
    async def handler(method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    with (
        patch(
            "domain.connections.available_sources.get_installation_access_token",
            new=AsyncMock(return_value="installation-token"),
        ),
        patch(
            "domain.connections.available_sources.httpx.AsyncClient",
            return_value=_MockHttpxClient(handler),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/connections/{github_connection.id}/available-sources",
                headers=API_KEY_HEADERS,
            )

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to fetch available sources from the provider."


@pytest.mark.asyncio
async def test_linear_provider_timeout_maps_to_502(linear_connection) -> None:
    async def handler(method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with patch(
        "domain.connections.available_sources.httpx.AsyncClient",
        return_value=_MockHttpxClient(handler),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/connections/{linear_connection.id}/available-sources",
                headers=API_KEY_HEADERS,
            )

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to fetch available sources from the provider."


@pytest.mark.asyncio
async def test_linear_graphql_auth_error_maps_to_403(linear_connection) -> None:
    def handler(method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "errors": [
                    {
                        "message": "Authentication required",
                        "extensions": {"code": "AUTHENTICATION_ERROR"},
                    }
                ]
            },
            request=request,
        )

    with patch(
        "domain.connections.available_sources.httpx.AsyncClient",
        return_value=_MockHttpxClient(handler),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/connections/{linear_connection.id}/available-sources",
                headers=API_KEY_HEADERS,
            )

    assert response.status_code == 403
    assert "Reconnect Linear" in response.json()["detail"]


@pytest.mark.asyncio
async def test_linear_graphql_other_error_maps_to_502(linear_connection) -> None:
    def handler(method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "errors": [
                    {
                        "message": "Invalid query",
                        "extensions": {"code": "GRAPHQL_VALIDATION_FAILED"},
                    }
                ]
            },
            request=request,
        )

    with patch(
        "domain.connections.available_sources.httpx.AsyncClient",
        return_value=_MockHttpxClient(handler),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/connections/{linear_connection.id}/available-sources",
                headers=API_KEY_HEADERS,
            )

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to fetch available sources from the provider."


@pytest.mark.asyncio
async def test_github_provider_http_runs_without_open_db_transaction(
    api_db, github_connection
) -> None:
    transaction_open_during_http: list[bool] = []

    def handler(method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        transaction_open_during_http.append(api_db.in_transaction())
        request = httpx.Request(method, url)
        return httpx.Response(
            200,
            json={"repositories": [{"full_name": "org/repo", "private": False}]},
            request=request,
        )

    async def override_get_db() -> AsyncGenerator[Any, None]:
        yield api_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with (
            patch(
                "domain.connections.available_sources.get_installation_access_token",
                new=AsyncMock(return_value="installation-token"),
            ),
            patch(
                "domain.connections.available_sources.httpx.AsyncClient",
                return_value=_MockHttpxClient(handler),
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/connections/{github_connection.id}/available-sources",
                    headers=API_KEY_HEADERS,
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert transaction_open_during_http == [False]

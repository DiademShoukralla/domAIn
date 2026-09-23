import pytest
from httpx import ASGITransport, AsyncClient

from domain.main import app


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
async def test_linear_callback_rejects_forged_state() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/oauth/linear/callback",
            params={"code": "fake-code", "state": "forged-state-token"},
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OAuth state"

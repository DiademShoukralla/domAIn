from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from domain.oauth import github_app


def _generate_test_private_key_base64() -> str:
    import base64

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(pem).decode("utf-8")


@pytest.mark.asyncio
async def test_get_installation_access_token_uses_cache() -> None:
    github_app._token_cache.clear()
    expires_at = datetime.now(tz=UTC) + timedelta(hours=1)

    with patch(
        "domain.oauth.github_app.create_installation_access_token",
        new=AsyncMock(return_value=("cached-token", expires_at)),
    ) as create_mock:
        first = await github_app.get_installation_access_token("999")
        second = await github_app.get_installation_access_token("999")

    assert first == "cached-token"
    assert second == "cached-token"
    create_mock.assert_awaited_once()


def test_create_app_jwt_uses_app_id() -> None:
    private_key_base64 = _generate_test_private_key_base64()
    with patch(
        "domain.oauth.github_app.get_settings",
        return_value=type(
            "Settings",
            (),
            {
                "github_app_id": "123456",
                "github_app_private_key_base64": private_key_base64,
            },
        )(),
    ):
        token = github_app.create_app_jwt()

    assert isinstance(token, str)
    assert token.count(".") == 2

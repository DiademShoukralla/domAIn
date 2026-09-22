from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.config import get_settings
from domain.crypto import decrypt_token, encrypt_token
from domain.db.models import Connection, Provider


def get_github_oauth_client(state: str | None = None) -> AsyncOAuth2Client:
    settings = get_settings()
    return AsyncOAuth2Client(
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        redirect_uri=settings.github_redirect_uri,
        scope=settings.github_scopes,
        state=state,
    )


def github_authorize_url(state: str) -> str:
    client = get_github_oauth_client(state=state)
    uri, _ = client.create_authorization_url("https://github.com/login/oauth/authorize")
    return cast(str, uri)


async def github_exchange_code(code: str, state: str | None = None) -> dict[str, Any]:
    client = get_github_oauth_client(state=state)
    token = await client.fetch_token(
        "https://github.com/login/oauth/access_token",
        code=code,
    )
    return cast(dict[str, Any], token)


async def github_fetch_user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload


async def upsert_github_connection(
    session: AsyncSession, user_id: UUID, token: dict[str, Any], user_info: dict[str, Any]
) -> Connection:
    access_token = token["access_token"]
    refresh_token = token.get("refresh_token")
    expires_at = None
    if token.get("expires_at"):
        expires_at = datetime.fromtimestamp(token["expires_at"], tz=UTC)

    result = await session.execute(
        select(Connection).where(Connection.user_id == user_id, Connection.provider == Provider.GITHUB)
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        connection = Connection(
            user_id=user_id,
            provider=Provider.GITHUB,
            access_token=encrypt_token(access_token),
            refresh_token=encrypt_token(refresh_token) if refresh_token else None,
            token_expires_at=expires_at,
            external_account_id=str(user_info["id"]),
            external_account_name=user_info.get("login") or user_info.get("name") or "github-user",
        )
        session.add(connection)
    else:
        connection.access_token = encrypt_token(access_token)
        connection.refresh_token = encrypt_token(refresh_token) if refresh_token else connection.refresh_token
        connection.token_expires_at = expires_at
        connection.external_account_id = str(user_info["id"])
        connection.external_account_name = user_info.get("login") or user_info.get("name") or "github-user"

    await session.commit()
    await session.refresh(connection)
    return connection


async def get_github_access_token(session: AsyncSession, connection: Connection) -> str:
    return decrypt_token(connection.access_token)

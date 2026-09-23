from typing import Any, cast
from uuid import UUID

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.config import get_settings
from domain.crypto import decrypt_token, encrypt_token
from domain.db.models import Connection, Provider


def get_linear_oauth_client(state: str | None = None) -> AsyncOAuth2Client:
    settings = get_settings()
    return AsyncOAuth2Client(
        client_id=settings.linear_client_id,
        client_secret=settings.linear_client_secret,
        redirect_uri=settings.linear_redirect_uri,
        scope=settings.linear_scopes,
        state=state,
    )


def linear_authorize_url(state: str) -> str:
    client = get_linear_oauth_client(state=state)
    uri, _ = client.create_authorization_url("https://linear.app/oauth/authorize")
    return cast(str, uri)


async def linear_exchange_code(code: str, state: str | None = None) -> dict[str, Any]:
    client = get_linear_oauth_client(state=state)
    token = await client.fetch_token(
        "https://api.linear.app/oauth/token",
        code=code,
    )
    return cast(dict[str, Any], token)


async def linear_fetch_user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"query": "query { viewer { id name email } }"},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        viewer: dict[str, Any] = data["data"]["viewer"]
        return viewer


async def upsert_linear_connection(
    session: AsyncSession, user_id: UUID, token: dict[str, Any], user_info: dict[str, Any]
) -> Connection:
    access_token = token["access_token"]
    refresh_token = token.get("refresh_token")
    # Linear tokens are long-lived; leave token_expires_at unset unless we can compute it.
    expires_at = None

    result = await session.execute(
        select(Connection).where(Connection.user_id == user_id, Connection.provider == Provider.LINEAR)
    )
    connection = result.scalar_one_or_none()
    display_name = user_info.get("name") or user_info.get("email") or "linear-user"
    if connection is None:
        connection = Connection(
            user_id=user_id,
            provider=Provider.LINEAR,
            access_token=encrypt_token(access_token),
            refresh_token=encrypt_token(refresh_token) if refresh_token else None,
            token_expires_at=expires_at,
            external_account_id=user_info["id"],
            external_account_name=display_name,
        )
        session.add(connection)
    else:
        connection.access_token = encrypt_token(access_token)
        connection.refresh_token = encrypt_token(refresh_token) if refresh_token else connection.refresh_token
        connection.token_expires_at = expires_at
        connection.external_account_id = user_info["id"]
        connection.external_account_name = display_name

    await session.commit()
    await session.refresh(connection)
    return connection


async def get_linear_access_token(session: AsyncSession, connection: Connection) -> str:
    if not connection.access_token:
        raise RuntimeError("Linear connection is missing access_token")
    return decrypt_token(connection.access_token)

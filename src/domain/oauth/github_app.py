import base64
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.config import get_settings
from domain.db.models import Connection, Provider

GITHUB_API_BASE = "https://api.github.com"


@dataclass
class _CachedInstallationToken:
    token: str
    expires_at: datetime


_token_cache: dict[str, _CachedInstallationToken] = {}


def _load_private_key_pem() -> str:
    settings = get_settings()
    if not settings.github_app_private_key_base64:
        raise RuntimeError("GITHUB_APP_PRIVATE_KEY_BASE64 is not configured")
    return base64.b64decode(settings.github_app_private_key_base64).decode("utf-8")


def create_app_jwt() -> str:
    settings = get_settings()
    if not settings.github_app_id:
        raise RuntimeError("GITHUB_APP_ID is not configured")

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, _load_private_key_pem(), algorithm="RS256")


def github_install_url(state: str) -> str:
    settings = get_settings()
    if not settings.github_app_slug:
        raise RuntimeError("GITHUB_APP_SLUG is not configured")
    return f"https://github.com/apps/{settings.github_app_slug}/installations/new?state={state}"


async def fetch_installation(installation_id: str) -> dict[str, Any]:
    app_jwt = create_app_jwt()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())


async def create_installation_access_token(installation_id: str) -> tuple[str, datetime]:
    app_jwt = create_app_jwt()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        payload = cast(dict[str, Any], response.json())
        expires_at = datetime.fromisoformat(str(payload["expires_at"]).replace("Z", "+00:00"))
        return str(payload["token"]), expires_at


async def get_installation_access_token(installation_id: str) -> str:
    cached = _token_cache.get(installation_id)
    now = datetime.now(tz=UTC)
    if cached is not None and cached.expires_at > now + timedelta(minutes=1):
        return cached.token

    token, expires_at = await create_installation_access_token(installation_id)
    _token_cache[installation_id] = _CachedInstallationToken(token=token, expires_at=expires_at)
    return token


def _account_fields(installation: dict[str, Any]) -> tuple[str, str]:
    account = cast(dict[str, Any], installation["account"])
    account_id = str(account["id"])
    account_name = str(account.get("login") or account.get("name") or "github-account")
    return account_id, account_name


async def upsert_github_connection(
    session: AsyncSession,
    user_id: UUID,
    installation_id: str,
    installation: dict[str, Any],
) -> Connection:
    external_account_id, external_account_name = _account_fields(installation)

    result = await session.execute(
        select(Connection).where(
            Connection.user_id == user_id, Connection.provider == Provider.GITHUB
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        connection = Connection(
            user_id=user_id,
            provider=Provider.GITHUB,
            access_token=None,
            refresh_token=None,
            token_expires_at=None,
            installation_id=installation_id,
            external_account_id=external_account_id,
            external_account_name=external_account_name,
        )
        session.add(connection)
    else:
        connection.access_token = None
        connection.refresh_token = None
        connection.token_expires_at = None
        connection.installation_id = installation_id
        connection.external_account_id = external_account_id
        connection.external_account_name = external_account_name

    await session.commit()
    await session.refresh(connection)
    return connection

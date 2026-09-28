from typing import Any, cast

import httpx

from domain.config import get_settings

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def github_user_authorize_url(state: str) -> str:
    settings = get_settings()
    if not settings.github_app_oauth_client_id:
        raise RuntimeError("GITHUB_APP_OAUTH_CLIENT_ID is not configured")
    redirect_uri = settings.github_auth_redirect_uri
    client_id = settings.github_app_oauth_client_id
    return (
        f"{GITHUB_AUTHORIZE_URL}?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&scope=read:user"
        f"&state={state}"
    )


async def exchange_github_user_code(code: str) -> str:
    settings = get_settings()
    if not settings.github_app_oauth_client_secret:
        raise RuntimeError("GITHUB_APP_OAUTH_CLIENT_SECRET is not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_app_oauth_client_id,
                "client_secret": settings.github_app_oauth_client_secret,
                "code": code,
                "redirect_uri": settings.github_auth_redirect_uri,
            },
        )
        response.raise_for_status()
        payload = cast(dict[str, Any], response.json())
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError("GitHub token exchange did not return an access token")
        return access_token


async def fetch_github_user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.middleware import get_actor
from domain.config import get_settings
from domain.db.session import get_db
from domain.oauth.github_app import (
    fetch_installation,
    github_install_url,
    upsert_github_connection,
)
from domain.oauth.linear import (
    linear_authorize_url,
    linear_exchange_code,
    linear_fetch_user,
    upsert_linear_connection,
)
from domain.oauth.state import OAuthStateError, create_oauth_state, verify_oauth_state
from domain.schemas.common import ActorContext

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/github/authorize")
async def github_authorize(actor: ActorContext = Depends(get_actor)) -> RedirectResponse:
    settings = get_settings()
    if (
        not settings.github_app_id
        or not settings.github_app_slug
        or not settings.github_app_private_key_base64
    ):
        raise HTTPException(status_code=503, detail="GitHub App is not configured")
    state = create_oauth_state(actor.user_id)
    return RedirectResponse(github_install_url(state))


@router.get("/github/callback")
async def github_callback(
    installation_id: str = Query(...),
    state: str = Query(...),
    _setup_action: str | None = Query(default=None, alias="setup_action"),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        user_id = verify_oauth_state(state)
    except OAuthStateError:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from None

    installation = await fetch_installation(installation_id)
    await upsert_github_connection(db, user_id, installation_id, installation)
    return RedirectResponse(
        url=f"{get_settings().app_base_url}/app/connections?provider=github&status=connected"
    )


@router.get("/linear/authorize")
async def linear_authorize(actor: ActorContext = Depends(get_actor)) -> RedirectResponse:
    settings = get_settings()
    if not settings.linear_client_id:
        raise HTTPException(status_code=503, detail="Linear OAuth is not configured")
    state = create_oauth_state(actor.user_id)
    return RedirectResponse(linear_authorize_url(state))


@router.get("/linear/callback")
async def linear_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        user_id = verify_oauth_state(state)
    except OAuthStateError:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from None

    token = await linear_exchange_code(code, state=state)
    user_info = await linear_fetch_user(token["access_token"])
    await upsert_linear_connection(db, user_id, token, user_info)
    return RedirectResponse(
        url=f"{get_settings().app_base_url}/app/connections?provider=linear&status=connected"
    )

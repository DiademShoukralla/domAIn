import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.middleware import get_actor
from domain.config import get_settings
from domain.db.session import get_db
from domain.oauth.github import (
    github_authorize_url,
    github_exchange_code,
    github_fetch_user,
    upsert_github_connection,
)
from domain.oauth.linear import (
    linear_authorize_url,
    linear_exchange_code,
    linear_fetch_user,
    upsert_linear_connection,
)
from domain.schemas.common import ActorContext

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/github/authorize")
async def github_authorize(actor: ActorContext = Depends(get_actor)) -> RedirectResponse:
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    state = secrets.token_urlsafe(16)
    # v1 single-user: state encodes user id for callback
    state = f"{actor.user_id}:{state}"
    return RedirectResponse(github_authorize_url(state))


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    user_id_str = state.split(":", 1)[0]
    token = await github_exchange_code(code, state=state)
    user_info = await github_fetch_user(token["access_token"])
    from uuid import UUID

    await upsert_github_connection(db, UUID(user_id_str), token, user_info)
    return RedirectResponse(url=f"{get_settings().app_base_url}/connections?provider=github&status=connected")


@router.get("/linear/authorize")
async def linear_authorize(actor: ActorContext = Depends(get_actor)) -> RedirectResponse:
    settings = get_settings()
    if not settings.linear_client_id:
        raise HTTPException(status_code=503, detail="Linear OAuth is not configured")
    state = secrets.token_urlsafe(16)
    state = f"{actor.user_id}:{state}"
    return RedirectResponse(linear_authorize_url(state))


@router.get("/linear/callback")
async def linear_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    user_id_str = state.split(":", 1)[0]
    token = await linear_exchange_code(code, state=state)
    user_info = await linear_fetch_user(token["access_token"])
    from uuid import UUID

    await upsert_linear_connection(db, UUID(user_id_str), token, user_info)
    return RedirectResponse(url=f"{get_settings().app_base_url}/connections?provider=linear&status=connected")

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from domain.auth.actor import resolve_actor
from domain.auth.allowlist import is_github_id_allowed
from domain.auth.browser_session import (
    create_browser_session,
    get_or_create_user,
    revoke_browser_session,
    session_cookie_secure,
    session_max_age_seconds,
)
from domain.auth.signing import (
    SignedValueError,
    create_auth_display_value,
    create_login_oauth_state,
    verify_auth_display_value,
    verify_login_oauth_state,
)
from domain.config import get_settings
from domain.db.models import User
from domain.db.session import async_session_factory
from domain.oauth.github_user import (
    exchange_github_user_code,
    fetch_github_user,
    github_user_authorize_url,
)

router = APIRouter(prefix="/auth", tags=["auth"])

AUTH_DISPLAY_MAX_AGE_SECONDS = 300


def _set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
        path="/",
        max_age=session_max_age_seconds(),
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _set_auth_display_cookie(response: Response, login: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_display_cookie_name,
        value=create_auth_display_value(login, ttl_seconds=AUTH_DISPLAY_MAX_AGE_SECONDS),
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
        path="/",
        max_age=AUTH_DISPLAY_MAX_AGE_SECONDS,
    )


def _clear_auth_display_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_display_cookie_name,
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
        path="/",
    )


@router.get("/github/login")
async def github_login() -> RedirectResponse:
    settings = get_settings()
    if not settings.github_app_oauth_client_id or not settings.github_app_oauth_client_secret:
        raise HTTPException(status_code=503, detail="GitHub login is not configured")
    state = create_login_oauth_state()
    return RedirectResponse(github_user_authorize_url(state))


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    settings = get_settings()
    app_url = settings.app_base_url.rstrip("/")

    try:
        verify_login_oauth_state(state)
    except SignedValueError:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from None

    access_token = await exchange_github_user_code(code)
    user_payload = await fetch_github_user(access_token)
    github_id = int(user_payload["id"])
    login = str(user_payload["login"])

    if not is_github_id_allowed(github_id):
        response = RedirectResponse(url=f"{app_url}/app/not-allowed")
        _set_auth_display_cookie(response, login)
        return response

    async with async_session_factory() as session:
        user = await get_or_create_user(session, github_id=github_id, login=login)
        raw_token, _record = await create_browser_session(session, user.id)

    response = RedirectResponse(url=f"{app_url}/app/")
    _set_session_cookie(response, raw_token)
    _clear_auth_display_cookie(response)
    return response


@router.get("/access-denied")
async def access_denied(request: Request) -> dict[str, str]:
    settings = get_settings()
    signed = request.cookies.get(settings.auth_display_cookie_name)
    if not signed:
        raise HTTPException(status_code=404, detail="No pending access request")
    try:
        login = verify_auth_display_value(signed)
    except SignedValueError:
        raise HTTPException(status_code=404, detail="No pending access request") from None
    return {"login": login}


@router.get("/me")
async def auth_me(request: Request) -> dict[str, str | int]:
    actor = await resolve_actor(request)
    if actor is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == actor.user_id))
        user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"login": user.login, "github_id": user.github_id}


@router.post("/logout")
async def logout(request: Request) -> Response:
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token:
        async with async_session_factory() as session:
            await revoke_browser_session(session, raw_token)

    response = Response(status_code=204)
    _clear_session_cookie(response)
    return response

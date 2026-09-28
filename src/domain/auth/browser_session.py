import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.config import get_settings
from domain.db.models import BrowserSession, User
from domain.schemas.common import ActorContext


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def session_cookie_secure() -> bool:
    return get_settings().app_env != "development"


def session_max_age_seconds() -> int:
    return get_settings().session_ttl_days * 24 * 60 * 60


async def get_or_create_user(session: AsyncSession, github_id: int, login: str) -> User:
    result = await session.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(github_id=github_id, login=login)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    if user.login != login:
        user.login = login
        await session.commit()
        await session.refresh(user)
    return user


async def create_browser_session(
    session: AsyncSession, user_id: UUID
) -> tuple[str, BrowserSession]:
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(tz=UTC) + timedelta(days=settings.session_ttl_days)
    record = BrowserSession(
        user_id=user_id,
        token_hash=hash_session_token(raw_token),
        expires_at=expires_at,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return raw_token, record


async def resolve_actor_from_session_token(
    session: AsyncSession, raw_token: str
) -> ActorContext | None:
    token_hash = hash_session_token(raw_token)
    result = await session.execute(
        select(BrowserSession).where(BrowserSession.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None

    now = datetime.now(tz=UTC)
    if record.revoked_at is not None or record.expires_at <= now:
        return None

    return ActorContext(user_id=record.user_id)


async def revoke_browser_session(session: AsyncSession, raw_token: str) -> None:
    token_hash = hash_session_token(raw_token)
    result = await session.execute(
        select(BrowserSession).where(BrowserSession.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return
    if record.revoked_at is None:
        record.revoked_at = datetime.now(tz=UTC)
        await session.commit()

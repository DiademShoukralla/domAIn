import hashlib
import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.config import get_settings
from domain.db.models import APIKey


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def ensure_bootstrap_api_key(session: AsyncSession) -> None:
    settings = get_settings()
    key_hash = hash_api_key(settings.bootstrap_api_key)
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    if result.scalar_one_or_none() is None:
        session.add(
            APIKey(
                key_hash=key_hash,
                user_id=settings.default_user_id,
                project_id=None,
            )
        )
        await session.commit()


async def validate_api_key(session: AsyncSession, api_key: str) -> tuple[UUID, UUID | None] | None:
    key_hash = hash_api_key(api_key)
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    record = result.scalar_one_or_none()
    if record is None:
        return None
    if record.user_id is None:
        return get_settings().default_user_id, record.project_id
    return record.user_id, record.project_id


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

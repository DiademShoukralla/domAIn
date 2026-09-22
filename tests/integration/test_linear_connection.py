import pytest

from domain.config import get_settings
from domain.db.models import Connection
from domain.oauth.linear import upsert_linear_connection

USER_ID = get_settings().default_user_id


@pytest.mark.asyncio
async def test_linear_connection_leaves_token_expires_at_unset(db_session) -> None:
    token = {"access_token": "linear-access-token", "expires_in": 3600}
    user_info = {"id": "linear-user-id", "name": "Linear User"}

    connection = await upsert_linear_connection(db_session, USER_ID, token, user_info)
    assert connection.token_expires_at is None

    refreshed = await db_session.get(Connection, connection.id)
    assert refreshed is not None
    assert refreshed.token_expires_at is None

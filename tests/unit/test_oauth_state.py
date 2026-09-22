import time
from uuid import UUID

import pytest

from domain.oauth.state import OAuthStateError, create_oauth_state, verify_oauth_state

USER_ID = UUID("00000000-0000-4000-8000-000000000001")


def test_create_and_verify_oauth_state() -> None:
    state = create_oauth_state(USER_ID)
    assert verify_oauth_state(state) == USER_ID


def test_verify_rejects_tampered_state() -> None:
    state = create_oauth_state(USER_ID)
    tampered = state[:-4] + "XXXX"
    with pytest.raises(OAuthStateError):
        verify_oauth_state(tampered)


def test_verify_rejects_forged_state() -> None:
    with pytest.raises(OAuthStateError):
        verify_oauth_state("not-a-valid-state-token")


def test_verify_rejects_expired_state(monkeypatch: pytest.MonkeyPatch) -> None:
    state = create_oauth_state(USER_ID, ttl_seconds=1)
    real_time = time.time

    def advanced_time() -> float:
        return real_time() + 120

    monkeypatch.setattr(time, "time", advanced_time)
    with pytest.raises(OAuthStateError):
        verify_oauth_state(state)

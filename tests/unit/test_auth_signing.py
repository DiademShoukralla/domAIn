import pytest

from domain.auth.signing import (
    SignedValueError,
    create_auth_display_value,
    create_login_oauth_state,
    verify_auth_display_value,
    verify_login_oauth_state,
)


def test_login_oauth_state_round_trip() -> None:
    state = create_login_oauth_state()
    verify_login_oauth_state(state)


def test_auth_display_value_round_trip() -> None:
    signed = create_auth_display_value("octocat")
    assert verify_auth_display_value(signed) == "octocat"


def test_tampered_signed_value_rejected() -> None:
    signed = create_auth_display_value("octocat")
    payload = verify_auth_display_value(signed)
    assert payload == "octocat"
    with pytest.raises(SignedValueError):
        verify_auth_display_value("not-a-valid-token")

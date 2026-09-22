from uuid import UUID

from domain.permissions import can_access

USER_A = UUID("00000000-0000-4000-8000-000000000001")
USER_B = UUID("00000000-0000-4000-8000-000000000002")
PROJECT_A = UUID("10000000-0000-4000-8000-000000000001")
PROJECT_B = UUID("10000000-0000-4000-8000-000000000002")


def test_global_resource_accessible_to_any_user() -> None:
    assert can_access(USER_A, None, None, None)
    assert can_access(USER_B, PROJECT_A, None, None)


def test_user_mismatch_denied() -> None:
    assert not can_access(USER_A, None, USER_B, None)


def test_project_mismatch_denied() -> None:
    assert not can_access(USER_A, PROJECT_A, USER_A, PROJECT_B)


def test_matching_user_and_project_allowed() -> None:
    assert can_access(USER_A, PROJECT_A, USER_A, PROJECT_A)

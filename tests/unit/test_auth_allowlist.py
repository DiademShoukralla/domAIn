from unittest.mock import patch

from domain.auth.allowlist import is_github_id_allowed


def test_allowlist_check_uses_numeric_github_id() -> None:
    with patch("domain.auth.allowlist.get_settings") as mock_settings:
        mock_settings.return_value.allowed_github_ids = frozenset({42, 100})
        assert is_github_id_allowed(42) is True
        assert is_github_id_allowed(100) is True
        assert is_github_id_allowed(99) is False

import os

import pytest

os.environ.setdefault(
    "TOKEN_ENCRYPTION_KEY",
    "J1DKacOrXJ8dI6ByJL5wpw73UYWIjwpaQX6BFzxuBIw=",
)
os.environ.setdefault("BOOTSTRAP_API_KEY", "test-api-key")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://domain:domain@localhost:5432/domain",
)
os.environ.setdefault("DATABASE_APPLICATION_NAME", "domain-pytest")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Enable pool checkout logging for disconnect leak integration tests."""
    for item in items:
        if "test_chat_websocket_disconnect" in item.nodeid:
            import os

            os.environ["DATABASE_ECHO_POOL"] = "1"
            break

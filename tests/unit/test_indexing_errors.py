import httpx

from domain.ingestion.errors import (
    GENERIC_INDEXING_FAILURE_MESSAGE,
    RECONNECT_WORKSPACE_MESSAGE,
    indexing_error_message,
)


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.example.com/resource")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


def test_auth_errors_map_to_reconnect_message() -> None:
    assert indexing_error_message(_http_error(401)) == RECONNECT_WORKSPACE_MESSAGE
    assert indexing_error_message(_http_error(403)) == RECONNECT_WORKSPACE_MESSAGE


def test_generic_errors_map_to_retry_message() -> None:
    assert indexing_error_message(RuntimeError("boom")) == GENERIC_INDEXING_FAILURE_MESSAGE
    assert indexing_error_message(_http_error(500)) == GENERIC_INDEXING_FAILURE_MESSAGE

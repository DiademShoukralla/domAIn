import httpx

RECONNECT_WORKSPACE_MESSAGE = "Reconnect the workspace to resume indexing."
GENERIC_INDEXING_FAILURE_MESSAGE = "Indexing failed. Try refreshing the source."


def indexing_error_message(exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (401, 403):
        return RECONNECT_WORKSPACE_MESSAGE
    return GENERIC_INDEXING_FAILURE_MESSAGE

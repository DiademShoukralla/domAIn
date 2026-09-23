from functools import lru_cache
from typing import Any, cast

import voyageai

from domain.config import get_settings


@lru_cache
def _get_client() -> Any:
    settings = get_settings()
    if not settings.voyage_api_key:
        raise RuntimeError("VOYAGE_API_KEY is not configured")
    client_kwargs: dict[str, str] = {"api_key": settings.voyage_api_key}
    if settings.voyage_base_url:
        client_kwargs["base_url"] = settings.voyage_base_url
    client_cls = getattr(voyageai, "Client")
    return cast(Any, client_cls(**client_kwargs))


async def embed_documents(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    if not texts:
        return []
    client = _get_client()
    result = client.embed(
        texts,
        model=settings.voyage_model,
        input_type="document",
    )
    return cast(list[list[float]], result.embeddings)


async def embed_query(text: str) -> list[float]:
    settings = get_settings()
    client = _get_client()
    result = client.embed(
        [text],
        model=settings.voyage_model,
        input_type="query",
    )
    return cast(list[float], result.embeddings[0])

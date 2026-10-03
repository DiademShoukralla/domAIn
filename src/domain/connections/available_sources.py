from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.db.models import KnowledgeSource, SourceType
from domain.oauth.github_app import GITHUB_API_BASE, get_installation_access_token
from domain.permissions import can_access
from domain.schemas.available_sources import AvailableSourceItem
from domain.schemas.common import ActorContext

GITHUB_REPOS_PER_PAGE = 100
LINEAR_TEAMS_PAGE_SIZE = 50

GITHUB_ACCESS_LOST_DETAIL = (
    "GitHub installation access was revoked or is no longer available. Reconnect GitHub."
)
LINEAR_ACCESS_LOST_DETAIL = "Linear access was revoked or is no longer available. Reconnect Linear."
PROVIDER_RATE_LIMIT_DETAIL = "Provider rate limit exceeded. Try again shortly."
PROVIDER_ERROR_DETAIL = "Failed to fetch available sources from the provider."


class ProviderRequestError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


LINEAR_AUTH_GRAPHQL_CODES = frozenset(
    {
        "AUTHENTICATION_ERROR",
        "FORBIDDEN",
        "JWT_EXPIRED",
        "INVALID_SCOPE",
        "UNAUTHENTICATED",
    }
)


def map_github_token_exchange_http_status(status_code: int) -> ProviderRequestError:
    if status_code in (401, 403, 404):
        return ProviderRequestError(403, GITHUB_ACCESS_LOST_DETAIL)
    if status_code == 429:
        return ProviderRequestError(429, PROVIDER_RATE_LIMIT_DETAIL)
    return ProviderRequestError(502, PROVIDER_ERROR_DETAIL)


def map_github_resource_http_status(status_code: int) -> ProviderRequestError:
    if status_code in (401, 403):
        return ProviderRequestError(403, GITHUB_ACCESS_LOST_DETAIL)
    if status_code == 429:
        return ProviderRequestError(429, PROVIDER_RATE_LIMIT_DETAIL)
    return ProviderRequestError(502, PROVIDER_ERROR_DETAIL)


def map_linear_http_status(status_code: int) -> ProviderRequestError:
    if status_code in (401, 403):
        return ProviderRequestError(403, LINEAR_ACCESS_LOST_DETAIL)
    if status_code == 429:
        return ProviderRequestError(429, PROVIDER_RATE_LIMIT_DETAIL)
    return ProviderRequestError(502, PROVIDER_ERROR_DETAIL)


def map_linear_graphql_errors(errors: list[dict[str, Any]]) -> ProviderRequestError:
    for error in errors:
        extensions = cast(dict[str, Any], error.get("extensions") or {})
        code = str(extensions.get("code", "")).upper()
        if code in LINEAR_AUTH_GRAPHQL_CODES:
            return ProviderRequestError(403, LINEAR_ACCESS_LOST_DETAIL)
    return ProviderRequestError(502, PROVIDER_ERROR_DETAIL)


def _parse_github_updated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def github_repo_payload_to_item(repo: dict[str, Any]) -> AvailableSourceItem:
    full_name = str(repo["full_name"])
    return AvailableSourceItem(
        source_type=SourceType.GITHUB_REPO,
        external_ref=full_name,
        name=full_name,
        private=bool(repo.get("private")),
        updated_at=_parse_github_updated_at(repo.get("updated_at")),
    )


def linear_team_payload_to_item(team: dict[str, Any]) -> AvailableSourceItem:
    return AvailableSourceItem(
        source_type=SourceType.LINEAR,
        external_ref=str(team["id"]),
        name=str(team["name"]),
        key=str(team["key"]) if team.get("key") is not None else None,
    )


def mark_already_added(
    items: list[AvailableSourceItem],
    existing: dict[tuple[SourceType, str], UUID],
) -> list[AvailableSourceItem]:
    marked: list[AvailableSourceItem] = []
    for item in items:
        source_id = existing.get((item.source_type, item.external_ref))
        if source_id is None:
            marked.append(item)
            continue
        marked.append(
            item.model_copy(update={"already_added": True, "source_id": source_id}),
        )
    return marked


def merge_github_repository_pages(pages: list[list[dict[str, Any]]]) -> list[AvailableSourceItem]:
    items: list[AvailableSourceItem] = []
    for page in pages:
        for repo in page:
            items.append(github_repo_payload_to_item(repo))
    return items


async def load_existing_sources_by_ref(
    db: AsyncSession,
    connection_id: UUID,
    actor: ActorContext,
) -> dict[tuple[SourceType, str], UUID]:
    result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.connection_id == connection_id)
    )
    existing: dict[tuple[SourceType, str], UUID] = {}
    for source in result.scalars().all():
        if can_access(actor.user_id, actor.project_id, source.user_id, source.project_id):
            existing[(source.source_type, source.external_ref)] = source.id
    return existing


async def fetch_github_installation_repositories(installation_id: str) -> list[AvailableSourceItem]:
    try:
        access_token = await get_installation_access_token(installation_id)
    except httpx.HTTPStatusError as exc:
        raise map_github_token_exchange_http_status(exc.response.status_code) from exc
    except httpx.RequestError as exc:
        raise ProviderRequestError(502, PROVIDER_ERROR_DETAIL) from exc
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    pages: list[list[dict[str, Any]]] = []
    page = 1

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                response = await client.get(
                    f"{GITHUB_API_BASE}/installation/repositories",
                    headers=headers,
                    params={"per_page": GITHUB_REPOS_PER_PAGE, "page": page},
                )
                if response.status_code >= 400:
                    raise map_github_resource_http_status(response.status_code)
                payload = cast(dict[str, Any], response.json())
                batch = cast(list[dict[str, Any]], payload.get("repositories", []))
                pages.append(batch)
                if len(batch) < GITHUB_REPOS_PER_PAGE:
                    break
                page += 1
    except httpx.RequestError as exc:
        raise ProviderRequestError(502, PROVIDER_ERROR_DETAIL) from exc

    return merge_github_repository_pages(pages)


async def fetch_linear_teams(access_token: str) -> list[AvailableSourceItem]:
    query = """
    query Teams($after: String, $first: Int!) {
      teams(first: $first, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes { id name key }
      }
    }
    """
    items: list[AvailableSourceItem] = []
    after: str | None = None

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                response = await client.post(
                    "https://api.linear.app/graphql",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "query": query,
                        "variables": {"after": after, "first": LINEAR_TEAMS_PAGE_SIZE},
                    },
                )
                if response.status_code >= 400:
                    raise map_linear_http_status(response.status_code)

                payload = cast(dict[str, Any], response.json())
                errors = cast(list[dict[str, Any]], payload.get("errors") or [])
                if errors:
                    raise map_linear_graphql_errors(errors)

                data = payload.get("data")
                if data is None:
                    raise ProviderRequestError(502, PROVIDER_ERROR_DETAIL)

                teams_data = data.get("teams")
                if teams_data is None:
                    raise ProviderRequestError(502, PROVIDER_ERROR_DETAIL)

                for team in cast(list[dict[str, Any]], teams_data.get("nodes", [])):
                    items.append(linear_team_payload_to_item(team))

                page_info = cast(dict[str, Any], teams_data.get("pageInfo") or {})
                if not page_info.get("hasNextPage"):
                    break
                after = cast(str | None, page_info.get("endCursor"))
    except httpx.RequestError as exc:
        raise ProviderRequestError(502, PROVIDER_ERROR_DETAIL) from exc

    return items

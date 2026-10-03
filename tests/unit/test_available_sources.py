from datetime import UTC, datetime
from uuid import uuid4

from domain.connections.available_sources import (
    GITHUB_ACCESS_LOST_DETAIL,
    LINEAR_ACCESS_LOST_DETAIL,
    PROVIDER_ERROR_DETAIL,
    map_github_resource_http_status,
    map_github_token_exchange_http_status,
    map_linear_graphql_errors,
    mark_already_added,
    merge_github_repository_pages,
)
from domain.db.models import SourceType
from domain.schemas.available_sources import AvailableSourceItem


def test_mark_already_added_sets_source_id() -> None:
    source_id = uuid4()
    items = [
        AvailableSourceItem(
            source_type=SourceType.GITHUB_REPO,
            external_ref="owner/added",
            name="owner/added",
        ),
        AvailableSourceItem(
            source_type=SourceType.GITHUB_REPO,
            external_ref="owner/new",
            name="owner/new",
        ),
    ]
    existing = {(SourceType.GITHUB_REPO, "owner/added"): source_id}

    marked = mark_already_added(items, existing)

    assert marked[0].already_added is True
    assert marked[0].source_id == source_id
    assert marked[1].already_added is False
    assert marked[1].source_id is None


def test_merge_github_repository_pages_across_multiple_pages() -> None:
    pages = [
        [
            {
                "full_name": "org/repo-one",
                "private": True,
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ],
        [
            {
                "full_name": "org/repo-two",
                "private": False,
                "updated_at": "2026-02-01T12:30:00Z",
            }
        ],
    ]

    items = merge_github_repository_pages(pages)

    assert len(items) == 2
    assert items[0].external_ref == "org/repo-one"
    assert items[0].private is True
    assert items[0].updated_at == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert items[1].external_ref == "org/repo-two"
    assert items[1].name == "org/repo-two"


def test_map_github_token_exchange_http_status_maps_404_to_403() -> None:
    error = map_github_token_exchange_http_status(404)
    assert error.status_code == 403
    assert error.detail == GITHUB_ACCESS_LOST_DETAIL


def test_map_github_resource_http_status_maps_404_to_502() -> None:
    error = map_github_resource_http_status(404)
    assert error.status_code == 502
    assert error.detail == PROVIDER_ERROR_DETAIL


def test_map_linear_graphql_errors_maps_auth_codes_to_403() -> None:
    error = map_linear_graphql_errors(
        [{"message": "not allowed", "extensions": {"code": "FORBIDDEN"}}]
    )
    assert error.status_code == 403
    assert error.detail == LINEAR_ACCESS_LOST_DETAIL


def test_map_linear_graphql_errors_maps_other_codes_to_502() -> None:
    error = map_linear_graphql_errors(
        [{"message": "bad input", "extensions": {"code": "INPUT_ERROR"}}]
    )
    assert error.status_code == 502
    assert error.detail == PROVIDER_ERROR_DETAIL

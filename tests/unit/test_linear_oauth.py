from urllib.parse import parse_qs, urlparse

from domain.oauth.linear import linear_authorize_url


def test_linear_authorize_url_includes_actor_app() -> None:
    url = linear_authorize_url("test-state-token")
    query = parse_qs(urlparse(url).query)
    assert query["actor"] == ["app"]

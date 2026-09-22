from domain.retrieval.coverage import coverage_check


def test_coverage_sufficient_when_terms_present() -> None:
    result = coverage_check(
        "permissions model access control",
        ["The permissions model uses can_access for authorization."],
        min_score=0.3,
    )
    assert result.sufficient
    assert result.score > 0.3


def test_coverage_insufficient_when_terms_missing() -> None:
    result = coverage_check(
        "kubernetes deployment terraform",
        ["Simple chunking strategy for markdown documents."],
        min_score=0.5,
    )
    assert not result.sufficient

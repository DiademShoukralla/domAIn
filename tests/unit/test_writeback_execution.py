from datetime import UTC, datetime

from domain.schemas.common import CouncilDecision, PersonaOpinion, Verdict
from domain.writeback.service import (
    _build_existing_doc_append,
    _build_new_doc_content,
    _new_doc_path,
)


def _sample_decision() -> CouncilDecision:
    return CouncilDecision(
        persona_opinions=[
            PersonaOpinion(
                persona="ux",
                verdict=Verdict.REQUEST_CHANGES,
                reasoning="Needs clearer acceptance criteria",
                citations=[],
            ),
            PersonaOpinion(
                persona="devx",
                verdict=Verdict.COMMENT,
                reasoning="Consider API ergonomics",
                citations=[],
            ),
            PersonaOpinion(
                persona="business",
                verdict=Verdict.APPROVE,
                reasoning="Aligns with roadmap goals",
                citations=[],
            ),
        ],
        overall_verdict=Verdict.REQUEST_CHANGES,
        synthesis="Request changes to clarify scope",
    )


def test_build_new_doc_content_includes_query_personas_and_synthesis() -> None:
    executed_at = datetime(2026, 9, 23, tzinfo=UTC)
    content = _build_new_doc_content(
        slug="council-scope",
        query="Should we ship feature X?",
        council_decision=_sample_decision(),
        executed_at=executed_at,
    )

    assert "# Council decision: council-scope" in content
    assert "Should we ship feature X?" in content
    assert "request_changes" in content
    assert "Needs clearer acceptance criteria" in content
    assert "Consider API ergonomics" in content
    assert "Aligns with roadmap goals" in content
    assert "Request changes to clarify scope" in content


def test_build_existing_doc_append_adds_dated_section_and_changelog() -> None:
    executed_at = datetime(2026, 9, 23, tzinfo=UTC)
    existing = "# Existing doc\n\nSome content.\n"
    updated = _build_existing_doc_append(
        existing,
        query="Should we ship feature X?",
        council_decision=_sample_decision(),
        executed_at=executed_at,
    )

    assert "## Council write-back (2026-09-23)" in updated
    assert "Date: 2026-09-23" in updated
    assert "## Changelog" in updated
    assert "| 2026-09-23 | Council write-back for query" in updated
    assert "Some content." in updated


def test_build_existing_doc_append_appends_changelog_row_when_table_exists() -> None:
    executed_at = datetime(2026, 9, 23, tzinfo=UTC)
    existing = (
        "# ADR\n\n"
        "## Changelog\n\n"
        "| Date | Change |\n"
        "|------|--------|\n"
        "| 2026-09-22 | Initial decision |\n"
    )
    updated = _build_existing_doc_append(
        existing,
        query="Roadmap question",
        council_decision=_sample_decision(),
        executed_at=executed_at,
    )

    assert "| 2026-09-22 | Initial decision |" in updated
    assert "| 2026-09-23 | Council write-back for query" in updated


def test_new_doc_path_is_dated_and_slugged() -> None:
    executed_at = datetime(2026, 9, 23, tzinfo=UTC)
    assert (
        _new_doc_path("Council Scope", executed_at)
        == "docs/business/council-decisions/2026-09-23-council-scope.md"
    )

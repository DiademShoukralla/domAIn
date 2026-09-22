import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CoverageResult:
    sufficient: bool
    score: float


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[a-zA-Z0-9_]+", text) if len(token) > 2}


def coverage_check(query: str, chunk_texts: list[str], min_score: float = 0.3) -> CoverageResult:
    """Lightweight coverage heuristic: fraction of query terms present across top chunks."""
    query_terms = _tokenize(query)
    if not query_terms:
        return CoverageResult(sufficient=True, score=1.0)
    if not chunk_texts:
        return CoverageResult(sufficient=False, score=0.0)

    covered_terms: set[str] = set()
    for text in chunk_texts:
        covered_terms |= _tokenize(text) & query_terms

    score = len(covered_terms) / len(query_terms)
    return CoverageResult(sufficient=score >= min_score, score=score)

from uuid import UUID

from domain.retrieval.rrf import RankedResult, reciprocal_rank_fusion


def test_rrf_merges_ranked_lists() -> None:
    chunk_a = UUID("00000000-0000-4000-8000-000000000010")
    chunk_b = UUID("00000000-0000-4000-8000-000000000011")
    chunk_c = UUID("00000000-0000-4000-8000-000000000012")

    vector = [RankedResult(chunk_id=chunk_a, rank=1), RankedResult(chunk_id=chunk_b, rank=2)]
    keyword = [RankedResult(chunk_id=chunk_b, rank=1), RankedResult(chunk_id=chunk_c, rank=2)]

    merged = reciprocal_rank_fusion([vector, keyword], k=60)
    ids = [item[0] for item in merged]

    assert ids[0] == chunk_b
    assert set(ids) == {chunk_a, chunk_b, chunk_c}

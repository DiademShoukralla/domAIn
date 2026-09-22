from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RankedResult:
    chunk_id: UUID
    rank: int


def reciprocal_rank_fusion(
    result_lists: list[list[RankedResult]],
    k: int = 60,
) -> list[tuple[UUID, float, dict[str, int | None]]]:
    """Merge ranked result lists with RRF. Returns (chunk_id, score, rank_metadata)."""
    scores: dict[UUID, float] = defaultdict(float)
    ranks: dict[UUID, dict[str, int | None]] = defaultdict(
        lambda: {"vector_rank": None, "keyword_rank": None}
    )

    list_names = ["vector", "keyword"]
    for list_index, results in enumerate(result_lists):
        name = list_names[list_index] if list_index < len(list_names) else f"list_{list_index}"
        for item in results:
            scores[item.chunk_id] += 1.0 / (k + item.rank)
            ranks[item.chunk_id][f"{name}_rank"] = item.rank

    merged = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return [(chunk_id, score, ranks[chunk_id]) for chunk_id, score in merged]

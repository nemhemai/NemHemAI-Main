# app/retrieval/fusion.py

from typing import List, Tuple
from app.retrieval.filters import RRF_K

# ──────────────────────────────────────────────────────────────────────────────
# RRF FUSION
# ──────────────────────────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    lists:  list[list[str]],
    k:      int = RRF_K,
) -> list[tuple[str, float]]:
    """
    Merge multiple ranked lists via Reciprocal Rank Fusion.

    Args:
        lists: Each sub-list is a ranked list of chunk_ids (best first).
        k:     RRF constant (default 60 per the original paper).

    Returns:
        List of (chunk_id, rrf_score) sorted by score descending.
    """
    scores: dict[str, float] = {}

    for ranked_list in lists:
        for rank, chunk_id in enumerate(ranked_list, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

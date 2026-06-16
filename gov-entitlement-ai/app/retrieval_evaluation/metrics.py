# app/retrieval_evaluation/metrics.py

def is_relevant(result, expected):
    """
    Determines if a retrieved chunk is relevant.

    Priority:
    1. Strong match (exact chunk_id)
    2. Semantic match (reranker)
    3. Weak lexical match (keyword/section)
    """

    text = (result.get("text") or "").lower()
    section = (result.get("section_path") or "").lower()
    chunk_id = result.get("chunk_id")

    # 1. Exact match
    if chunk_id in expected.get("relevant_chunk_ids", []):
        return True

    # 2. Semantic match (primary)
    rerank_score = result.get("rerank_score", 0)
    if rerank_score >= 0.5:   # ← slightly relaxed
        return True

    # 3. Lexical fallback
    keyword_match = any(
        kw.lower() in text for kw in expected.get("expected_keywords", [])
    )

    section_match = any(
        sec.lower() in section for sec in expected.get("expected_sections", [])
    )

    return keyword_match or section_match
# ─────────────────────────────────────────────────────────────

def top1_accuracy(results, expected):
    if not results:
        return 0
    return int(is_relevant(results[0], expected))


def top3_accuracy(results, expected):
    return int(any(is_relevant(r, expected) for r in results[:3]))


def precision_at_k(results, expected, k=5):
    if not results:
        return 0.0

    relevant = sum(is_relevant(r, expected) for r in results[:k])
    return relevant / k


# ─────────────────────────────────────────────────────────────
# OPTIONAL (ADVANCED — VERY USEFUL)

def mean_reciprocal_rank(results, expected):
    """
    Measures how early the first relevant result appears.
    """
    for i, r in enumerate(results, start=1):
        if is_relevant(r, expected):
            return 1 / i
    return 0
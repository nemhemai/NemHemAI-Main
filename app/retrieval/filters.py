# app/retrieval/filters.py

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

RRF_K              = 60     # RRF constant — larger K = less aggressive rank fusion
DENSE_CANDIDATES   = 50     # pgvector top-N before fusion
SPARSE_CANDIDATES  = 50     # FTS top-N before fusion
RERANK_CANDIDATES  = 15     # RRF top-N sent to ColBERT reranker
DEFAULT_TOP_K      = 10     # final results returned to caller
MIN_QUALITY_FILTER = 0.50   # skip chunks below this quality at retrieval time

def apply_default_filters(filters: dict | None) -> dict:
    filters = filters or {}
    if "min_quality" not in filters:
        filters["min_quality"] = MIN_QUALITY_FILTER
    return filters
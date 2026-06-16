# app/retrieval/hybrid_search.py

"""
retriever.py — Government Knowledge Infrastructure | Hybrid Retrieval
────────────────────────────────────────────────────────────────────────────────

POSITION IN PIPELINE:
  document_embeddings (DB)  ←─┐
  document_chunks (DB)      ←─┤─  [THIS FILE]  ←  user query
  (FTS via tsvector)        ←─┘

PURPOSE:
  Given a user query, retrieve the most relevant chunks using hybrid search,
  then rerank for precision.

RETRIEVAL STRATEGY — FOUR STAGES:
  1. Dense search    → cosine similarity via pgvector    → top-50 candidates
  2. Sparse search   → FTS (tsvector) + sparse dot prod  → top-50 candidates
  3. RRF fusion      → merge both lists via Reciprocal Rank Fusion → top-20
  4. ColBERT rerank  → BGE-M3 late interaction on top-20 → final top-k

WHY HYBRID:
  Dense alone misses: "Section 4.13", "100 kg/day", exact clause numbers
  Sparse alone misses: "solid waste producer" ≠ "generator" (semantic miss)
  Together they cover both failure modes with no extra models needed.

WHY RRF:
  Dense scores (cosine, 0-1) and sparse scores (BM25, 0-∞) are on different
  scales. Normalising them is fragile. RRF uses only rank position, which is
  scale-invariant. Standard constant k=60 works well empirically.

WHY COLBERT RERANK:
  After fusion, the top-20 are good candidates but not perfectly ordered.
  ColBERT late interaction compares query tokens against passage tokens
  at fine granularity — significantly better than cosine on short clauses.
  Costs ~0.1-0.5s for 20 candidates, acceptable at query time.

RETRIEVAL RESULT SCHEMA:
  Each result dict contains:
    chunk_id, document_id, text, text_raw, table_markdown,
    section_path, breadcrumb, chunk_heading, element_ids, page_range,
    is_table, chunk_type, token_count, detected_language,
    min_quality_score, avg_quality_score,
    dense_score, sparse_score, rrf_score, final_score
"""

from __future__ import annotations

import logging
from typing import Any
from app.retrieval.filters import DEFAULT_TOP_K, MIN_QUALITY_FILTER, DENSE_CANDIDATES, SPARSE_CANDIDATES, RRF_K, RERANK_CANDIDATES
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.hybrid_search import dense_search
from app.retrieval.hydration import hydrate_chunks
from app.retrieval.sparse import sparse_search

import numpy as np

from embedding import ChunkEmbedder, sparse_dot_product

logger = logging.getLogger(__name__)



# ──────────────────────────────────────────────────────────────────────────────
# MAIN RETRIEVER CLASS
# ──────────────────────────────────────────────────────────────────────────────

class HybridRetriever:
    """
    Hybrid retriever for government document RAG.

    Usage:
        retriever = HybridRetriever()
        results = retriever.retrieve(
            conn,
            query      = "What is the penalty for not segregating waste?",
            top_k      = 5,
            document_id = 42,        # optional: restrict to one document
        )

        for r in results:
            print(r["text_raw"])
            print(f"Section: {r['section_path']}  Score: {r['final_score']:.3f}")
    """

    def __init__(self, embedder: ChunkEmbedder | None = None):
        # Reuse an existing embedder if passed (avoids reloading the model)
        self._embedder = embedder or ChunkEmbedder()

    # ── Main retrieval entry point ─────────────────────────────────────────────

    def retrieve(
        self,
        conn:        Any,
        query:       str,
        top_k:       int  = DEFAULT_TOP_K,
        document_id: int | None = None,
        filters:     dict | None = None,
        use_rerank:  bool = True,
    ) -> list[dict]:
        """
        Full hybrid retrieval pipeline: dense + sparse → RRF → rerank.

        Args:
            conn:        psycopg2 database connection.
            query:       User's natural language question.
            top_k:       Number of final results to return.
            document_id: If set, search only within this document.
                         If None, searches across all documents.
            filters:     Optional dict to narrow search:
                           - is_table (bool)       → table-only or text-only
                           - min_quality (float)   → quality floor (default 0.50)
                           - language (str)        → 'en', 'hi', 'mr'
                           - section_path (str)    → prefix match on section
            use_rerank:  If True, apply ColBERT reranking on top-20 RRF results.
                         Set False for faster retrieval at slight accuracy cost.

        Returns:
            List of result dicts, each containing chunk fields + score fields:
              dense_score, sparse_score, rrf_score, final_score
        """
        if not query or not query.strip():
            return []

        filters = filters or {}
        if "min_quality" not in filters:
            filters["min_quality"] = MIN_QUALITY_FILTER

        # ── Step 1: Embed the query ────────────────────────────────────────────
        query_dense, query_sparse = self._embedder.embed_query(query)

        # ── Step 2: Dense search ───────────────────────────────────────────────
        dense_results = dense_search(
            conn, query_dense,
            top_n=DENSE_CANDIDATES,
            document_id=document_id,
            filters=filters,
        )
        dense_scores:  dict[str, float] = {r["chunk_id"]: r["dense_score"] for r in dense_results}
        dense_ranked:  list[str]        = [r["chunk_id"] for r in dense_results]

        logger.debug(f"Dense search: {len(dense_results)} candidates")

        # ── Step 3: Sparse search ──────────────────────────────────────────────
        sparse_results = sparse_search(
            conn, query, query_sparse,
            top_n=SPARSE_CANDIDATES,
            document_id=document_id,
            filters=filters,
        )
        sparse_scores: dict[str, float] = {
            r["chunk_id"]: r.get("sparse_score", r.get("fts_score", 0.0))
            for r in sparse_results
        }
        sparse_ranked: list[str] = [r["chunk_id"] for r in sparse_results]

        logger.debug(f"Sparse search: {len(sparse_results)} candidates")

        # ── Step 4: RRF fusion ─────────────────────────────────────────────────
        rrf_ranked = reciprocal_rank_fusion([dense_ranked, sparse_ranked], k=RRF_K)
        rrf_scores: dict[str, float] = {chunk_id: score for chunk_id, score in rrf_ranked}

        # Take top RERANK_CANDIDATES for reranking
        top_ids = [cid for cid, _ in rrf_ranked[:RERANK_CANDIDATES]]

        logger.debug(f"RRF fusion: {len(rrf_ranked)} unique candidates, top-{RERANK_CANDIDATES} to rerank")

        # ── Step 5: Hydrate chunk records ──────────────────────────────────────
        all_known: dict[str, dict] = {}
        for r in dense_results + sparse_results:
            all_known[r["chunk_id"]] = r

        chunk_map = hydrate_chunks(conn, [cid for cid in top_ids if cid not in all_known])
        all_known.update(chunk_map)

        # ── Step 6: ColBERT reranking ──────────────────────────────────────────
        top_chunks = [all_known[cid] for cid in top_ids if cid in all_known]
        rerank_scores: dict[str, float] = {}

        if use_rerank and top_chunks:
            texts_for_rerank = [c["text"] for c in top_chunks]

            ranked_pairs = self._embedder.rerank(
                query, texts_for_rerank, top_k=len(top_chunks)
            )

            for orig_idx, score in ranked_pairs:
                if orig_idx < len(top_chunks):
                    cid = top_chunks[orig_idx]["chunk_id"]
                    rerank_scores[cid] = score

        # ── Step 7: Assemble final results ─────────────────────────────────────
        results: list[dict] = []

        for chunk in top_chunks:
            cid = chunk["chunk_id"]

            result = dict(chunk)
            result.pop("sparse_vector", None)   # don't return raw sparse to caller

            result["dense_score"]  = round(dense_scores.get(cid, 0.0), 4)
            result["sparse_score"] = round(sparse_scores.get(cid, 0.0), 4)
            result["rrf_score"]    = round(rrf_scores.get(cid, 0.0), 6)
            result["final_score"]  = round(rerank_scores.get(cid, rrf_scores.get(cid, 0.0)), 4)

            results.append(result)

        # Sort by final score
        results.sort(key=lambda x: x["final_score"], reverse=True)

        final = results[:top_k]

        logger.info(
            f"Retrieval complete: query='{query[:60]}' → "
            f"{len(final)} results (doc={document_id}, rerank={use_rerank})"
        )

        return final

    # ── Convenience: retrieve with section filter ──────────────────────────────

    def retrieve_from_section(
        self,
        conn:        Any,
        query:       str,
        section_path: str,
        top_k:       int = DEFAULT_TOP_K,
        document_id: int | None = None,
    ) -> list[dict]:
        """
        Retrieves only from chunks whose section_path starts with the given prefix.
        Useful for focused queries like "what are the penalties in Chapter VII?"
        """
        return self.retrieve(
            conn, query, top_k=top_k,
            document_id=document_id,
            filters={"section_path": section_path},
        )

    # ── Convenience: table-only retrieval ─────────────────────────────────────

    def retrieve_tables(
        self,
        conn:        Any,
        query:       str,
        top_k:       int = DEFAULT_TOP_K,
        document_id: int | None = None,
    ) -> list[dict]:
        """
        Retrieves only table chunks.
        Useful for queries expecting structured data (quantities, schedules, penalties).
        """
        return self.retrieve(
            conn, query, top_k=top_k,
            document_id=document_id,
            filters={"is_table": True},
            use_rerank=False,   # tables are usually self-explanatory, skip rerank
        )


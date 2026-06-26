# app/retrieval/retriever.py

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
import re
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from app.core.database import get_db_conn, release_db_conn

from app.retrieval.query_expansion import expand_query
from app.retrieval.document_router import route_documents, get_doc_type

# NOTE: numpy not required here anymore (used in dense module), but kept if future use
import numpy as np

from app.embedding.embedding_engine import  EmbeddingEngine as ChunkEmbedder
from app.retrieval.query_expansion import detect_query_type
from app.memory.redis_cache import retrieval_cache

# ──────────────────────────────────────────────────────────────────────────────
# MODULAR IMPORTS (UPDATED FOR NEW ARCHITECTURE)
# ──────────────────────────────────────────────────────────────────────────────

from app.retrieval.dense import dense_search
from app.retrieval.sparse import sparse_search
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.hydration import hydrate_chunks
from app.retrieval.reranker import rerank_chunks
from app.retrieval.filters import (
    apply_default_filters,
    DENSE_CANDIDATES,
    SPARSE_CANDIDATES,
    RERANK_CANDIDATES,
    DEFAULT_TOP_K,
    RRF_K,
)

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
        sparse_only: bool = False,
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
            sparse_only: If True, skip dense embedding/search and colbert completely. Extremely fast.

        Returns:
            List of result dicts, each containing chunk fields + score fields:
              dense_score, sparse_score, rrf_score, final_score
        """
        if not query or not query.strip():
            return []

        # UPDATED: centralised filter handling
        filters = apply_default_filters(filters)
        
        # ── Step 0: Detect query intent ────────────────────────────────────────
        query_type = detect_query_type(query)
        
        # ── Step 0.5: Check Retrieval Cache ────────────────────────────────────
        # Only use cache for global searches (no specific document filtering)
        # and standard queries.
        if document_id is None and not sparse_only:
            cached_chunks = retrieval_cache.get(query, query_type)
            if cached_chunks:
                logger.info(f"Retrieval Cache HIT for query: '{query}'")
                # Apply top_k cut
                return cached_chunks[:top_k]
        
        expanded_query = expand_query(query, query_type)
        print("Original Query:", query)
        print("Expanded Query:", expanded_query)
        
        # 🔥 DOCUMENT ROUTING
        target_doc_types = route_documents(query, query_type)

        # ── Step 1: Embed the query ────────────────────────────────────────────
        if not sparse_only:
            query_dense, query_sparse = self._embedder.embed_query(query)
        else:
            query_dense, query_sparse = None, {}
        
        # ── Step 2 & 3: Concurrent Dense & Sparse Search ────────────────────────
        dense_results = []
        sparse_results = []

        def run_dense():
            if sparse_only:
                return []
            local_conn = get_db_conn()
            try:
                return dense_search(
                    local_conn, query_dense,
                    top_n=DENSE_CANDIDATES,
                    document_id=document_id,
                    filters=filters,
                )
            finally:
                release_db_conn(local_conn)

        def run_sparse():
            local_conn = get_db_conn()
            try:
                return sparse_search(
                    local_conn, expanded_query, query_sparse,
                    top_n=SPARSE_CANDIDATES,
                    document_id=document_id,
                    filters=filters,
                )
            finally:
                release_db_conn(local_conn)

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_dense = executor.submit(run_dense)
            future_sparse = executor.submit(run_sparse)
            
            dense_results = future_dense.result()
            sparse_results = future_sparse.result()

        dense_scores:  dict[str, float] = {r["chunk_id"]: r["dense_score"] for r in dense_results}
        dense_ranked:  list[str]        = [r["chunk_id"] for r in dense_results]
        logger.debug(f"Dense search: {len(dense_results)} candidates")

        sparse_scores: dict[str, float] = {
            r["chunk_id"]: r.get("sparse_score", r.get("fts_score", 0.0))
            for r in sparse_results
        }
        sparse_ranked: list[str] = [r["chunk_id"] for r in sparse_results]
        logger.debug(f"Sparse search: {len(sparse_results)} candidates")
        
        # ─────────────────────────────────────────
        # 🔥 DOCUMENT ROUTING BOOST (PRE-RRF)
        # ─────────────────────────────────────────

        print("Target document types for routing:", target_doc_types)
        if target_doc_types:

            def match_doc_type(doc_name):
                doc_type = get_doc_type(doc_name)
                return doc_type in target_doc_types

            # Boost dense results
            for r in dense_results:
                if match_doc_type(r.get("document_name")):
                    r["dense_score"] *= 1.8

            # Boost sparse results
            for r in sparse_results:
                if match_doc_type(r.get("document_name")):
                    r["sparse_score"] = r.get("sparse_score", 0) * 1.8

        # ── Step 4: RRF fusion ─────────────────────────────────────────────────
        if not sparse_only:
            rrf_ranked = reciprocal_rank_fusion([dense_ranked, sparse_ranked], k=RRF_K)
            rrf_scores: dict[str, float] = {chunk_id: score for chunk_id, score in rrf_ranked}
        else:
            rrf_ranked = [(cid, score) for cid, score in sparse_scores.items()]
            rrf_ranked.sort(key=lambda x: x[1], reverse=True)
            rrf_scores = sparse_scores

        # Take top RERANK_CANDIDATES for initial reranking batch
        initial_ids = [cid for cid, _ in rrf_ranked[:RERANK_CANDIDATES]]
        
        logger.debug(f"Fusion/Selection: {len(rrf_ranked)} unique candidates, initial {len(initial_ids)} selected")

        # ── Step 5: Hydrate chunk records ──────────────────────────────────────
        all_known: dict[str, dict] = {}
        for r in dense_results + sparse_results:
            all_known[r["chunk_id"]] = r

        chunk_map = hydrate_chunks(conn, [cid for cid in initial_ids if cid not in all_known])
        all_known.update(chunk_map)

        # ── Step 6: ColBERT reranking (MODULARIZED) ────────────────────────────
        top_chunks = [all_known[cid] for cid in initial_ids if cid in all_known]
        rerank_scores: dict[str, float] = {}

        if use_rerank and not sparse_only and top_chunks:
            # Stage 1: Rerank the initial batch
            rerank_scores = rerank_chunks(self._embedder, query, top_chunks)
            
            # OOD Fallback Check
            OOD_THRESHOLD = 0.15
            max_score = max(rerank_scores.values()) if rerank_scores else 0.0
            
            if max_score < OOD_THRESHOLD and len(rrf_ranked) > RERANK_CANDIDATES:
                logger.info(f"OOD Fallback Triggered (max score {max_score:.3f} < {OOD_THRESHOLD}). Fetching next batch.")
                
                # Fetch next batch (e.g., next 10 candidates)
                fallback_limit = RERANK_CANDIDATES + 10
                fallback_ids = [cid for cid, _ in rrf_ranked[RERANK_CANDIDATES:fallback_limit]]
                
                # Hydrate fallback batch
                chunk_map_fallback = hydrate_chunks(conn, [cid for cid in fallback_ids if cid not in all_known])
                all_known.update(chunk_map_fallback)
                
                fallback_chunks = [all_known[cid] for cid in fallback_ids if cid in all_known]
                top_chunks.extend(fallback_chunks)
                
                # Rerank fallback batch
                fallback_scores = rerank_chunks(self._embedder, query, fallback_chunks)
                rerank_scores.update(fallback_scores)

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
        
        # ── Step 7.5: Adjust scores based on query intent ──────────────────────

        for result in results:

            text = (result.get("text") or "").lower()
            heading = (result.get("chunk_heading") or "").lower()      
                        
            # 🚫 HARD FILTER definitions (STOP further processing)
            if query_type == "enforcement":
               if ("means" in text or "includes" in text[:200] or "definition" in heading or "definitions" in heading or "व्याख्या" in text):   # ← Marathi definition keyword or "अर्थ" in text       # ← Hindi/Marathi meaning
                    result["final_score"] = 0.0
                    continue   # 🚨 CRITICAL
            
             # 🚫 HARD FILTER tables (STOP further processing)
            if query_type == "enforcement":
                if result.get("is_table") and "penalty" not in text:
                    result["final_score"] = 0.0
                    continue   # 🚨 CRITICAL
            
            # 🌍 Language-aware ranking
            query_lang = "en"  # for now assume English query

            if query_lang == "en":
                if result.get("detected_language") == "en":
                    result["final_score"] *= 1.2
                else:
                    result["final_score"] *= 0.7
            
           # 🧠 Stopword removal (CRITICAL FIX)
            STOPWORDS = {
                "the", "is", "in", "of", "for", "to", "and", "or",
                "on", "with", "by", "as", "at", "an", "be", "this",
                "that", "are", "from"
            }

            query_terms = set(query.lower().split())
            query_words = set(re.findall(r"\b\w+\b", query.lower())) - STOPWORDS
            text_words = set(re.findall(r"\b\w+\b", text)) - STOPWORDS
            
            overlap = len(query_words & text_words)
            
            # ─────────────────────────────────────────
            # ✅ STEP 4: KEYWORD PRECISION BOOST
            # ─────────────────────────────────────────

            if overlap > 0:
                keyword_score = overlap / max(len(query_terms), 1)

                # main keyword precision boost
                result["final_score"] += (1 + 0.15 * keyword_score)
            
            # 🧠 Semantic safety (protect good dense matches)
            if result.get("dense_score", 0) > 0.6:
                result["final_score"] *= 1.1
    
            # 🔍 Boost presence of important query terms
            for word in query_words:
                if word in text:
                    result["final_score"] *= 1.01
                                
            # 📜 Clause-level boost (gov docs are clause-heavy)
            if any(x in text[:120] for x in [
                "section",
                "rule",
                "clause",
                "8.",
                "9.",
                "10."
            ]):
                result["final_score"] *= 1.1   
                
            # 🟢 Boost table results for numeric queries
            if query_type == "table" and result.get("is_table"):
                result["final_score"] *= 1.3

            # 🟢 Boost relevant headings
            if query_type == "enforcement":
               if any(x in heading for x in ["penalty", "fine", "action", "compliance", "non-compliance"]):
                result["final_score"] *= 1.5
            
            # 🚫 Very low score suppression (safe cleanup)
            if result["final_score"] < 0.3:
                result["final_score"] *= 0.7
                
            # ─────────────────────────────────────────
            # ✅ STEP 2: QUALITY BOOST (SAFE)
            # ─────────────────────────────────────────

            quality = result.get("avg_quality_score") or 0.5

            # very small boost (won't break ranking)
            result["final_score"] *= (1 + 0.03 * quality)

        # Remove zero-score results
        results = [r for r in results if r["final_score"] > 0]
        
        # Sort by final score
        results.sort(key=lambda x: x["final_score"], reverse=True)

        final = results[:top_k]

        logger.info(
            f"Retrieval complete: query='{query[:100]}' → "
            f"{len(final)} results (doc={document_id}, rerank={use_rerank})"
        )

        # ── Step 8: Update Retrieval Cache ─────────────────────────────────────
        if document_id is None and not sparse_only:
            # Cache the full sorted results (before top_k cut if you want, or just final)
            # We'll cache `results` so top_k can be dynamic, but `final` is also fine.
            retrieval_cache.set(query, query_type, results)

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
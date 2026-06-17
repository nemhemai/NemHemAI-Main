# app/embedding/embedding_engine.py

"""
embedding.py — Government Knowledge Infrastructure | Embedding Layer
────────────────────────────────────────────────────────────────────────────────

POSITION IN PIPELINE:
  document_chunks (DB)  →  [THIS FILE]  →  document_embeddings (DB)
                                                     ↓
                                              retriever.py

PURPOSE:
  Batch-encode chunks using BGE-M3 and persist both dense and sparse vectors
  into the document_embeddings table (pgvector).

BGE-M3 OUTPUTS (all produced in one forward pass):
  dense_vecs   → float32[1024]          cosine similarity search
  sparse_vecs  → {token_id: weight}     learned sparse (BM25-style)
  colbert_vecs → float32[seq, 1024]     late-interaction reranking
                                        (NOT stored here — used at query time)

WHY DENSE + SPARSE:
  Dense alone misses exact keyword matches ("Section 4.13", "100 kg/day").
  Sparse alone misses semantic paraphrase ("solid waste producer" ≠ "generator").
  Together via RRF fusion they cover both failure modes.

BATCH STRATEGY:
  Optimal batch size: 32 chunks for BGE-M3 on CPU, 64 on GPU.
  Chunks are pre-sorted by token_count descending so OOM errors surface early.
  Failed batches are retried at batch_size=1 (chunk-by-chunk) before giving up.

PERFORMANCE ESTIMATES:
  CPU (no GPU):  ~0.5-1s/chunk  → 800 chunks ≈ 8-13 min  (fine for ingestion)
  GPU (T4):      ~0.05s/chunk   → 800 chunks ≈ 40-60 sec
  GPU (A100):    ~0.01s/chunk   → 800 chunks ≈ 8 sec

USAGE:
  # Embed all chunks for a document
  embedder = ChunkEmbedder()
  embedder.embed_document(conn, document_id=42)

  # Embed a query at retrieval time
  query_dense, query_sparse = embedder.embed_query("define bulk waste generator")
"""

from __future__ import annotations

from functools import lru_cache
from scipy import sparse
from app.core.config import settings
import logging
from typing import Any
import numpy as np
import time 

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

EMBEDDING_MODEL = settings.EMBED_MODEL_PATH
DENSE_DIM            = 1024             # BGE-M3 dense output dimension
DEFAULT_BATCH_SIZE   = 8               # optimized for 16GB RAM PC (balanced speed/memory)
MAX_INPUT_TOKENS     = 512              # hard cap passed to FlagEmbedding
#MIN_QUALITY_TO_EMBED = 0.0              # embed everything (filter at retrieval)

# ──────────────────────────────────────────────────────────────────────────────
# MODEL LOADER (singleton — loaded once per process)
# ──────────────────────────────────────────────────────────────────────────────

_MODEL_INSTANCE = None


def load_model() -> Any:
    """
    Load the BGE-M3 model via FlagEmbedding.
    Cached as a module-level singleton — model is loaded only once.

    FlagEmbedding docs: https://github.com/FlagOpen/FlagEmbedding
    Install: pip install FlagEmbedding

    The model is downloaded from HuggingFace on first run (~2.2 GB).
    Subsequent runs use the local cache (~/.cache/huggingface/).
    """
    global _MODEL_INSTANCE

    if _MODEL_INSTANCE is not None:
        return _MODEL_INSTANCE

    try:
        from FlagEmbedding import BGEM3FlagModel
    except ImportError:
        raise ImportError(
            "FlagEmbedding not installed. Run: pip install FlagEmbedding"
        )

    logger.info(f"Loading local BGE-M3 model from {EMBEDDING_MODEL}")

    t0 = time.time()
    
    import torch
    import gc
    import psutil
    import os

    # Aggressive garbage collection to free memory before loading large model
    gc.collect()

    # Limit PyTorch threads to avoid CPU/Memory thrashing
    physical_cores = psutil.cpu_count(logical=False) or 4
    torch.set_num_threads(physical_cores)
    os.environ["OMP_NUM_THREADS"] = str(physical_cores)

    _MODEL_INSTANCE = BGEM3FlagModel(
        EMBEDDING_MODEL,
        use_fp16=True,       # fp16 halves memory, negligible accuracy loss
        device="cuda" if cuda_available() else "cpu",
    )

    logger.info(f"Model loaded in {time.time() - t0:.1f}s")

    return _MODEL_INSTANCE


def cuda_available() -> bool:
    """Check if CUDA is available without importing torch at module level."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False
    
# ──────────────────────────────────────────────────────────────────────────────
# SPARSE VECTOR UTILS
# ──────────────────────────────────────────────────────────────────────────────

def sparse_to_dict(sparse_output: Any) -> dict[str, float]:
    """
    Convert BGE-M3 sparse output into {token_id: weight}
    Handles BOTH formats:
      1. {"indices": [...], "values": [...]}  (older format)
      2. {"123": 0.45, "456": 0.12}          (current lexical_weights)
    """

    if sparse_output is None:
        return {}

    # ✅ CASE 1: Already dict of token → weight (YOUR CASE)
    if isinstance(sparse_output, dict):
        return {
            str(k): float(v)
            for k, v in sparse_output.items()
            if float(v) > 0
        }

    # ✅ CASE 2: list wrapper
    if isinstance(sparse_output, list):
        if not sparse_output:
            return {}
        sparse_output = sparse_output[0]

    # ✅ CASE 3: indices/values format
    if isinstance(sparse_output, dict) and "indices" in sparse_output:
        indices = sparse_output.get("indices", [])
        values  = sparse_output.get("values", [])

        return {
            str(int(idx)): float(w)
            for idx, w in zip(indices, values)
            if float(w) > 0
        }

    return {}

def sparse_dot_product(a: dict, b: dict) -> float:
    """
    Compute dot product between two sparse vectors stored as {token_id: weight}.
    Used at retrieval time to score chunks against a query sparse vector.
    """
    # Iterate over the smaller dict for efficiency
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(k, 0.0) for k, w in a.items())

# ──────────────────────────────────────────────────────────────────────────────
# BATCH ENCODER
# ──────────────────────────────────────────────────────────────────────────────

def encode_batch(
    texts:      list[str],
    model:      Any,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> tuple[np.ndarray, list[dict]]:
    """
    Encode a list of texts with BGE-M3.

    Returns:
        dense_matrix: np.ndarray of shape (N, 1024)
        sparse_list:  list of N sparse dicts
    """
    all_dense:  list[np.ndarray] = []
    all_sparse: list[dict]       = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]

        try:
            output = model.encode(
                batch,
                batch_size      = len(batch),
                max_length      = MAX_INPUT_TOKENS,
                return_dense    = True,
                return_sparse   = True,
                return_colbert_vecs = False,   # not stored, used only at rerank time
            )

            dense  = output["dense_vecs"]    # np.ndarray (batch, 1024)
            sparse = output["lexical_weights"] # list of dicts
            #print("OUTPUT KEYS:", output.keys())
            #print("LEXICAL:", output.get("lexical_weights"))
            #print("OUTPUT KEYS:", output.keys())
            #print("SPARSE SAMPLE:", sparse[0])
            #print("SPARSE:", output.get("sparse_vecs"))

            # Normalise dense vectors to unit length (required for cosine via pgvector <=>)
            norms  = np.linalg.norm(dense, axis=1, keepdims=True)
            norms  = np.where(norms == 0, 1.0, norms)
            dense  = dense / norms

            all_dense.extend(dense)
            all_sparse.extend(
                [sparse_to_dict(s) for s in sparse]
            )

        except Exception as exc:
            logger.warning(
                f"Batch {i//batch_size + 1} failed: {exc}. "
                f"Retrying chunk-by-chunk..."
            )

            # Retry individually — isolates the bad chunk
            for text in batch:
                try:
                    out = model.encode(
                        [text],
                        batch_size=1,
                        max_length=MAX_INPUT_TOKENS,
                        return_dense=True,
                        return_sparse=True,
                        return_colbert_vecs=False,
                    )
                    d = out["dense_vecs"][0]
                    norm = np.linalg.norm(d)
                    d = d / norm if norm > 0 else d

                    all_dense.append(d)
                    all_sparse.append(sparse_to_dict(out["lexical_weights"][0]))

                except Exception as e2:
                    logger.error(f"Single-chunk encode failed: {e2}. Using zero vector.")
                    all_dense.append(np.zeros(DENSE_DIM, dtype=np.float32))
                    all_sparse.append({})

    return np.array(all_dense, dtype=np.float32), all_sparse


@lru_cache(maxsize=1024)
def _global_cached_embed_query(query: str, model) -> tuple[np.ndarray, dict]:
    dense_vecs, sparse_vecs = encode_batch(
        [query],
        model,
        batch_size=1
    )
    return dense_vecs[0], sparse_vecs[0]

# ──────────────────────────────────────────────────────────────────────────────
# MAIN EMBEDDER CLASS
# ──────────────────────────────────────────────────────────────────────────────

class EmbeddingEngine:
    """
    BGE-M3 encoder for document chunks.

    Usage:
        embedder = ChunkEmbedder()

        # Embed all chunks for a document (ingestion pipeline)
        embedder.embed_document(conn, document_id=42)

        # Embed a single query (retrieval pipeline)
        dense_vec, sparse_vec = embedder.embed_query("define bulk waste generator")
    """

    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE):
        self.batch_size = batch_size
        self._model     = None   # lazy-loaded on first use
        
    def build_embedding_text(self, chunk: dict) -> str:
        """
        Build structured text for embedding.

        This improves retrieval quality by adding context.
        """

        section = chunk.get("section_path") or ""
        heading = chunk.get("heading") or ""
        text    = chunk.get("text") or ""

        return f"""Section: {section}
    Title: {heading}

    Content:
    {text}""".strip()
    
    def generate_embeddings(self, chunks: list[dict]):
        """
        Generate dense + sparse embeddings for given chunks.
        """

        if not chunks:
            return [], []

        # Build structured input
        texts = [self.build_embedding_text(c) for c in chunks]

        # Encode using BGE-M3
        dense_vecs, sparse_vecs = encode_batch(
            texts,
            self.model,
            batch_size=self.batch_size
        )

        return dense_vecs, sparse_vecs

    @property
    def model(self) -> Any:
        """Lazy-load the model on first access."""
        if self._model is None:
            self._model = load_model()
        return self._model
    
    from functools import lru_cache
    
    @lru_cache(maxsize=1024)
    def _cached_embed_query(self, query: str) -> tuple[np.ndarray, dict]:
        dense_vecs, sparse_vecs = encode_batch(
            [query],
            self.model,
            batch_size=1
        )
        return dense_vecs[0], sparse_vecs[0]

    def embed_query(self, query: str) -> tuple[np.ndarray, dict]:
        """
        Encode a single query into dense + sparse vectors.
        Used during retrieval phase.
        """
        return self._cached_embed_query(query)
    
    def rerank(self, query: str, texts: list[str], top_k: int):
        """
        ColBERT-style reranking using BGE-M3 dense similarity.
        (Simplified version — works well for now)
        """

        if not texts:
            return []

        # Encode query
        q_dense, _ = self.embed_query(query)

        scores = []

        # Encode all candidate texts
        denses, _ = encode_batch(
            texts,
            self.model,
            batch_size=self.batch_size
        )

        for i, d in enumerate(denses):
            score = float(np.dot(q_dense, d))  # cosine (already normalized)
            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    


Embedding Module Documentation (app/embedding)

1. Overview

The embedding module is the semantic encoding layer of the Hybrid RAG system.

It is responsible for:
    Converting chunks into vector representations
    Generating both dense and sparse embeddings
    Storing embeddings in PostgreSQL (pgvector)
    Preparing data for hybrid retrieval (semantic + keyword)

This module transforms:
    Chunks → Searchable AI representations

2. Architecture & Flow

Pipeline Position
document_chunks (DB)
        ↓
chunk_fetcher.py
        ↓
embedding_engine.py
        ↓
embedding_store.py
        ↓
document_embeddings (DB)

3. Submodules Breakdown

3.1 Chunk Loader (chunk_fetcher.py)

Purpose
    Fetch chunks that are not yet embedded

Key Design Decisions

    1. Left Join Filtering
        LEFT JOIN document_embeddings e USING (chunk_id)
        WHERE e.chunk_id IS NULL
    
    Why:
        Ensures only unprocessed chunks are fetched
        Enables incremental embedding
    
    2. Token-Based Ordering
        ORDER BY token_count DESC
    
    Why:
        Larger chunks processed first
        Early detection of OOM errors
    
Advantages
    Efficient incremental processing
    Prevents redundant embedding

Limitations
    No pagination strategy beyond LIMIT
    No retry tracking for failed chunks

3.2 Embedding Store (embedding_store.py)

Purpose
    Persist embeddings into document_embeddings table

Key Design Decisions

    1. Dense Vector Storage
        dense.tolist()
    Stored using pgvector

    2. Sparse Vector Storage
        Json(sparse)
    Stored as JSONB

    3. Idempotent Insert
        ON CONFLICT (chunk_id) DO UPDATE
    
    Why:
        Allows reprocessing
        Supports model upgrades

Advantages
    Supports hybrid retrieval
    Safe re-runs

Limitations
    No compression of vectors
    Storage size can grow quickly

3.3 Embedding Pipeline Runner (main_embedding.py)

Purpose
    Orchestrates full embedding workflow

Flow
Fetch Chunks
   ↓
Generate Embeddings
   ↓
Store Embeddings

Key Features

    1. Batch Processing
        Default batch size: 200
        Improves throughput
    
    2. Fault Isolation
        continue  # skip failed batch
    
    Why:
        Prevents full pipeline failure
    
    3. Multi-Document Processing
        Automatically processes all pending documents
    
    4. Device Awareness
        Detects GPU availability
    
 Advantages
    Scalable pipeline
    Fault-tolerant

Limitations
    Uses print instead of logging
    No checkpointing

3.4 Embedding Engine (embedding_engine.py)

Purpose
    Generate embeddings using BGE-M3 model

4. Core Design Philosophy

❗ Why Hybrid Embeddings (Dense + Sparse)
| Type   | Strength            |
| ------ | ------------------- |
| Dense  | Semantic meaning    |
| Sparse | Exact keyword match |

Problem with Single Approach
    Dense fails on exact queries ("Section 4.13")
    Sparse fails on semantic queries ("waste producer")

✅ Solution
    Combine both using hybrid retrieval (RRF)

5. Model Choice: BGE-M3

Key Capabilities
    1024-dim dense vectors
    Sparse lexical weights
    Multilingual (English + Indic)
    Supports long context (8192 tokens)

Why BGE-M3?
| Feature       | Benefit                    |
| ------------- | -------------------------- |
| Hybrid output | Dense + Sparse in one pass |
| Multilingual  | Works with Indian docs     |
| Long context  | Matches chunk size         |

Why not alternatives?
| Model             | Reason Not Used      |
| ----------------- | -------------------- |
| OpenAI embeddings | Paid, API dependency |
| e5-large          | Limited context      |
| LaBSE             | No hybrid support    |

6. Key Components

6.1 Model Loader (Singleton)
    _MODEL_INSTANCE

Why:
    Load model only once
    Saves memory and time

6.2 Batch Encoding
    encode_batch()

Features:
    Batch processing
    Retry fallback (chunk-by-chunk)
    Dense normalization (cosine-ready)

6.3 Sparse Vector Conversion
    sparse_to_dict()

Handles:
    Multiple formats
    Converts to {token_id: weight}

6.4 Embedding Text Builder
    Section + Title + Content

Why:
    Improves retrieval quality
    Adds structural context

6.5 Query Embedding
    Same pipeline as chunks
    Ensures consistency

6.6 Reranking
    Uses cosine similarity
    Simplified ColBERT-style reranking

7. Performance Strategy

Batch Sizes
| Device | Batch Size |
| ------ | ---------- |
| CPU    | 32         |
| GPU    | 64         |

Estimates
| Hardware | Speed         |
| -------- | ------------- |
| CPU      | ~0.5–1s/chunk |
| T4 GPU   | ~0.05s/chunk  |
| A100     | ~0.01s/chunk  |

8. Advantages
    Hybrid retrieval ready
    Multilingual support
    Efficient batch processing
    Idempotent storage
    Scalable architecture

9. Limitations / Trade-offs (Critical)

❌ 9.1 Heavy Model Dependency
    Requires ~2.2GB model
    Slow first-time load

❌ 9.2 No Embedding Caching
    Recomputes embeddings

❌ 9.3 Storage Overhead
    Dense + sparse = large DB size

❌ 9.4 No Distributed Processing
    Single-node pipeline

❌ 9.5 Print-based Logging
    Not production-grade

10. Alternatives & Trade-offs

Embedding Models
| Model            | Pros                  | Cons      |
| ---------------- | --------------------- | --------- |
| BGE-M3 (current) | Hybrid + multilingual | Heavy     |
| e5-large         | Lightweight           | No sparse |
| OpenAI           | Easy                  | Paid      |

Storage Options
| Option             | Pros     | Cons           |
| ------------------ | -------- | -------------- |
| pgvector (current) | Simple   | Limited scale  |
| Pinecone           | Scalable | Paid           |
| FAISS              | Fast     | No persistence |

11. Future Improvements

High Priority
    Replace print with logging
    Add retry tracking
    Add embedding caching

Medium Priority
    Optimize storage size
    Add batching limits

Advanced
    Distributed embedding pipeline
    GPU optimization
    Vector compression

12. Key Takeaways
This module is critical for retrieval performance

Strong in:
    hybrid embeddings
    multilingual support
    efficient batching

Weak in:
    scalability
    storage efficiency

13. Non-Technical Summary (For Stakeholders)
This module converts document content into a format that AI can understand

It ensures:
    Relevant answers are found quickly
    Both exact and semantic matches work
    System supports multiple languages

It is the core intelligence engine behind search quality

Direct Assessment
    Design quality: Extremely High
    Complexity: High
    Production readiness: Medium (needs scaling improvements)
Database Module Documentation (app/database)

1. Overview

The database module defines the entire data layer architecture of the Hybrid RAG system.

It is responsible for:
    Schema definition for all pipeline stages
    Database initialization and migration execution
    Structuring data for hybrid retrieval (dense + sparse + metadata)

This module is not just storage—it encodes system intelligence, traceability, and retrieval strategy directly into the database design.

2. Architecture & Flow

End-to-End Data Flow
    Raw Document
        ↓
    documents (registry)
        ↓
    document_elements (structured extraction)
        ↓
    document_chunks (semantic units)
        ↓
    document_embeddings (vector + sparse)
        ↓
    retrieval system

Control Layer
    Frontend Upload
        ↓
    ingestion_jobs (status tracking)
        ↓
    Pipeline Execution

3. Initialization Layer

File: init_db.py
Purpose:
    Executes SQL schema files in controlled order
    Initializes database structure

Key Design Choices:
    Uses Pathlib for OS-safe file handling
    Uses connection pooling (get_db_conn)
    Explicit commit/rollback handling

    sql_files = sorted(schema_dir.glob("06_ingestion_jobs.sql"))

4. Schema Design & Justification

4.1 Extensions Layer (01_extensions.sql)

Extensions Used:

pgvector
    Enables vector similarity search
    Core for semantic retrieval

pgcrypto
    Enables SHA256 hashing
    Used for duplicate detection

pg_trgm
    Enables fuzzy text matching
    Critical for OCR error tolerance

4.2 Document Registry (documents)

Purpose:
    Central metadata store for all documents

Key Design Decisions:
    Checksum-based deduplication
    Separation of metadata and content
    Government-specific metadata fields

Why separate from content?
    Improves scalability
    Avoids heavy rows
    Enables faster filtering

4.3 Structured Elements (document_elements)

Purpose:
    Stores parsed document structure

Key Innovations:

1. Hierarchical Representation
    section_path
    heading_breadcrumb

2. Quality-Aware RAG
    quality_score
    flag_reason

3. Hybrid Search Support
    fts_tokens (Postgres full-text search)
    Trigram index for fuzzy matching

Why this design?
    Enables context-aware retrieval
    Preserves document semantics
    Handles OCR noise effectively

4.4 Chunking Layer (document_chunks)

Purpose:
    Converts elements into retrieval-ready chunks

Key Features:
    Traceability via element_ids
    Context preservation (breadcrumb, section_path)
    Quality aggregation (avg_quality_score)
    Overlap tracking for better context windows

Why not embed directly from elements?
    Elements are too granular
    Chunks provide better semantic coherence

4.5 Embedding Layer (document_embeddings)

Purpose:
    Stores embeddings for hybrid retrieval

Key Design Decisions:

1. Dense + Sparse Hybrid
    embedding (vector)
    sparse_vector (JSONB)

2. pgvector Index (IVFFLAT)
    USING ivfflat (embedding vector_cosine_ops)

3. One-to-One Mapping
    Each chunk → one embedding

Why hybrid retrieval?
    Dense = semantic meaning
    Sparse = keyword precision

4.6 Pipeline Tracking (ingestion_jobs)

Purpose:
    Tracks ingestion lifecycle

Key Features:
    Stage-based status tracking
    Progress percentage for UI
    Error logging

Why no foreign key?
Enables:
    Partial failures
    Retry mechanisms
    Loose coupling

5. Libraries & Technologies Used

5.1 PostgreSQL

Why used:
    Relational + JSONB + full-text support

Why not NoSQL?
    Lack of strong relational guarantees
    Harder joins for structured data

5.2 pgvector

Why used:
    Native vector search inside DB

Why not external vector DBs?
| Option   | Reason Not Used           |
| -------- | ------------------------- |
| Pinecone | Paid, external dependency |
| Weaviate | Infra overhead            |
| FAISS    | No persistence            |

5.3 JSONB

Why used:
    Flexible schema fields (metadata, breadcrumbs)

Trade-off:
    Slightly slower than structured columns

6. Design Strategies

6.1 Layered Data Model

Each stage has its own table:
    Registry → Elements → Chunks → Embeddings

Benefit:
    Modular pipeline
    Easy debugging

6.2 Traceability-First Design
    element_ids
    chunk_id
    section_path

Impact:
    Full auditability
    Explainable AI outputs

6.3 Hybrid Retrieval Strategy
    Full-text search (tsvector)
    Fuzzy matching (trigram)
    Vector search (pgvector)

Result:
    Robust against:
    OCR errors
    User query variations

7. Advantages
    System-Level Strengths
    Fully offline system
    Highly explainable architecture
    Scalable schema design
    Strong metadata filtering
    Supports multilingual documents

8. Limitations / Trade-offs (Critical)

❌ 8.1 Broken Initialization Logic
    Only one SQL file executed
    System will fail in production

❌ 8.2 No Migration Management
    No versioning of schema
    No rollback strategy

❌ 8.3 Weak Constraint Usage
    Missing FK in some places (intentional but risky)

❌ 8.4 IVFFLAT Requires Tuning
    Performance depends on lists parameter
    Not auto-optimized

❌ 8.5 JSONB Overuse
    Some fields could be normalized
    May impact query performance at scale

9. Alternatives & Trade-offs

Vector Storage
| Option             | Pros               | Cons                |
| ------------------ | ------------------ | ------------------- |
| pgvector (current) | Simple, integrated | Limited scalability |
| Pinecone           | Scalable           | Paid                |
| FAISS              | Fast               | No persistence      |

Schema Strategy
| Approach             | Pros            | Cons           |
| -------------------- | --------------- | -------------- |
| Normalized (current) | Clean, scalable | More joins     |
| Denormalized         | Faster reads    | Redundant data |

10. Future Improvements

High Priority
    Fix schema execution (load all SQL files)
    Add migration tool (Alembic)
    Add constraint validation

Medium Priority
    Tune vector indexes
    Add partitioning for large datasets
    Optimize JSONB usage

Advanced
    Multi-tenant schema support
    Sharding for large-scale deployment
    Hybrid storage (DB + vector DB)

11. Key Takeaways

This module is architecturally strong but operationally incomplete
Excellent design for:
    Hybrid retrieval
    Explainability
    Government-scale documents

However:
    Initialization bug is critical
    Needs production hardening

12. Non-Technical Summary (For Stakeholders)

This module stores and organizes all documents processed by the system
It ensures:
    Documents are searchable using AI
    Results are traceable and explainable
    System can handle multilingual government data

It forms the data backbone of the AI system
Without this layer, retrieval and answer generation are not possible

Direct Assessment
    Design quality: High
    Implementation maturity: Medium
    Production readiness: Not yet
Chunking Module Documentation (app/chunking)

1. Overview

The chunking module is the semantic transformation layer of the Hybrid RAG system.

It is responsible for:
    Converting structured elements into retrieval-ready chunks
    Preserving document hierarchy and legal structure
    Optimizing content for embedding models (BGE-M3)
    Ensuring traceability and explainability

This module bridges:
    Structured extraction → AI retrieval

2. Architecture & Flow

Pipeline Position
document_elements (DB)
        ↓
fetch_elements.py
        ↓
structure_chunker.py
        ↓
insert_chunks.py
        ↓
document_chunks (DB)

3. Submodules Breakdown

3.1 Element Loader (fetch_elements.py)

Purpose
    Fetch elements from document_elements table
    Normalize them into chunker-compatible format

Key Design Decisions

    1. Ordered Retrieval
        ORDER BY page_number ASC, sequence_order ASC

    Why:
        Maintains document reading order
        Critical for semantic chunking
    
    2. JSON Normalization

        Ensures fields like:
            heading_breadcrumb
            structured_content
            flag_reason
        are always valid

    3. Metadata Reconstruction
        elem["metadata"] = {...}
    
    Why:
        Chunker expects metadata structure
        DB schema and chunker interface decoupled
    
    4. Pending Document Detection
        Identifies documents not yet chunked
    
Advantages
    Clean DB abstraction
    Ensures consistent input to chunker

Limitations
    No pagination (loads entire document into memory)
    No retry mechanism

3.2 Chunk Inserter (insert_chunks.py)

Purpose
    Insert generated chunks into document_chunks table

Key Design Decisions

    1. Bulk Insert (execute_values)

    Why:
        High performance for large datasets
    
    2. JSONB Handling

        Uses Json() wrapper for:
            breadcrumb
            element_ids
            page_range
    
    3. Idempotency
        ON CONFLICT (chunk_id) DO NOTHING
    
    Why:
        Prevent duplicate insertion
        Safe reprocessing

Advantages
    Efficient insertion
    Fault-tolerant

Limitations
    No batching (risk for large documents)
    No partial failure recovery

3.3 Pipeline Runner (pipeline_runner.py)

Purpose
    Orchestrates full chunking pipeline

Flow
Load Elements
   ↓
Chunk Elements
   ↓
Insert into DB

Design Philosophy
    Thin orchestration layer
    Keeps business logic inside chunker

Advantages
    Clean separation of concerns
    Easy to extend

3.4 Core Chunker (structure_chunker.py)

Purpose
    Convert elements → semantically meaningful chunks

4. Core Design Philosophy

❗ Why NOT Fixed-Size Chunking
    Traditional approach:
        Split every 400 tokens
    
    Problem:
        Breaks semantic meaning
        Legal clauses become fragmented
    
✅ Structure-Aware Chunking (Our Approach)

Uses document structure:
    clauses
    sections
    paragraphs

Impact:
    Preserves meaning
    Improves retrieval accuracy

5. Chunking Rules (Critical)

Priority Rules
    Tables → standalone chunks
    Headings → context only
    Clauses/paragraphs → atomic units
    Target: 200–400 tokens
    Max: 450 tokens
    Min: 50 tokens
    Overlap: last 1–2 elements
    Section boundary → flush

6. Key Components

6.1 Context Prefix Builder
    [Chapter II > Definitions | Section 4]

Why important?
    Improves embedding quality
    Adds semantic context

6.2 Token Estimation
    Language-aware
    Matches ingestion pipeline logic

6.3 Overlap Strategy
    Carries last N elements forward

Why:
    Prevents context loss between chunks

6.4 Quality Signals

    Each chunk tracks:
        min_quality_score
        avg_quality_score
        has_low_quality

6.5 Traceability

    Each chunk stores:
        element_ids
        page_range
        sequence_range

6.6 Table Handling

    Always standalone
        Includes:
            natural language representation
            markdown
        
6.7 Definition Detection
    _is_definition()

Why:
    Definitions must not mix with other content
    Critical for legal retrieval

7. Advanced Features

7.1 Dynamic Buffering

    Accumulates elements until:
        token limit reached
        section changes

7.2 Smart Merging
    Small chunks merged with previous ones

7.3 Sentence Splitting (Fallback)
    Handles extremely large elements

7.4 Section Boundary Enforcement
    Prevents cross-section mixing

8. Embedding Optimization (BGE-M3)

Why BGE-M3?
    1024-dim embeddings
    Multilingual support
    Hybrid retrieval (dense + sparse)
    8192 token window

Why this chunk size?
| Parameter | Value | Reason            |
| --------- | ----- | ----------------- |
| Target    | 350   | Optimal retrieval |
| Max       | 450   | Avoid truncation  |
| Min       | 50    | Avoid noise       |

9. Advantages
    Preserves document semantics
    Improves retrieval accuracy
    Supports multilingual content
    Fully explainable
    Optimized for legal documents

10. Limitations / Trade-offs (Critical)

❌ 10.1 High Complexity
    Difficult to debug
    Hard to modify safely

❌ 10.2 Heuristic-Based
    Some decisions may fail on edge cases

❌ 10.3 Memory Usage
    Entire document loaded into memory

❌ 10.4 No Parallel Chunking
    Sequential processing

❌ 10.5 Tight Coupling to Schema
    Depends heavily on element structure

11. Alternatives & Trade-offs

Chunking Strategies
| Strategy                  | Pros           | Cons             |
| ------------------------- | -------------- | ---------------- |
| Fixed-size                | Simple         | Breaks semantics |
| Sliding window            | Better context | Redundant data   |
| Structure-aware (current) | Best accuracy  | Complex          |

12. Future Improvements

High Priority
    Add parallel chunking
    Add memory optimization
    Improve logging

Medium Priority
    Adaptive chunk sizing
    Better overlap tuning

Advanced
    LLM-based chunk refinement
    Semantic chunk scoring

13. Key Takeaways
This module is core to retrieval quality

Strong in:
    semantic preservation
    explainability
    hybrid retrieval readiness

Weak in:
    complexity
    scalability

14. Non-Technical Summary (For Stakeholders)
    This module breaks documents into meaningful pieces

    Ensures:
        AI understands context properly
        Answers are accurate and complete
        Results can be traced back to original documents

    It is the most critical layer for answer quality

Direct Assessment
    Design quality: Extremely High
    Complexity: Very High
    Production readiness: Medium-High (needs optimization)


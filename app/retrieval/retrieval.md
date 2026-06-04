Retrieval Module Documentation (app/retrieval)
1. Overview

The retrieval module is the decision engine of the Hybrid RAG system.

It is responsible for:
    Retrieving the most relevant chunks for a query
    Combining semantic (dense) and keyword (sparse) search
    Ranking and refining results using multiple strategies
    Producing high-quality context for answer generation

This module transforms:
    User Query → Relevant Context

2. Architecture & Flow

Pipeline Position
User Query
     ↓
Query Embedding
     ↓
Dense Search (pgvector)
     ↓
Sparse Search (FTS + sparse)
     ↓
RRF Fusion
     ↓
Reranking (ColBERT-style)
     ↓
Final Results

3. Core Retrieval Strategy

4-Stage Hybrid Retrieval
| Stage | Method        | Purpose                |
| ----- | ------------- | ---------------------- |
| 1     | Dense Search  | Semantic similarity    |
| 2     | Sparse Search | Keyword precision      |
| 3     | RRF Fusion    | Combine both           |
| 4     | Reranking     | Improve final ordering |

Why Hybrid Retrieval?
| Problem                     | Solution     |
| --------------------------- | ------------ |
| Dense misses exact keywords | Sparse fixes |
| Sparse misses semantics     | Dense fixes  |

4. Submodules Breakdown

4.1 Dense Search (dense.py)

Purpose
    Retrieve chunks using cosine similarity via pgvector

Key Design
    1 - (embedding <=> query_vector)
        <=> = cosine distance
        Converted to similarity
    
Features

    Supports filters:
        document_id
        language
        section_path
        quality threshold
    
Advantages
    Fast semantic retrieval
    Works well for natural language queries

Limitations
    Misses exact keywords matches
    Depends heavily on embedding qulaity

4.2 Sparse Search (sparse.py)

Purpose
    Retrieve using PostgreSQL Full-Text Search + sparse vectors

Two-Stage Strategy
    FTS (fast filtering)
    Sparse dot product (re-ranking)

Why this approach?
    FTS is fast shallow
    Sparse vectors add semantic weighting

Advantages
    Captures exact terms (e.g., "Section 4.13")
    Handles OCR noise better

Limitations
    Requires tsvector indexing
    Less semantic understanding

4.3 Fusion (fusion.py)

Method: Reciprocal Rank Fusion (RRF)
    score = 1 / (k + rank)

why RRF?
    Dense and sparse scores are not comparable
    RRF uses rank, not score

Advantages
    Simple and robust
    No normalization required

Limitations
    Ignores actual score magnitude

4.4 Hydration (hydration.py)

Purpose
    Fetch full chunk data after ranking

Why needed?
    Initial retrieval returns partial data
    Hydration enriches results

4.5 Reranker (reranker.py)

Purpose
    Improve ranking using embedding similarity

Method
    Recompute similarity with query
    Sort candidates

Why Rerank?
    Initial retrieval is approximate
    Reranking improves precision

4.6 Query Intent Detection (query_intent.py)

Purpose
    Classify query type

Types
| Type        | Example          |
| ----------- | ---------------- |
| definition  | "What is..."     |
| enforcement | "Penalty for..." |
| table       | "Amount per day" |
| general     | default          |

Why needed?
    Adjust ranking dynamically
    Improve relevance

4.7 Filters (filters.py)

Purpose 
    Central configuration for retrieval

Key Constants
| Parameter         | Value |
| ----------------- | ----- |
| DENSE_CANDIDATES  | 50    |
| SPARSE_CANDIDATES | 50    |
| RERANK_CANDIDATES | 15    |
| DEFAULT_TOP_K     | 10    |

Why Filtering?
    Remove low-quality chunks
    Improve precision

4.8 Main Retriever (retriever.py)

Purpose
    Orchestrates full hybrid retrieval pipeline

5. Retrieval Piepline (Detailed)

Step 1: Query Embedding
    Generate:
        dense vector
        sparse vector
    
Step 2: Dense Retrieval
    Top 50 semantic matches

Step 3: Sparse Retrieval
    Top 50 keyword matches

Step 4:  RRF Fusion
    Merge both result sets

Step 5: Hydration
    Load full chunk data

Step 6: Reranking
    Refine top 15 results

Step 7: Final Scoring Adjustments

    Advanced scoring logic includes:

        Keyword Overlap Boost
            overlap(query_words, text_words)
        
        Language Boost
            English preferred (currently)

        Clause Detection Boost
            Boost sections like:
                "Section"
                "Rule"
        
        Query Intent Boost
            | Type        | Boost                   |
            | ----------- | ----------------------- |
            | enforcement | penalty-related content |
            | table       | table chunks            |
            | definition  | definition sections     |

        Quality-Based Adjustment
            Uses avg_quality_score
        
        Final Output
            Each result contains:
                text
                section_path
                chunk metadata

                scores:
                    dense_score
                    sparse_Score
                    rrf_score
                    final_score
    
6. Advanced Features

6.1 Hard Filtering Logic
    Removec irrelevant chunks completely 

    Example:
        Definitions removed for enforcement queries
    
6.2 Overlap-Aware Ranking
    Boost chunks with shared query terms

6.3 Semantic Safety
    Protects strong dense matches

6.4 Table-Aware Retieval
    Special handling for structured data

7. Advantages
    Combines semantic + keywords search
    Highly customizable ranking
    Explainable scoring
    Handles noisy OCR data
    Optimized for legal/governments docs

8. Limitations/  Trade-oofs (critical)

❌ 8.1 High Complexity
    Many heuristics
    Hard to tune

❌ 8.2 Heuristic Overfitting
    May not generalize

❌ 8.3 Performance Cost
    Multiple stages → slower

❌ 8.4 No Learning-Based Ranking
    All rules are manual

❌ 8.5 Language Bias
    Currently favors English

9. Alternatives & Trade-offs

Retrieval Strategies
| Strategy         | Pros          | Cons             |
| ---------------- | ------------- | ---------------- |
| Dense-only       | Simple        | Misses keywords  |
| Sparse-only      | Precise       | Misses semantics |
| Hybrid (current) | Best accuracy | Complex          |

Fusion Methods
| Method       | Pros     | Cons           |
| ------------ | -------- | -------------- |
| RRF          | Robust   | Ignores scores |
| Weighted sum | Flexible | Needs tuning   |

10. Future Improvements

High Priority
    Add learning-based ranking (LTR)
    Improve multilingual handling
    Optimize performance

Medium Priority
    Adaptive weighting (dense vs sparse)
    Better query intent detection

Advanced
    Neural rerankers (ColBERT full)
    Query expansion
    Feedback-based learning

11. Key Takeaways
This module is the core intelligence of retrieval

Strong in:
    hybrid search
    explainability
    flexibility

Weak in:
    complexity
    scalability

12. Non-Technical Summary (For Stakeholders)
This module finds the most relevant information from documents

It ensures:
    Accurate answers
    Fast search
    Context-aware results

It is the brain of the search system

Direct Assessment
    Design quality: Extremely High
    Complexity: Very High
    Production readiness: Medium (needs optimization & simplification)




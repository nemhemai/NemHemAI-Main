Retrieval Evaluation Module Documentation (app/retrieval_evaluation)
1. Overview

The retrieval_evaluation module is the validation and performance measurement layer of the Hybrid RAG system.

It is responsible for:
    Measuring retrieval effectiveness using standard IR metrics
    Generating evaluation datasets automatically
    Identifying failure patterns
    Providing insights to improve retrieval quality

This module transforms:
    Retrieval Outputs → Measurable Performance Metrics

2. Architecture & Flow

Evaluation Pipeline
Dataset Generation
      ↓
Retriever Execution
      ↓
Metric Calculation
      ↓
Failure Analysis
      ↓
Performance Report

3. Evaluation Results (Our System)

    Total Queries : 38
    Top-1 Accuracy: 0.921
    Top-3 Accuracy: 0.947
    Precision@5   : 0.763
    MRR           : 0.934

Interpretation
| Metric | Value | Meaning                                 |
| ------ | ----- | --------------------------------------- |
| Top-1  | 0.921 | 92% queries correct at rank 1           |
| Top-3  | 0.947 | Almost all queries correct within top 3 |
| P@5    | 0.763 | Some noise in lower ranks               |
| MRR    | 0.934 | Relevant results appear very early      |

Direct Assessment
    Retrieval quality: Very High
    Ranking quality: Strong
    Noise control: Moderate (needs tuning)

4. Submodules Breakdown

4.1 Metrics (metrics.py)

Purpose
    Define evaluation metrics for retrieval quality

Core Metrics
    1. Top-1 Accuracy
        Is first result relevant?

    2. Top-3 Accuracy
        Checks if any of top 3 results are relevant

    3. Precision@K
        relevant_results / k

    4. Mean Reciprocal Rank (MRR)
        1 / rank_of_first_relevant
    
Relevance Logic
    is_relevant()

Multi-Level Matching Strategy
| Level | Type                            | Priority |
| ----- | ------------------------------- | -------- |
| 1     | Exact chunk_id match            | Highest  |
| 2     | Semantic match (reranker score) | Medium   |
| 3     | Keyword/section match           | Lowest   |

Why this design?
    Real-world retrieval is noisy
    Exact match alone is too strict

Advantages
    Flexible evaluation
    Captures semantic relevance

Limitations
    Heuristic-based relevance
    No human labeling

4.2 Evaluator (evaluator.py)

Purpose
    Execute retrieval on dataset
    Compute metrics per query

Key Design

Per-Query Evaluation
    evaluate_query()

Dataset Evaluation
    evaluate_dataset()

Output Structure
    Each result contains:
        query
        type
        metrics (top1, top3, p@5, mrr)
        top retrieved chunks

Advantages
    Simple interface
    Modular

Limitations
    No batching or parallel execution
    No logging

4.3 Analysis (analysis.py)

Purpose
    Identify failures and categorize them

Failure Types
| Type                | Example         |
| ------------------- | --------------- |
| enforcement_failure | penalty queries |
| definition_failure  | "what is..."    |
| table_failure       | numeric queries |
| general_failure     | fallback        |

Why needed?
    Helps debug retrieval weaknesses

4.4 Runner (runner.py)

Purpose
    Entry point for evaluation

Responsibilities
    Load dataset
    Run evaluator
    Compute aggregate metrics

Output
    Console-based report

Limitations
    No visualization
    No persistent logs

4.5 Dataset Generator (dataset_generator.py)

Purpose
    Automatically generate evaluation dataset from chunks

5. Dataset Generation Pipeline

Step-by-Step
Fetch Chunks
   ↓
Filter Valid Chunks
   ↓
Extract Terms
   ↓
Generate Queries
   ↓
Validate Queries
   ↓
Balance Dataset

Key Techniques

    1. Balanced Sampling
    Ensures equal distribution:
        definition
        enforcement
        table
        general

    2. Term Extraction
        extract_term()
    Extracts meaningful keywords

    3. Query Templates
        | Type        | Example          |
        | ----------- | ---------------- |
        | definition  | "What is X?"     |
        | enforcement | "Penalty for X?" |
        | table       | "Limits for X?"  |

    4. Data Cleaning
        Removes duplicates
        Filters low-quality queries

Advantages
    Fully automated dataset generation
    Covers multiple query types

Limitations
    Synthetic queries (not real users)
    May introduce bias

6. Design Strategies

6.1 Weak Supervision
    Uses heuristics instead of labeled data

6.2 Multi-Metric Evaluation
    Captures:
        accuracy
        ranking quality
        precision

6.3 Failure Categorization
    Enables targeted improvements

7. Advantages
    Automated evaluation pipeline
    Supports continuous improvement
    Covers multiple query types
    Lightweight and fast

8. Limitations / Trade-offs (Critical)

❌ 8.1 Synthetic Dataset Bias
    Not representative of real users

❌ 8.2 Weak Relevance Labels
    Based on heuristics
    Not ground truth

❌ 8.3 Small Dataset Size
    Only 38 queries
    Not statistically strong

❌ 8.4 No Human Evaluation
    Missing qualitative feedback

9. Alternatives & Trade-offs

Evaluation Methods
| Method              | Pros     | Cons          |
| ------------------- | -------- | ------------- |
| Heuristic (current) | Fast     | Less accurate |
| Human annotation    | Accurate | Expensive     |
| LLM-based eval      | Scalable | Costly        |

10. Insights from Your Results

Strengths
    Excellent Top-1 accuracy → retrieval is precise
    High MRR → relevant results appear early
    Strong hybrid retrieval performance

Weaknesses
    Precision@5 lower → irrelevant results in lower ranks
    Some noise in ranking
    Likely issues:
        over-boosting keywords
        weak filtering

11. Recommended Improvements

High Priority
    Increase dataset size (100–300 queries)
    Add real user queries
    Improve relevance labeling

Medium Priority
    Add per-type metrics (definition vs enforcement)
    Improve failure analysis

Advanced
    Add LLM-based evaluation
    Build feedback loop
    Track performance over time

12. Key Takeaways
    This module ensures system reliability and quality
        Strong in:
            evaluation design
            automation
            metric coverage

        Weak in:
            dataset realism
            scalability

13. Non-Technical Summary (For Stakeholders)
    This module checks how well the AI system performs
        It ensures:
            Answers are accurate
            Relevant information is retrieved
            System improves over time
    It acts as the quality control 

Final Assessment
    Design quality: High
    Reliability: Medium (needs better data)
    Production readiness: Medium
    
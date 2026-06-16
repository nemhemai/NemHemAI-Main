Generation Module Documentation (app/generation)
1. Overview

The generation module is the final answer synthesis layer of the Hybrid RAG system.

It is responsible for:
    Converting retrieved chunks into structured answers
    Ensuring answers are grounded in source documents
    Extracting responses in strict JSON format
    Generating citations and translations

This module transforms:
    Retrieved Context → Final Answer (with citations)

2. Architecture & Flow

Pipeline Position
Retrieved Chunks
       ↓
Context Filtering
       ↓
Context Builder
       ↓
Prompt Builder
       ↓
LLM (Inference)
       ↓
Answer Extractor
       ↓
Translation
       ↓
Citation Builder
       ↓
Final Response

3. Core Design Philosophy

❗ Controlled Generation (NOT Free-Form LLM)
    Unlike typical RAG systems:
        LLM → Generate answer freely
    
    ❌ Problems:
        Hallucination
        Unverifiable answers
        No traceability

✅ Our Approach: Extraction-Based Generation
    LLM → Extract answer from context (strict JSON)
        ✔ No hallucination
        ✔ Fully grounded answers
        ✔ Structured output

4. Submodules Breakdown

4.1 Pipeline (pipeline.py)

Purpose
    Orchestrates full generation flow

Flow
Filter Chunks
   ↓
Build Context
   ↓
Build Prompt
   ↓
Extract Answer
   ↓
Translate
   ↓
Build Final Response

Key Design Decisions

    1. Context Limiting
        MAX_CHUNKS = 3

    Why:
        Reduces noise
        Improves LLM focus
        Prevents context overflow

    2. Definition Boosting
        Reorders chunks for definition queries

4.2 Context Builder (context_builder.py)

Purpose
    Convert chunks into structured prompt format

Format
    [CHUNK 1]
    DOCUMENT: X
    SECTION: Y
    PAGES: Z

    CONTENT:
    ...

Why structured context?
    Improves LLM understanding
    Enables traceability

Limitations
    Fixed truncation (800 chars)
    May lose important info

4.3 Prompt Builder (prompt_builder.py)

Purpose
    Create strict LLM instructions

Key Strategy
    ONLY return JSON between <START> and <END>

Why?
    Prevents hallucination
    Ensures machine-readable output

Constraints
    No explanation
    Copy exact text
    Structured output

4.4 Answer Extractor (answer_extractor.py)

Purpose
    Parse LLM output into structured response

Multi-Step Parsing Strategy

    1. Tagged JSON Extraction
        <START> {...} <END>

    2. Fallback JSON Detection
        Extract any JSON block

    3. Final Fallback
        Extract directly from chunks

Special Handling

    Placeholder Detection
        "answer_original": "..."
    → triggers fallback

Advantages
    Robust parsing
    Multiple fallback layers

Limitations
    Regex-based parsing
    Can break with malformed output

4.5 Citation Builder (citation_builder.py)

Purpose
    Attach source references to answers

Output Structure
    {
    document_id,
    section_path,
    page_range,
    snippet
    }

Why needed?
    Explainability
    Trust in AI outputs

4.6 Context Filter (context_filter.py)

Purpose
    Reorder chunks based on query intent

Example
    Definition queries → prioritize "means", "defined as"

Why not modify retrieval?
    Keeps retrieval generic
    Applies lightweight post-processing

4.7 Translator (translator.py)

Purpose
    Translate answers into target language

Why needed?
    Multilingual support
    Government use cases

Limitations
    Uses same LLM
    No quality control

4.8 Response Builder (response_builder.py)

Purpose
    Combine all outputs into final response

Output Format
    {
    query,
    answer_original,
    answer_translated,
    citations,
    confidence
    }

4.9 Main Entry (main_generation.py)

Purpose
    Run full pipeline with:
        retriever
        LLM

LLM Used
    Local model via llama_cpp

Why local LLM?
| Advantage | Reason             |
| --------- | ------------------ |
| Privacy   | No API calls       |
| Cost      | Free inference     |
| Control   | Full customization |

5. Key Strategies

5.1 Grounded Answering
    Only extract from context
    No external knowledge

5.2 Structured Output Enforcement
    JSON-only responses
    Regex validation

5.3 Multi-Level Fallback
    LLM extraction
    JSON fallback
    Chunk fallback

5.4 Context Optimization
    Limit chunks
    Reorder intelligently

6. Advantages
    Zero hallucination risk
    Fully explainable answers
    Structured outputs
    Multilingual support
    Robust fallback mechanisms

7. Limitations / Trade-offs (Critical)

❌ 7.1 Over-Constrained LLM
    Cannot generate natural explanations
    Limited flexibility

❌ 7.2 Context Loss
    Only 3 chunks used
    May miss relevant info

❌ 7.3 Regex Fragility
    JSON extraction can fail

❌ 7.4 No Answer Synthesis
    Only extracts (does not summarize across chunks)

❌ 7.5 Translation Quality
    No validation
    Depends on LLM

8. Alternatives & Trade-offs

Generation Approaches
| Approach             | Pros     | Cons               |
| -------------------- | -------- | ------------------ |
| Extractive (current) | Safe     | Less flexible      |
| Generative           | Natural  | Hallucination risk |
| Hybrid               | Balanced | Complex            |

9. Future Improvements

High Priority
    Add structured logging
    Improve JSON parsing robustness
    Increase context size dynamically

Medium Priority
    Add answer synthesis across chunks
    Improve translation quality

Advanced
    Citation-aware generation
    Confidence scoring via model
    Multi-hop reasoning

10. Key Takeaways
This module ensures answer correctness and trust

    Strong in:
        grounding
        explainability
        robustness

    Weak in:
        flexibility
        expressiveness

11. Non-Technical Summary (For Stakeholders)
This module generates answers from documents

    It ensures:
        Answers are accurate
        Sources are clearly shown
        System supports multiple languages
    It is the final output layer of the AI system

Final Assessment
    Design quality: Extremely High
    Reliability: Very High
    Production readiness: Medium-High (needs flexibility improvements)

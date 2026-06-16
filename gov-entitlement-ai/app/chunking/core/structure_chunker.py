# app/chunking/core/structure_chunker.py


"""
chunker.py — Government Knowledge Infrastructure | Chunking Layer
────────────────────────────────────────────────────────────────────────────────

POSITION IN PIPELINE:
  document_elements (DB)  →  [THIS FILE]  →  chunks[]  →  BGE-M3  →  vector store

PURPOSE:
  Convert structured document elements (from the extraction + validation pipeline)
  into embedding-ready chunks that preserve legal document structure.

WHY NOT FIXED-SIZE CHUNKING:
  Fixed-size chunking (every 400 tokens) destroys clause atomicity.
  A clause like "4.13. Bulk Waste Generator means any establishment generating
  more than 100 kg of waste per day" becomes two fragments — the definition
  head in one chunk and the definition body in another. The retriever then
  returns a fragment that answers "what is 100 kg" but not "define bulk waste".

  This chunker uses STRUCTURE-AWARE chunking: it respects the document's own
  logical units (clauses, paragraphs, sections) as the primary split boundaries.

CHUNKING RULES (in priority order):
  1. Tables → always standalone chunks, never merged with text
  2. Headings/sections → never standalone, carried as context metadata
  3. Clauses/paragraphs → atomic units, never split mid-element
  4. Target: 200–400 tokens per chunk (optimal for factual RAG retrieval)
  5. Max: 450 tokens (hard limit, with fallback sentence split for huge elements)
  6. Min: 50 tokens (sub-threshold elements merge forward)
  7. Overlap: last 1-2 elements carried into the next chunk for retrieval continuity
  8. Section boundary → always flush current buffer

CONTEXT PREFIX (WHY IT MATTERS FOR BGE-M3):
  BGE-M3 retrieves better when chunks carry their document context.
  A clause reading "100 kg per day" alone is ambiguous.
  Prefixed as "[Chapter II > Definitions | Section 4] 4.13. Bulk Waste Generator..."
  it becomes retrievable for queries about definitions, thresholds, and chapter content.
  The prefix is stored in `text` (used for embedding). `text_raw` has no prefix (for UI).

EMBEDDING MODEL NOTES:
  BGE-M3 (BAAI/bge-m3) — recommended:
    • 8192-token window — our chunks of 450 max fit with large margin
    • Multilingual: English, Hindi, Marathi all supported natively
    • Hybrid: single inference gives dense + sparse (BM25-like) + colbert scores
    • Best choice for Indian government documents with mixed languages

  Alternatives if BGE-M3 is unavailable:
    • multilingual-e5-large: good, 512 tokens, weaker on Indic languages
    • LaBSE: 512 tokens, strong cross-lingual but weaker on long docs
    • IndicBERT: Hindi/Marathi only — would need separate English model

INPUT:
  List of element dicts from document_elements (as loaded from DB or memory).
  Required fields per element:
    element_id, document_id, element_type, section_path, heading_breadcrumb,
    sequence_order, page_number, content_original, token_count, detected_language,
    quality_score, is_manual_review, structured_content (for tables)

OUTPUT:
  List of chunk dicts — see _build_chunk() for the full schema.
  Each chunk is ready for: DB insertion, BGE-M3 embedding, BM25 indexing.
"""

from __future__ import annotations

import re
import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# TUNEABLE CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

MIN_CHUNK_TOKENS   = 50    # chunks below this are too small to embed meaningfully
TARGET_CHUNK_TOKENS = 350  # ideal chunk size for factual RAG retrieval
MAX_CHUNK_TOKENS   = 450   # hard ceiling — never exceed this (minus prefix tokens)
OVERLAP_ELEMENTS   = 2     # number of elements carried forward as overlap

# Element types that carry context but are not content
CONTEXT_TYPES = {"heading", "section"}

# Element types that are always standalone chunks
STANDALONE_TYPES = {"table"}

# Quality threshold below which a chunk is flagged
LOW_QUALITY_THRESHOLD = 0.70

# Max tokens reserved for the context prefix (so content fits in MAX_CHUNK_TOKENS)
PREFIX_TOKEN_BUDGET = 40


# ──────────────────────────────────────────────────────────────────────────────
# TOKEN COUNTER
# ──────────────────────────────────────────────────────────────────────────────

def _count_tokens(text: str, lang: str = "en") -> int:
    """
    Fast token estimator (no tokenizer required).
    Matches the logic in text_utils.py for consistency.
    Indic scripts use character-based estimation (fewer spaces).
    """
    if not text:
        return 0
    if lang in ("hi", "mr", "ta", "te", "kn"):
        return max(1, len(text) // 4)
    return len(text.split())


# ──────────────────────────────────────────────────────────────────────────────
# CONTEXT PREFIX BUILDER
# ──────────────────────────────────────────────────────────────────────────────

def _build_context_prefix(
    breadcrumb: list[str],
    section_path: str | None,
    chunk_heading: str | None,
) -> str:
    """
    Build the context prefix that is prepended to the chunk text before embedding.

    Format:  [Breadcrumb > Path | Section X] Heading:
    Example: [Chapter II > Definitions | Section 4] CHAPTER-II DEFINITIONS:

    This makes short clauses like "4.13. Bulk Waste Generator means ..."
    retrievable under queries for "definition", "chapter 2", "section 4", etc.

    Kept under PREFIX_TOKEN_BUDGET tokens so it doesn't dominate the chunk.
    """
    parts: list[str] = []

    # Breadcrumb: take last 2 levels to stay concise
    if breadcrumb:
        clean_breadcrumb = []

        for b in breadcrumb:
            b = b.strip()

            # ❌ skip numeric / noisy entries
            if not b:
                continue
            if b.isdigit():
                continue
            if len(b) <= 3:
                continue
            if re.match(r"^[0-9\.\-\(\)]+$", b):
                continue

            clean_breadcrumb.append(b)

        crumb = " > ".join(clean_breadcrumb[-2:])

        if crumb:
            parts.append(crumb)

    if section_path:
        sec = str(section_path).strip().replace(".", "")

        if sec:
            parts.append(f"Section {sec}")

    bracket = ""
    if parts:
        bracket = "[" + " | ".join(parts) + "]"

    if chunk_heading:
        heading_short = (
            chunk_heading
            .replace("::", ":")
            .replace("  ", " ")
            .strip()
        )[:60]
        if bracket:
            return f"{bracket} {heading_short}:"
        return f"{heading_short}:"

    return bracket


# ──────────────────────────────────────────────────────────────────────────────
# SENTENCE SPLITTER (fallback for huge single elements)
# ──────────────────────────────────────────────────────────────────────────────

def _split_long_text(text: str, max_tokens: int, lang: str = "en") -> list[str]:
    """
    Emergency fallback: split a single element that exceeds max_tokens.

    Splits on sentence boundaries (. ? ! । — the Devanagari danda).
    Used only when a single extracted element is too large for one chunk.
    In practice this should be rare — most clauses are 20-80 tokens.
    """
    # Sentence boundary pattern (handles English and Devanagari)
    sentence_re = re.compile(r"(?<=[.!?।])\s+")
    sentences   = sentence_re.split(text)

    segments: list[str] = []
    current:  list[str] = []
    current_tokens = 0

    for sentence in sentences:
        s_tokens = _count_tokens(sentence, lang)

        if current_tokens + s_tokens > max_tokens and current:
            segments.append(" ".join(current))
            current = [sentence]
            current_tokens = s_tokens
        else:
            current.append(sentence)
            current_tokens += s_tokens

    if current:
        segments.append(" ".join(current))

    return [s for s in segments if s.strip()]


# ──────────────────────────────────────────────────────────────────────────────
# CHUNK BUILDER
# ──────────────────────────────────────────────────────────────────────────────

def _build_chunk(
    buffer:         list[dict],
    document_id:    int | str,
    chunk_index:    int,
    section_path:   str | None,
    breadcrumb:     list[str],
    chunk_heading:  str | None,
    is_overlap_start: bool = False,
    overlap_tokens:   int  = 0,
    is_table:         bool = False,
    table_markdown:   str | None = None,
) -> dict | None:
    """
    Assemble a chunk dict from a buffer of elements.

    Returns None if the buffer is empty or produces no usable text.
    """
    if not buffer:
        return None

    # ── Collect text ──────────────────────────────────────────────────────────
    texts: list[str] = []

    for elem in buffer:
        text = (elem.get("content_original") or "").strip()
        if text:
            texts.append(text)

    if not texts:
        return None

    text_raw = "\n".join(texts)

    if not text_raw.strip():
        return None

    # ── Build context prefix ──────────────────────────────────────────────────
    prefix     = _build_context_prefix(breadcrumb, section_path, chunk_heading)
    text_full  = f"{prefix} {text_raw}".strip() if prefix else text_raw

    # ── Language: majority vote across elements ───────────────────────────────
    langs     = [e.get("detected_language") or "en" for e in buffer]
    lang      = Counter(langs).most_common(1)[0][0]

    token_count = _count_tokens(text_full, lang)

    # ── Quality metrics ───────────────────────────────────────────────────────
    quality_scores = [
        e.get("quality_score") or 1.0
        for e in buffer
        if e.get("quality_score") is not None
    ]
    min_quality = round(min(quality_scores), 3) if quality_scores else 1.0
    avg_quality = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 1.0
    has_low_quality = any(
        (e.get("quality_score") or 1.0) < LOW_QUALITY_THRESHOLD for e in buffer
    )

    # ── Source traceability ───────────────────────────────────────────────────
    element_ids   = [e["element_id"] for e in buffer if e.get("element_id")]
    pages         = sorted(set(
        e.get("metadata", {}).get("page_number") or e.get("page_number")
        for e in buffer
        if (e.get("metadata", {}).get("page_number") or e.get("page_number"))
    ))
    seq_orders    = [e.get("sequence_order", 0) for e in buffer]
    element_types = [e.get("element_type", "paragraph") for e in buffer]

    # ── Chunk ID ──────────────────────────────────────────────────────────────
    # Format: {doc_id}_c{chunk_index}
    chunk_id = f"{document_id}_c{chunk_index:04d}"

    # ── Chunk type ────────────────────────────────────────────────────────────
    if is_table:
        chunk_type = "table"
    elif chunk_heading and len(texts) == 1:
        chunk_type = "heading_text"
    else:
        chunk_type = "text"

    return {
        # ── Identity ──────────────────────────────────────────────────────────
        "chunk_id":         chunk_id,
        "document_id":      document_id,

        # ── Text ──────────────────────────────────────────────────────────────
        "text":             text_full,      # → send this to BGE-M3 for embedding
        "text_raw":         text_raw,       # → show this in the UI / citations

        # ── Table-specific: markdown for LLM context window ───────────────────
        "table_markdown":   table_markdown, # None for non-table chunks

        # ── Document structure context ────────────────────────────────────────
        "section_path":     section_path,
        "breadcrumb":       list(breadcrumb),
        "chunk_heading":    chunk_heading,

        # ── Source traceability ───────────────────────────────────────────────
        "element_ids":      element_ids,
        "page_range":       pages,
        "sequence_range":   [min(seq_orders), max(seq_orders)] if seq_orders else [],

        # ── Content metadata ──────────────────────────────────────────────────
        "element_types":    element_types,
        "is_table":         is_table,
        "chunk_type":       chunk_type,
        "token_count":      token_count,
        "detected_language": lang,

        # ── Quality ───────────────────────────────────────────────────────────
        "min_quality_score": min_quality,
        "avg_quality_score": avg_quality,
        "has_low_quality":   has_low_quality,

        # ── Overlap tracking ──────────────────────────────────────────────────
        "has_overlap":      is_overlap_start,
        "overlap_tokens":   overlap_tokens,
    }


# ──────────────────────────────────────────────────────────────────────────────
# BUFFER FLUSHER
# ──────────────────────────────────────────────────────────────────────────────

def _flush_buffer(
    buffer:        list[dict],
    chunks:        list[dict],
    chunk_index:   int,
    document_id:   int | str,
    section_path:  str | None,
    breadcrumb:    list[str],
    chunk_heading: str | None,
    is_overlap:    bool = False,
    overlap_tokens: int = 0,
) -> int:
    """
    Flush the current buffer into a chunk and append to chunks list.
    Returns the updated chunk_index.
    """
    if not buffer:
        return chunk_index

    # Skip if total content is below min threshold
    total_tokens = sum(_count_tokens(
        e.get("content_original") or "", e.get("detected_language") or "en"
    ) for e in buffer)

    if total_tokens < MIN_CHUNK_TOKENS:
        logger.debug(
            f"Buffer below min ({total_tokens} tokens) — "
            f"merging forward or discarding"
        )
        # Still emit — the next chunk will absorb these via overlap or they
        # stand alone. The caller decides whether to carry them forward.

    chunk = _build_chunk(
        buffer        = buffer,
        document_id   = document_id,
        chunk_index   = chunk_index,
        section_path  = section_path,
        breadcrumb    = breadcrumb,
        chunk_heading = chunk_heading,
        is_overlap_start = is_overlap,
        overlap_tokens   = overlap_tokens,
    )

    if chunk:

        # 🔥 NEW: Merge small chunks with previous chunk
        if chunk["token_count"] < MIN_CHUNK_TOKENS and chunks:

            prev = chunks[-1]

            prev["text"] += " " + chunk["text"]
            prev["text_raw"] += " " + chunk["text_raw"]

            prev["token_count"] += chunk["token_count"]

            # merge metadata
            prev["element_ids"].extend(chunk["element_ids"])
            prev["page_range"] = sorted(set(prev["page_range"] + chunk["page_range"]))
            prev["sequence_range"] = [
                min(prev["sequence_range"][0], chunk["sequence_range"][0]),
                max(prev["sequence_range"][1], chunk["sequence_range"][1])
            ]

            prev["element_types"].extend(chunk["element_types"])

            # quality merge
            prev["min_quality_score"] = min(prev["min_quality_score"], chunk["min_quality_score"])
            prev["avg_quality_score"] = (
                prev["avg_quality_score"] + chunk["avg_quality_score"]
            ) / 2

            prev["has_low_quality"] = (
                prev["has_low_quality"] or chunk["has_low_quality"]
            )

        else:
            chunks.append(chunk)
            chunk_index += 1

        return chunk_index
    
def _is_definition(text: str) -> bool:
    """
    Detect definition clauses in legal/government documents.
    """

    if not text:
        return False

    text = text.strip().lower()

    patterns = [
        r'^"?[a-z0-9\s\-]+"?\s+means\b',
        r'^"?[a-z0-9\s\-]+"?\s+shall\s+mean\b',
        r'^"?[a-z0-9\s\-]+"?\s+refers\s+to\b',
    ]

    for p in patterns:
        if re.match(p, text):
            return True

    return False

# ──────────────────────────────────────────────────────────────────────────────
# MAIN CHUNKER
# ──────────────────────────────────────────────────────────────────────────────

class DocumentChunker:
    """
    Structure-aware chunker for Indian government PDF documents.

    Usage:
        chunker = DocumentChunker()
        chunks  = chunker.chunk(elements, document_id=doc_id)

    Args:
        min_tokens:    Minimum tokens per chunk (default 50)
        target_tokens: Target tokens per chunk (default 350)
        max_tokens:    Hard maximum tokens per chunk (default 450)
        overlap_n:     Number of elements to carry as overlap (default 2)

    The chunker reads elements in sequence_order order, groups them into
    coherent chunks, and emits a list of chunk dicts ready for embedding.
    """

    def __init__(
        self,
        min_tokens:    int = MIN_CHUNK_TOKENS,
        target_tokens: int = TARGET_CHUNK_TOKENS,
        max_tokens:    int = MAX_CHUNK_TOKENS,
        overlap_n:     int = OVERLAP_ELEMENTS,
    ):
        self.min_tokens    = min_tokens
        self.target_tokens = target_tokens
        self.max_tokens    = max_tokens
        self.overlap_n     = overlap_n

    # ── Public entry point ────────────────────────────────────────────────────

    def chunk(
        self,
        elements:    list[dict],
        document_id: int | str,
    ) -> list[dict]:
        """
        Chunk a list of document elements into embedding-ready chunks.

        Args:
            elements:    List of element dicts (from document_elements DB or extractor).
                         Must have: element_id, element_type, sequence_order,
                         content_original, token_count, detected_language,
                         section_path, heading_breadcrumb, quality_score,
                         structured_content (for tables), metadata.page_number
            document_id: The document this belongs to.

        Returns:
            List of chunk dicts. See module docstring for schema.
        """
        if not elements:
            return []

        # Sort by reading order (sequence_order is the canonical order)
        elements = sorted(
            elements,
            key=lambda e: (
                e.get("metadata", {}).get("page_number") or e.get("page_number") or 0,
                e.get("sequence_order") or 0,
            )
        )

        chunks:        list[dict] = []
        buffer:        list[dict] = []
        overlap_carry: list[dict] = []   # elements from end of prev chunk

        chunk_index    = 0
        buffer_tokens  = 0
        buffer_is_overlap_start = False  # True when buffer begins with overlap elements
        buffer_overlap_tokens   = 0      # token count of overlap prefix in buffer

        # Context state — updated when we see headings/sections
        current_section:   str | None  = None
        current_breadcrumb: list[str]  = []
        current_heading:   str | None  = None
        prev_section:      str | None  = None

        for elem in elements:
            etype = elem.get("element_type", "paragraph")
            # 🔥 NEW: Section boundary enforcement (works for ALL elements)
            new_section = elem.get("section_path")

            if (
                buffer and
                current_section and
                new_section and
                new_section != current_section
            ):

                chunk_index = _flush_buffer(
                    buffer, chunks, chunk_index, document_id,
                    current_section, current_breadcrumb, current_heading,
                    is_overlap=buffer_is_overlap_start,
                    overlap_tokens=buffer_overlap_tokens,
                )

                overlap_carry = buffer[-self.overlap_n:] if len(buffer) >= self.overlap_n else buffer[:]

                buffer = []
                buffer_tokens = 0
                buffer_is_overlap_start = False
                buffer_overlap_tokens = 0

                current_section = new_section

            # ── 1. CONTEXT-ONLY ELEMENTS (headings, sections) ─────────────────
            if etype in CONTEXT_TYPES:
                # Section boundary — flush current buffer
                new_section = elem.get("section_path") or current_section
                bc          = elem.get("heading_breadcrumb") or current_breadcrumb

                section_changed = (
                    new_section and
                    current_section and
                    new_section != current_section
                )

                if buffer and section_changed:
                    chunk_index = _flush_buffer(
                        buffer, chunks, chunk_index, document_id,
                        current_section, current_breadcrumb, current_heading,
                        is_overlap=buffer_is_overlap_start,
                        overlap_tokens=buffer_overlap_tokens,
                    )
                    # Last N elements become overlap carry for next chunk
                    overlap_carry  = buffer[-self.overlap_n:] if len(buffer) >= self.overlap_n else buffer[:]
                    buffer         = []
                    buffer_tokens  = 0
                    buffer_is_overlap_start = False
                    buffer_overlap_tokens   = 0

                # Update context state
                current_section    = new_section or current_section
                current_breadcrumb = bc or current_breadcrumb
                prev_section       = current_section

                if etype == "heading":
                    current_heading = (elem.get("content_original") or "")[:80]

                # Headings do NOT enter the buffer — they are context only
                continue

            # ── 2. TABLE ELEMENTS (always standalone) ─────────────────────────
            if etype in STANDALONE_TYPES:
                # Flush text buffer first
                if buffer:
                    chunk_index = _flush_buffer(
                        buffer, chunks, chunk_index, document_id,
                        current_section, current_breadcrumb, current_heading,
                        is_overlap=buffer_is_overlap_start,
                        overlap_tokens=buffer_overlap_tokens,
                    )
                    overlap_carry = []   # tables break overlap continuity
                    buffer        = []
                    buffer_tokens = 0
                    buffer_is_overlap_start = False
                    buffer_overlap_tokens   = 0

                # Build table chunk
                sc           = elem.get("structured_content") or {}
                nl_text      = sc.get("nl_representation") or elem.get("content_original") or ""
                table_md     = sc.get("markdown")
                table_lang   = elem.get("detected_language") or "en"
                table_tokens = _count_tokens(nl_text, table_lang)

                prefix  = _build_context_prefix(
                    elem.get("heading_breadcrumb") or current_breadcrumb,
                    elem.get("section_path") or current_section,
                    current_heading,
                )
                text_full = f"{prefix} {nl_text}".strip() if prefix else nl_text

                quality_score = elem.get("quality_score") or 1.0
                page_no = (
                    elem.get("metadata", {}).get("page_number") or
                    elem.get("page_number")
                )

                table_chunk = {
                    "chunk_id":         f"{document_id}_c{chunk_index:04d}",
                    "document_id":      document_id,
                    "text":             text_full,
                    "text_raw":         nl_text,
                    "table_markdown":   table_md,
                    "section_path":     elem.get("section_path") or current_section,
                    "breadcrumb":       list(elem.get("heading_breadcrumb") or current_breadcrumb),
                    "chunk_heading":    current_heading,
                    "element_ids":      [elem.get("element_id")] if elem.get("element_id") else [],
                    "page_range":       [page_no] if page_no else [],
                    "sequence_range":   [elem.get("sequence_order", 0)] * 2,
                    "element_types":    ["table"],
                    "is_table":         True,
                    "chunk_type":       "table",
                    "token_count":      _count_tokens(text_full, table_lang),
                    "detected_language": table_lang,
                    "min_quality_score": round(quality_score, 3),
                    "avg_quality_score": round(quality_score, 3),
                    "has_low_quality":   quality_score < LOW_QUALITY_THRESHOLD,
                    "has_overlap":       False,
                    "overlap_tokens":    0,
                }

                chunks.append(table_chunk)
                chunk_index += 1
                continue

            # ── 3. CONTENT ELEMENTS (clauses, paragraphs, etc.) ───────────────

            text    = (elem.get("content_original") or "").strip()
            # 🔥 NEW: Definition boundary enforcement
            if _is_definition(text):

                if buffer:
                    chunk_index = _flush_buffer(
                        buffer, chunks, chunk_index, document_id,
                        current_section, current_breadcrumb, current_heading,
                        is_overlap=buffer_is_overlap_start,
                        overlap_tokens=buffer_overlap_tokens,
                    )

                    overlap_carry = buffer[-self.overlap_n:] if len(buffer) >= self.overlap_n else buffer[:]

                    buffer = []
                    buffer_tokens = 0
                    buffer_is_overlap_start = False
                    buffer_overlap_tokens = 0
            lang    = elem.get("detected_language") or "en"
            e_tokens = _count_tokens(text, lang)

            # Single element too large — split it (rare edge case)
            if e_tokens > self.max_tokens - PREFIX_TOKEN_BUDGET:
                logger.warning(
                    f"Element {elem.get('element_id')} has {e_tokens} tokens "
                    f"(exceeds max). Splitting at sentence boundaries."
                )
                # Flush current buffer first
                if buffer:
                    chunk_index = _flush_buffer(
                        buffer, chunks, chunk_index, document_id,
                        current_section, current_breadcrumb, current_heading,
                        is_overlap=buffer_is_overlap_start,
                        overlap_tokens=buffer_overlap_tokens,
                    )
                    overlap_carry = buffer[-self.overlap_n:]
                    buffer        = []
                    buffer_tokens = 0
                    buffer_is_overlap_start = False
                    buffer_overlap_tokens   = 0

                segments = _split_long_text(text, self.max_tokens - PREFIX_TOKEN_BUDGET, lang)

                for seg_idx, seg in enumerate(segments):
                    seg_elem = dict(elem)
                    seg_elem["content_original"] = seg
                    seg_elem["element_id"]       = f"{elem.get('element_id', '')}_s{seg_idx}"

                    seg_chunk = _build_chunk(
                        buffer        = [seg_elem],
                        document_id   = document_id,
                        chunk_index   = chunk_index,
                        section_path  = current_section,
                        breadcrumb    = current_breadcrumb,
                        chunk_heading = current_heading,
                    )
                    if seg_chunk:
                        chunks.append(seg_chunk)
                        chunk_index += 1

                overlap_carry = []  # can't overlap across a forced split cleanly
                continue

            # ── Start buffer with overlap from previous chunk ─────────────────
            if overlap_carry and not buffer:
                buffer        = list(overlap_carry)
                buffer_tokens = sum(
                    _count_tokens(
                        e.get("content_original") or "",
                        e.get("detected_language") or "en"
                    )
                    for e in buffer
                )
                buffer_is_overlap_start = True
                buffer_overlap_tokens   = buffer_tokens
                overlap_carry = []

            # ── Buffer overflow: flush before adding this element ─────────────
            if buffer_tokens + e_tokens > self.max_tokens - PREFIX_TOKEN_BUDGET:
                # Flush at a clean clause boundary — the element itself is NOT in buffer yet
                prev_overlap = buffer[-self.overlap_n:] if len(buffer) >= self.overlap_n else buffer[:]

                chunk_index = _flush_buffer(
                    buffer, chunks, chunk_index, document_id,
                    current_section, current_breadcrumb, current_heading,
                    is_overlap=buffer_is_overlap_start,
                    overlap_tokens=buffer_overlap_tokens,
                )

                # Compute overlap token count for the next chunk's metadata
                overlap_tok = sum(
                    _count_tokens(
                        e.get("content_original") or "",
                        e.get("detected_language") or "en"
                    )
                    for e in prev_overlap
                )

                # Start new buffer with overlap + current element
                buffer                  = list(prev_overlap) + [elem]
                buffer_tokens           = overlap_tok + e_tokens
                buffer_is_overlap_start = len(prev_overlap) > 0
                buffer_overlap_tokens   = overlap_tok

                overlap_carry = []
                continue

            # ── Normal: add element to buffer ─────────────────────────────────
            buffer.append(elem)
            buffer_tokens += e_tokens
            # 🔥 NEW: Target-based flush (prevents over-merging)
            if buffer_tokens >= self.target_tokens:

                prev_overlap = buffer[-self.overlap_n:] if len(buffer) >= self.overlap_n else buffer[:]

                chunk_index = _flush_buffer(
                    buffer, chunks, chunk_index, document_id,
                    current_section, current_breadcrumb, current_heading,
                    is_overlap=buffer_is_overlap_start,
                    overlap_tokens=buffer_overlap_tokens,
                )

                # Prepare overlap for next chunk
                overlap_tok = sum(
                    _count_tokens(
                        e.get("content_original") or "",
                        e.get("detected_language") or "en"
                    )
                    for e in prev_overlap
                )

                buffer = list(prev_overlap)
                buffer_tokens = overlap_tok
                buffer_is_overlap_start = len(prev_overlap) > 0
                buffer_overlap_tokens = overlap_tok

                continue

        # ── Flush remaining buffer ────────────────────────────────────────────
        if buffer:
            chunk_index = _flush_buffer(
                buffer, chunks, chunk_index, document_id,
                current_section, current_breadcrumb, current_heading,
                is_overlap=buffer_is_overlap_start,
                overlap_tokens=buffer_overlap_tokens,
            )

        logger.info(
            f"Chunking complete: {len(elements)} elements → {len(chunks)} chunks "
            f"(document_id={document_id})"
        )

        return chunks

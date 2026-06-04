# app/utils/table_utils.py

"""
table_utils.py
────────────────────────────────────────────────────────────────────────────────
Table extraction, storage, and cross-page merging for Indian government PDFs.

TWO MAIN RESPONSIBILITIES
─────────────────────────

1. STORAGE SCHEMA (serialize_table)
   Converts a Docling TableData object into a rich structured dict that
   preserves everything Docling gives us: merged cells (row/col spans),
   separate header rows, section-separator rows, footnotes, and two
   ready-to-use text representations.

2. CROSS-PAGE MERGE (merge_cross_page_tables)
   Detects and merges tables that span across multiple pages.
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# TUNEABLE CONSTANTS
# ─────────────────────────────────────────────────────────────

CONTINUATION_SCORE_THRESHOLD = 3
BBOX_TOP_THRESHOLD = 150
BBOX_BOTTOM_THRESHOLD = 150
COL_WIDTH_TOLERANCE = 0.15


# ─────────────────────────────────────────────────────────────
# CELL CLEANING REGEX
# ─────────────────────────────────────────────────────────────

_PUNCT_ONLY_RE = re.compile(r"^[\s\:\-\,\;\|\/\\]+$")
_COLON_ONLY_RE = re.compile(r"^\s*:+\s*$")

_BLEED_STARTER_RE = re.compile(
    r"^(every\b|in accordance\b|should\b|of solid\b|of the\b|as may be\b"
    r"|unless\b|subject to\b|pursuant to\b|notwithstanding\b"
    r"|provided that\b|where\b|which\b|that\b|and\b|or\b|to\b)",
    re.IGNORECASE,
)

_NUMERIC_SECTION_RE = re.compile(r"^\d+(\.\d+)*[\.)]?")


# ─────────────────────────────────────────────────────────────
# CLEAN TABLE CELL TEXT
# ─────────────────────────────────────────────────────────────

def _clean_cell_text(text: str | None) -> str | None:
    """
    Clean a single table cell:
    • Remove border artifacts
    • Remove punctuation-only cells
    • Normalize whitespace
    """

    if not text:
        return None

    t = str(text).strip()

    # Remove vertical bars
    t = re.sub(r"\|+", " ", t)

    # Remove punctuation runs
    t = re.sub(r"\s*[:;,_\-]{2,}\s*", " ", t)

    # Normalize spaces
    t = re.sub(r"\s+", " ", t).strip()

    if not t:
        return None

    if _PUNCT_ONLY_RE.fullmatch(t):
        return None

    if _COLON_ONLY_RE.fullmatch(t):
        return None

    return t


# ─────────────────────────────────────────────────────────────
# REMOVE PARAGRAPH BLEED
# ─────────────────────────────────────────────────────────────

def _clean_cell_bleed(text: str | None) -> str | None:
    """
    Remove paragraph bleed from table cells.
    """

    if not text:
        return None

    t = text.strip()

    if _BLEED_STARTER_RE.match(t):

        sentences = re.split(r"(?<=[.!?])\s+", t)

        if len(sentences) > 1:
            return sentences[-1].strip() or None

        return None

    return t


# ─────────────────────────────────────────────────────────────
# EXTRACT FOOTNOTES
# ─────────────────────────────────────────────────────────────

def _extract_footnotes(rows_raw: list):

    footnotes = []
    footnote_re = re.compile(r"^\s*[\*†‡]\s*.{5,}", re.DOTALL)

    cleaned = []

    for row in rows_raw:

        new_row = []
        is_footnote_row = False

        for cell in row:

            if cell and footnote_re.match(str(cell)):

                footnotes.append(str(cell).strip())
                is_footnote_row = True

            else:

                new_row.append(cell)

        if not is_footnote_row:
            cleaned.append(row)

    return cleaned, footnotes

# ─────────────────────────────────────────────────────────────
# TABLE TYPE DETECTION
# ─────────────────────────────────────────────────────────────

def _detect_table_type(headers: list[list], rows: list[dict]) -> str:
    """
    Classify the table into one of four types:

    definition  → clause-number tables (4.1, 4.2 etc.)
    schedule    → regulatory schedules
    data        → mostly numeric tables
    mixed       → fallback
    """

    if not rows:
        return "mixed"

    # Combine all header text
    header_text = " ".join(
        cell or ""
        for header_row in headers
        for cell in header_row
    ).lower()

    # Schedule tables (common in government PDFs)
    if any(
        kw in header_text
        for kw in [
            "category",
            "colour",
            "color",
            "quantity",
            "penalty",
            "fine",
            "schedule",
            "annexure",
            "rate",
            "charge",
            "fee",
            "limit",
            "standard",
            "description",
            "item",
        ]
    ):
        return "schedule"

    # Detect definition tables (4.1, 4.2 style numbering)
    first_col_values = []

    for row in rows:
        if row.get("cells"):
            first_cell = row["cells"][0].get("text", "") or ""
            first_col_values.append(first_cell.strip())

    definition_count = sum(
        1 for v in first_col_values
        if re.match(r"^\d+\.\d+", v)
    )

    if definition_count >= max(2, len(first_col_values) * 0.5):
        return "definition"

    # Detect numeric data tables
    all_cell_texts = [
        cell.get("text", "") or ""
        for row in rows
        for cell in row.get("cells", [])
    ]

    numeric_cells = sum(
        1 for t in all_cell_texts
        if re.fullmatch(r"[\d,.\s%]+", t.strip())
    )

    if all_cell_texts and numeric_cells / len(all_cell_texts) > 0.4:
        return "data"

    return "mixed"


# ─────────────────────────────────────────────────────────────
# NATURAL LANGUAGE REPRESENTATION
# ─────────────────────────────────────────────────────────────

def _build_nl_representation(headers, rows, table_type):
    """
    Convert structured table rows into a flat text string
    suitable for embeddings in vector databases.
    """

    if not rows:
        return ""

    col_labels = []

    if headers:

        num_cols = max(len(r) for r in headers)
        col_labels = [None] * num_cols

        for header_row in headers:

            for i, cell in enumerate(header_row):

                if cell and not col_labels[i]:
                    col_labels[i] = cell

                elif cell:
                    col_labels[i] = f"{col_labels[i]} / {cell}"

    parts = []

    for row in rows:

        if row.get("is_section_separator"):
            continue

        cells = row.get("cells", [])

        if table_type == "definition":

            cell_texts = [
                c.get("text") for c in cells if c.get("text")
            ]

            if cell_texts:
                parts.append(", ".join(str(t) for t in cell_texts))

        else:

            row_parts = []

            for cell in cells:

                col_i = cell.get("col_idx", 0)
                val = cell.get("text")

                if not val:
                    continue

                label = (
                    col_labels[col_i]
                    if col_labels and col_i < len(col_labels)
                    else None
                )

                if label and label != ":":
                    row_parts.append(f"{label}: {val}")

                else:
                    row_parts.append(str(val))

            if row_parts:
                parts.append(", ".join(row_parts))

    return "; ".join(parts)


# ─────────────────────────────────────────────────────────────
# MARKDOWN BUILDER
# ─────────────────────────────────────────────────────────────

def _build_markdown(headers, rows, num_cols):
    """
    Build markdown table representation.
    This is used when sending table context to an LLM.
    """

    lines = []

    # Header rows
    for header_row in headers:

        padded = list(header_row) + [None] * (num_cols - len(header_row))
        cells = [str(c) if c else "" for c in padded]

        lines.append("| " + " | ".join(cells) + " |")

    # Markdown separator
    lines.append("|" + "|".join(["---"] * num_cols) + "|")

    # Data rows
    for row in rows:

        if row.get("is_section_separator"):
            lines.append("|" + "|".join(["---"] * num_cols) + "|")
            continue

        grid = [""] * num_cols

        for cell in row.get("cells", []):

            col_i = cell.get("col_idx", 0)
            col_span = cell.get("col_span", 1)
            text = str(cell.get("text") or "")

            for k in range(col_span):

                if col_i + k < num_cols:
                    grid[col_i + k] = text if k == 0 else f"↓{text}"

        lines.append("| " + " | ".join(grid) + " |")

    return "\n".join(lines)

# ─────────────────────────────────────────────────────────────
# MAIN SERIALIZER
# ─────────────────────────────────────────────────────────────

def serialize_table(
    table_data: Any,
    table_id: str = "",
    source_page: int | None = None,
    section_path: str | None = None,
) -> dict | None:
    """
    Convert a Docling TableData object into the structured storage format.

    Args:
        table_data: Docling table_data object
        table_id: optional identifier
        source_page: page number where table was found
        section_path: section heading context

    Returns:
        Structured table dictionary or None
    """

    if not table_data:
        return None

    try:

        num_rows = table_data.num_rows
        num_cols = table_data.num_cols

        header_rows = []
        data_rows = []
        footnotes = []

        covered = set()

        for row_i, row in enumerate(table_data.grid):

            is_header = False
            is_section_sep = False
            row_cells = []

            for col_i, cell in enumerate(row):

                if (row_i, col_i) in covered:
                    continue

                if cell is None:
                    continue

                is_header = is_header or bool(
                    getattr(cell, "column_header", False)
                )

                is_section_sep = is_section_sep or bool(
                    getattr(cell, "row_section", False)
                )

                raw_text = getattr(cell, "text", None)

                text = _clean_cell_text(raw_text)
                text = _clean_cell_bleed(text)

                row_span = max(1, getattr(cell, "row_span", 1))
                col_span = max(1, getattr(cell, "col_span", 1))

                # Mark grid cells covered by span
                for dr in range(row_span):
                    for dc in range(col_span):
                        covered.add((row_i + dr, col_i + dc))

                # Detect footnotes
                if text and re.match(r"^\s*[\*†‡]", text):
                    footnotes.append(text)
                    continue

                if is_section_sep:
                    continue

                row_cells.append({
                    "col_idx": col_i,
                    "text": text,
                    "row_span": row_span,
                    "col_span": col_span
                })

            # Classify row
            if is_section_sep:

                data_rows.append({
                    "row_idx": row_i,
                    "is_section_separator": True,
                    "cells": []
                })

            elif is_header:

                header_rows.append(
                    [c.get("text") for c in row_cells]
                )

            else:

                if any(c.get("text") for c in row_cells):

                    data_rows.append({
                        "row_idx": row_i,
                        "is_section_separator": False,
                        "cells": row_cells
                    })

        table_type = _detect_table_type(header_rows, data_rows)

        nl_repr = _build_nl_representation(
            header_rows,
            data_rows,
            table_type
        )

        markdown = _build_markdown(
            header_rows,
            data_rows,
            num_cols
        )

        return {
            "table_id": table_id or f"table_p{source_page}_{id(table_data)}",
            "is_continuation": False,
            "continuation_of": None,
            "num_rows": len(data_rows),
            "num_cols": num_cols,
            "num_header_rows": len(header_rows),
            "headers": header_rows,
            "rows": data_rows,
            "nl_representation": nl_repr,
            "markdown": markdown,
            "footnotes": footnotes,
            "source_pages": [source_page] if source_page else [],
            "section_path": section_path,
            "table_type": table_type
        }

    except Exception as exc:

        logger.warning(f"Table serialization failed: {exc}")

        return None


# ─────────────────────────────────────────────────────────────
# CROSS PAGE TABLE MERGING HELPERS
# ─────────────────────────────────────────────────────────────

def _is_vertically_aligned(elem_a, elem_b):
    bbox_a = _normalize_bbox(elem_a.get("source_location", {}).get("bbox"))
    bbox_b = _normalize_bbox(elem_b.get("source_location", {}).get("bbox"))

    if not bbox_a or not bbox_b:
        return False

    # B should start AFTER A ends (true continuation)
    return bbox_b["top"] >= bbox_a["bottom"]

def _normalize_bbox(bbox):
    if not bbox:
        return None

    top = bbox.get("top")
    bottom = bbox.get("bottom")

    if top is None or bottom is None:
        return None

    # Fix inverted coordinate system
    y_min = min(top, bottom)
    y_max = max(top, bottom)

    return {
        "top": y_min,
        "bottom": y_max
    }

def _is_bottom_heavy(elem):
    bbox = elem.get("source_location", {}).get("bbox")
    bbox = _normalize_bbox(bbox)

    if not bbox:
        return False

    return bbox["bottom"] > 700

def _is_top_heavy(elem):
    bbox = elem.get("source_location", {}).get("bbox")
    bbox = _normalize_bbox(bbox)

    if not bbox:
        return False

    return bbox["top"] < 200

def _has_header_rows(structured_content: dict) -> bool:

    return bool(structured_content.get("headers"))


def _get_last_sr_no(structured_content: dict):

    rows = structured_content.get("rows", [])

    for row in reversed(rows):

        if row.get("is_section_separator"):
            continue

        cells = row.get("cells", [])

        if cells:

            text = cells[0].get("text", "") or ""

            m = re.match(r"^(\d+)", text.strip())

            if m:
                return int(m.group(1))

    return None


def _get_first_sr_no(structured_content: dict):

    rows = structured_content.get("rows", [])

    for row in rows:

        if row.get("is_section_separator"):
            continue

        cells = row.get("cells", [])

        if cells:

            text = cells[0].get("text", "") or ""

            m = re.match(r"^(\d+)", text.strip())

            if m:
                return int(m.group(1))

    return None


# ─────────────────────────────────────────────────────────────
# TABLE MERGE LOGIC
# ─────────────────────────────────────────────────────────────

def _merge_two_tables(elem_a, elem_b):

    sc_a = elem_a["structured_content"]
    sc_b = elem_b["structured_content"]

    rows_a = sc_a.get("rows", [])
    rows_b = sc_b.get("rows", [])

    sc_a["rows"] = rows_a + rows_b
    
    sc_a["num_rows"] = len(sc_a["rows"])
    
    # Merge source pages (VERY IMPORTANT)
    sc_a["source_pages"].extend(sc_b.get("source_pages", []))

    # Remove duplicates + keep order
    sc_a["source_pages"] = list(dict.fromkeys(sc_a["source_pages"]))
    
    # Mark continuation relationship
    sc_b["is_continuation"] = True
    sc_b["continuation_of"] = sc_a.get("table_id")

    sc_a["nl_representation"] = _build_nl_representation(
        sc_a.get("headers", []),
        sc_a["rows"],
        sc_a.get("table_type", "mixed"),
    )

    sc_a["markdown"] = _build_markdown(
        sc_a.get("headers", []),
        sc_a["rows"],
        sc_a.get("num_cols", 1),
    )

    elem_a["content_original"] = sc_a["nl_representation"]
    elem_a["token_count"] = len(sc_a["nl_representation"].split())

    return elem_a


# ─────────────────────────────────────────────────────────────
# CROSS PAGE MERGER
# ─────────────────────────────────────────────────────────────
def merge_cross_page_tables(elements):
    """
    Merge tables that span multiple pages.
    """

    changed = True

    while changed:

        changed = False
        skip = set()

        tables = [
            i for i, e in enumerate(elements)
            if e.get("element_type") == "table"
        ]

        tables = [
            (i, e) for i, e in enumerate(elements)
            if e.get("element_type") == "table"
        ]

        for ti in range(len(tables) - 1):

            idx_a, elem_a = tables[ti]
            idx_b, elem_b = tables[ti + 1]

            if idx_b in skip:
                continue

            page_a = elem_a.get("metadata", {}).get("page_number")
            page_b = elem_b.get("metadata", {}).get("page_number")

            sc_a = elem_a.get("structured_content", {})
            sc_b = elem_b.get("structured_content", {})

            # -----------------------------
            # STRICT PAGE CONTINUITY CHECK
            # -----------------------------
            if not page_a or not page_b:
                continue

            if page_b != page_a + 1:
                continue

            if sc_a.get("num_cols") != sc_b.get("num_cols"):
                continue

            last_sr = _get_last_sr_no(sc_a)
            first_sr = _get_first_sr_no(sc_b)

            score = 0
            
            # 🚫 HARD BLOCKS (only real contradictions)
            # 1. Serial reset (VERY STRONG reject)
            if last_sr and first_sr and first_sr <= last_sr:
                continue

            # 2. Header mismatch (VERY STRONG reject)
            if _has_header_rows(sc_a) and _has_header_rows(sc_b):
                headers_a = sc_a.get("headers", [])
                headers_b = sc_b.get("headers", [])

                if headers_a and headers_b and headers_a[0] != headers_b[0]:
                    continue
            
            # ---------------------------------------
            # 3.Layout alignment (ROBUST FIX)
            # ---------------------------------------
            if _is_vertically_aligned(elem_a, elem_b):
                score += 2
            
            # Same column structure (extra signal)
            if sc_a.get("num_cols") == sc_b.get("num_cols"):
                score += 1
                
            # ---------------------------------------
            # 4. No-header continuation (CRITICAL FIX)
            # ---------------------------------------
            if not _has_header_rows(sc_b):
                score += 1
                
            # Close vertical gap → strong continuation
            gap = abs(
                _normalize_bbox(elem_b["source_location"]["bbox"])["top"]
                - _normalize_bbox(elem_a["source_location"]["bbox"])["bottom"]
            )

            if gap < 400:
                score += 2
                
            normA = _normalize_bbox(elem_a.get("source_location", {}).get("bbox"))
            normB = _normalize_bbox(elem_b.get("source_location", {}).get("bbox"))

            logger.info(
                f"[MERGE CHECK] pages: {page_a}->{page_b} | "
                f"score={score} | "
                f"cols={sc_a.get('num_cols')} | "
                f"sr=({last_sr}->{first_sr}) | "
                f"headerA={_has_header_rows(sc_a)} headerB={_has_header_rows(sc_b)} | "
                f"normA={normA} normB={normB}"
            )

            if score >= CONTINUATION_SCORE_THRESHOLD:

                logger.info(
                    f"Merging cross-page tables page {page_a} + {page_b}"
                )

                _merge_two_tables(elem_a, elem_b)

                skip.add(idx_b)

                changed = True

        elements = [
            e for i, e in enumerate(elements)
            if i not in skip
        ]

    # Renumber sequence order
    for i, elem in enumerate(elements):
        elem["sequence_order"] = i

    return elements

# ─────────────────────────────────────────────────────────────
# STATISTICAL TABLE DETECTION (NON-INTRUSIVE ADDITION)
# ─────────────────────────────────────────────────────────────

def is_statistical_table_text(text: str) -> bool:
    """
    Detect if text is likely a statistical/numeric-heavy table.

    This does NOT affect existing table logic.
    It is only used by the PDF extractor for timeout decisions.
    """

    if not text:
        return False

    total_chars = len(text)

    if total_chars == 0:
        return False

    digit_count = sum(c.isdigit() for c in text)

    ratio = digit_count / total_chars

    # Heuristic threshold (safe default)
    return ratio > 0.35
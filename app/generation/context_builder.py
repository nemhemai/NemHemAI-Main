# app/generation/context_builder.py

import re


# 🎯 Generic patterns (domain-independent)
ENTITY_PATTERN = re.compile(r'\b([A-Z]{2,}\d*\.?\d*)\b')

VALUE_PATTERN = re.compile(
    r'(\d+(?:[\.\-–]\d+)*\s*(?:µg/m3|mg/m3|ppm|ppb|%|₹|rs\.?|crore|lakh)?)',
    re.IGNORECASE
)

def filter_relevant_sentences(text: str, query: str) -> str:
    """
    Keeps only sentences relevant to query keywords
    """

    query_words = set(re.findall(r'\b\w+\b', query.lower()))

    sentences = re.split(r'(?<=[.!?])\s+', text)

    filtered = []

    for sent in sentences:
        sent_words = set(re.findall(r'\b\w+\b', sent.lower()))

        # keep sentence if overlap exists
        if len(query_words & sent_words) > 0:
            filtered.append(sent.strip())

    return " ".join(filtered[:5])  # limit size

def extract_structured_lines(text: str) -> list[str]:
    """
    Extract entity-value pairs for numeric queries
    """

    lines = []

    sentences = re.split(r'(?<=[.!?])\s+', text)

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        entities = ENTITY_PATTERN.findall(sent)
        values = VALUE_PATTERN.findall(sent)

        if not entities or not values:
            continue

        # 🔥 pick first entity + most relevant value
        entity = entities[0]

        # prefer range value
        selected_value = None
        for v in values:
            if "-" in v or "–" in v:
                selected_value = v
                break

        if not selected_value:
            selected_value = values[0]

        lines.append(f"{entity}: {selected_value}")

    return lines


def build_context(chunks: list[dict], query_analysis: dict) -> str:
    """
    Adaptive context builder
    """

    query_type = query_analysis.get("query_type", "mixed")

    formatted_blocks = []

    for i, chunk in enumerate(chunks, 1):

        text = chunk.get("text", "")
        section = chunk.get("section_path")

        # ─────────────────────────────────────────────────────────────
        # 🔢 STRUCTURED MODE (NUMERIC QUERIES)
        # ─────────────────────────────────────────────────────────────
        if query_type == "numeric": 

            structured_lines = extract_structured_lines(text)

            if structured_lines:
                block = f"""
[Source {i}]
Section: {section}
Data:
{chr(10).join(structured_lines)}
"""
            else:
                # fallback
                block = f"""
[Source {i}]
Section: {section}
Content:
{text[:500]}
"""

        # ─────────────────────────────────────────────────────────────
        # 📄 RAW MODE (ALL OTHER QUERIES)
        # ─────────────────────────────────────────────────────────────
        else:
            block = f"""
[Source {i}]
Section: {section}
Content:
{text[:800]}
"""

        formatted_blocks.append(block.strip())

    return "\n\n".join(formatted_blocks)
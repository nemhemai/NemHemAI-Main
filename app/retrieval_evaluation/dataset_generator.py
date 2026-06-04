# app/retrieval_evaluation/dataset_generator.py

import random
import re
from collections import defaultdict
import json
import os


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1 — FETCH CHUNKS (BALANCED ACROSS DOCUMENTS)
# ──────────────────────────────────────────────────────────────────────────────

def fetch_chunks_per_document(conn, per_doc_limit=20):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT document_id FROM document_chunks")
        doc_ids = [r[0] for r in cur.fetchall()]

    all_chunks = []

    for doc_id in doc_ids:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT chunk_id, document_id, text, chunk_heading,
                       section_path, is_table, min_quality_score
                FROM document_chunks
                WHERE document_id = %s
                  AND min_quality_score >= 0.7
                ORDER BY random()
                LIMIT %s
            """, (doc_id, per_doc_limit))

            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]

            for r in rows:
                all_chunks.append(dict(zip(cols, r)))

    return all_chunks


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2 — STOPWORDS
# ──────────────────────────────────────────────────────────────────────────────

STOPWORDS = {
    "the", "is", "in", "of", "for", "to", "and", "or", "on", "with", "by",
    "what", "which", "this", "that", "are", "from", "will", "shall",
    "section", "rule", "note", "notes"
}


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3 — CHUNK FILTER
# ──────────────────────────────────────────────────────────────────────────────

def is_valid_chunk(chunk):
    section = (chunk.get("section_path") or "").lower()
    heading = (chunk.get("chunk_heading") or "").lower()

    if any(x in section for x in ["annexure", "appendix", "index"]):
        return False

    if heading and len(heading.split()) < 2:
        return False

    return True


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4 — OCR NOISE FILTER
# ──────────────────────────────────────────────────────────────────────────────

def is_clean_text(text):
    words = text.split()
    bad_tokens = [w for w in words if not re.match(r"^[a-z]+$", w)]

    return len(bad_tokens) <= len(words) * 0.4


# ──────────────────────────────────────────────────────────────────────────────
# STEP 5 — NORMALIZE WORDS (NEW FIX)
# ──────────────────────────────────────────────────────────────────────────────

def normalize_words(words):
    normalized = []
    seen_roots = set()

    for w in words:
        root = w.rstrip("s")  # handle plural duplication

        if root not in seen_roots:
            normalized.append(w)
            seen_roots.add(root)

    return normalized


# ──────────────────────────────────────────────────────────────────────────────
# STEP 6 — TERM EXTRACTION (FINAL FIXED)
# ──────────────────────────────────────────────────────────────────────────────

def extract_term(chunk):
    text = chunk.get("chunk_heading") or chunk.get("text", "")
    text = text.lower()

    text = re.sub(r"[^a-z0-9\s]", " ", text)

    words = [
        w for w in text.split()
        if len(w) > 3 and w not in STOPWORDS
    ]

    # Remove meaningless tokens
    words = [
        w for w in words
        if w not in {"means", "include", "includes"}
    ]

    # Remove duplicates
    words = list(dict.fromkeys(words))

    # ✅ NEW: normalize plurals
    words = normalize_words(words)

    if len(words) < 2:
        return None

    return " ".join(words[:3])


# ──────────────────────────────────────────────────────────────────────────────
# STEP 7 — TERM VALIDATION (FINAL)
# ──────────────────────────────────────────────────────────────────────────────

def is_valid_term(term):
    words = term.split()

    if len(words) < 2:
        return False

    numeric_ratio = sum(w.isdigit() for w in words) / len(words)
    if numeric_ratio > 0.4:
        return False

    if any(w.isdigit() and len(w) == 4 for w in words):
        return False

    if len(set(words)) < len(words) * 0.7:
        return False

    # reject incomplete phrases
    if term.endswith(("under", "within", "towards", "includes")):
        return False

    # weak combinations
    bad_combinations = [
        "duties responsibilities",
        "measures taken",
        "following servicer",
    ]

    for bc in bad_combinations:
        if bc in term:
            return False

    return True


# ──────────────────────────────────────────────────────────────────────────────
# STEP 8 — SEMANTIC FILTER (FINAL FIX)
# ──────────────────────────────────────────────────────────────────────────────

def is_semantically_meaningful(term):
    bad_words = {
        "here", "stay", "impact",
        "things", "various", "some"
    }

    words = term.split()

    if any(w in bad_words for w in words):
        return False

    if len(words) <= 2 and any(w in ["process", "system"] for w in words):
        return False

    return True


# ──────────────────────────────────────────────────────────────────────────────
# STEP 9 — TYPE DETECTION
# ──────────────────────────────────────────────────────────────────────────────

def detect_chunk_type(chunk):
    text = (chunk.get("text") or "").lower()

    if chunk.get("is_table"):
        return "table"

    if any(x in text[:200] for x in ["means", "definition", "refers to"]):
        return "definition"

    if any(x in text for x in [
        "penalty", "fine", "punishable",
        "non-compliance", "violation"
    ]):
        return "enforcement"

    return "general"


# ──────────────────────────────────────────────────────────────────────────────
# STEP 10 — TABLE VALIDATION (STRICT)
# ──────────────────────────────────────────────────────────────────────────────

def is_valid_table(chunk):
    text = (chunk.get("text") or "").lower()

    has_number = any(char.isdigit() for char in text)

    has_pattern = any(x in text for x in [
        "per day", "per year", "per month",
        "maximum", "minimum", "range", "limit"
    ])

    return has_number and has_pattern


# ──────────────────────────────────────────────────────────────────────────────
# STEP 11 — QUERY TEMPLATES
# ──────────────────────────────────────────────────────────────────────────────

QUERY_TEMPLATES = {
    "definition": [
        "What is {term}?",
        "Define {term}",
        "What does {term} mean?"
    ],
    "enforcement": [
        "What is the penalty for {term}?",
        "What happens if {term} is not followed?",
        "Action for violation of {term}"
    ],
    "table": [
        "What are the limits for {term}?",
        "What values are defined for {term}?",
        "How much {term} is allowed?"
    ],
    "general": [
        "Explain {term}",
        "What are the guidelines for {term}?",
        "What is the process for {term}?"
    ]
}


# ──────────────────────────────────────────────────────────────────────────────
# STEP 12 — QUERY VALIDATION
# ──────────────────────────────────────────────────────────────────────────────

def is_valid_query(query):
    q = query.lower()

    if len(q.split()) < 4:
        return False

    words = q.split()

    if len(set(words)) < len(words) * 0.7:
        return False

    if any(x in q for x in ["means means", "what what"]):
        return False

    return True


# ──────────────────────────────────────────────────────────────────────────────
# STEP 13 — MAIN PIPELINE
# ──────────────────────────────────────────────────────────────────────────────

def generate_dataset(conn, per_doc_limit=20):
    chunks = fetch_chunks_per_document(conn, per_doc_limit)

    dataset = []

    for chunk in chunks:

        if not is_valid_chunk(chunk):
            continue

        term = extract_term(chunk)

        if not term or not is_valid_term(term):
            continue

        if not is_semantically_meaningful(term):
            continue

        if not is_clean_text(term):
            continue

        if chunk.get("is_table"):
            if not is_valid_table(chunk):
                continue
            qtype = "table"
        else:
            qtype = detect_chunk_type(chunk)

        template = random.choice(QUERY_TEMPLATES[qtype])
        query = template.format(term=term)

        # grammar fixes
        query = query.replace("means mean", "mean")
        query = query.replace("means means", "mean")

        # remove duplicate words
        query_words = query.split()
        query = " ".join(dict.fromkeys(query_words))

        # fix plural duplication artifacts
        query = query.replace("waste wastes", "waste")
        query = query.replace("collection collecting", "collection")

        if not is_valid_query(query):
            continue

        dataset.append({
            "query": query,
            "type": qtype,
            "expected_keywords": [
                w for w in term.split() if len(w) > 3
            ][:3],
            "expected_sections": [
                (chunk.get("section_path") or "")[:25]
            ],
            "relevant_chunk_ids": [chunk["chunk_id"]],
            "relevance_type": "weak",
            "document_id": chunk["document_id"]
        })

    return dataset


# ──────────────────────────────────────────────────────────────────────────────
# STEP 14 — CLEAN DATASET
# ──────────────────────────────────────────────────────────────────────────────

def clean_dataset(dataset):
    seen = set()
    cleaned = []

    for d in dataset:
        q = d["query"].strip().lower()

        if len(q) < 10:
            continue

        if q in seen:
            continue

        seen.add(q)
        cleaned.append(d)

    return cleaned


# ──────────────────────────────────────────────────────────────────────────────
# STEP 15 — BALANCE DATASET
# ──────────────────────────────────────────────────────────────────────────────

def balance_dataset(dataset, per_type_limit=25):
    buckets = defaultdict(list)

    for d in dataset:
        buckets[d["type"]].append(d)

    final = []

    for t in ["definition", "enforcement", "general", "table"]:
        items = buckets.get(t, [])
        random.shuffle(items)
        final.extend(items[:per_type_limit])

    return final


# ──────────────────────────────────────────────────────────────────────────────
# STEP 16 — SAVE DATASET
# ──────────────────────────────────────────────────────────────────────────────

def save_dataset(dataset, path="app/evaluation/evaluation_dataset.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
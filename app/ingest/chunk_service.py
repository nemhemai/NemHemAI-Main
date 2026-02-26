# app/ingestion/chunk_service.py

from typing import List, Dict
from app.utils.id_generator import generate_chunk_id


MAX_CHUNK_SIZE = 50  # characters per chunk
CHUNK_OVERLAP = 10    # overlap characters


def split_text(text: str, max_size: int, overlap: int):
    """
    Safe overlapping chunk splitter.
    """

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + max_size
        if end >= text_length:
            chunks.append(text[start:text_length])
            break

        chunks.append(text[start:end])

        start = end - overlap

    return chunks


def prepare_chunks(structured_json: Dict) -> List[Dict]:
    """
    Converts structured sections into chunk-ready objects.
    No persistence. No embeddings.
    """

    act_id = structured_json["act_id"]
    sections = structured_json["sections"]

    chunk_records = []

    for section in sections:

        section_id = section["section_id"]
        content = section["content"]

        if not content or not content.strip():
            continue

        text_chunks = split_text(
            text=content,
            max_size=MAX_CHUNK_SIZE,
            overlap=CHUNK_OVERLAP
        )

        for chunk_text in text_chunks:

            chunk_id = generate_chunk_id(section_id)

            chunk_records.append({
                "chunk_id": chunk_id,
                "act_id": act_id,
                "section_id": section_id,
                "text": chunk_text
            })

    return chunk_records
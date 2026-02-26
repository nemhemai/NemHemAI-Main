# app/ingestion/persistence_service.py

from app.ingest.graph_ingestor import persist_structured_json
from app.ingest.chunk_service import prepare_chunks


def validate_structured_json(data: dict):
    """
    Minimal structural validation before persistence.
    Extraction layer remains source-of-truth.
    """

    required_root_fields = ["act_id", "act_title", "sections"]

    for field in required_root_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(data["sections"], list) or len(data["sections"]) == 0:
        raise ValueError("Sections must be a non-empty list.")

    seen_section_ids = set()

    for section in data["sections"]:
        required_section_fields = ["section_id", "heading", "content"]

        for field in required_section_fields:
            if field not in section:
                raise ValueError(f"Missing section field: {field}")

        if section["section_id"] in seen_section_ids:
            raise ValueError("Duplicate section_id detected in payload.")

        seen_section_ids.add(section["section_id"])


def persist_to_graph(structured_json: dict):
    """
    Orchestrates validation + graph ingestion.
    """

    # 1. Validate structure
    validate_structured_json(structured_json)

    # 2. Persist using atomic graph layer
    summary = persist_structured_json(structured_json)
    
    # Prepare chunks (no storage yet)
    chunks = prepare_chunks(structured_json)

    summary["chunks_prepared"] = len(chunks)

    return summary


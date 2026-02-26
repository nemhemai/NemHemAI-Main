# app/ingestion/graph_ingestor.py

from app.graph.connection import driver
from app.graph.queries import (
    upsert_act,
    upsert_section,
    create_has_section
)


def _ingest_transaction(tx, structured_json):
    """
    Runs FULL ingestion inside a single Neo4j transaction.
    If any step fails → entire transaction rolls back.
    """

    act_id = structured_json["act_id"]
    act_title = structured_json["act_title"]
    sections = structured_json["sections"]

    # 1. Upsert Act
    upsert_act(tx, act_id, act_title)

    # 2. Upsert Sections + Relationships
    for section in sections:
        section_payload = {
            "section_id": section["section_id"],
            "heading": section["heading"],
            "content": section["content"],
            "act_id": act_id
        }

        upsert_section(tx, section_payload)
        create_has_section(tx, act_id, section["section_id"])


def persist_structured_json(structured_json):
    """
    Public ingestion entry point.
    Ensures atomic write behavior.
    """

    summary = {
        "acts_processed": 1,
        "sections_processed": len(structured_json["sections"]),
        "relationships_created": len(structured_json["sections"])
    }

    with driver.session() as session:
        session.execute_write(_ingest_transaction, structured_json)

    return summary
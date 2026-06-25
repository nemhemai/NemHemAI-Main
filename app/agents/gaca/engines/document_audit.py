"""4.4 Document Audit Engine - visibility into document processing activities.

Tracks: upload, OCR, field extraction, verification result, tampering, history.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.gaca.models import Document


def record_document(db: Session, **fields) -> Document:
    row = Document(
        document_id=fields["document_id"],
        citizen_id=fields.get("citizen_id"),
        document_type=fields.get("document_type"),
        verification_status=fields.get("verification_status"),
        extracted_data=fields.get("extracted_data"),
        verification_results=fields.get("verification_results"),
        anomaly_indicators=fields.get("anomaly_indicators"),
    )
    db.merge(row)
    db.commit()
    return db.get(Document, fields["document_id"])


def update_verification(db: Session, document_id: str, status: str,
                        results: dict | None = None, anomalies: dict | None = None) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise ValueError("document not found")
    doc.verification_status = status
    if results is not None:
        doc.verification_results = results
    if anomalies is not None:
        doc.anomaly_indicators = anomalies
    db.commit()
    return doc


def document_history(db: Session, citizen_id: str) -> list[Document]:
    return db.execute(
        select(Document).where(Document.citizen_id == citizen_id)
        .order_by(Document.upload_date.desc())
    ).scalars().all()

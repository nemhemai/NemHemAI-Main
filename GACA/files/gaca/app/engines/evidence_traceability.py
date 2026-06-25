"""4.3 Evidence Traceability Engine - relationships between decisions and evidence.

Shows exactly how a document influenced a decision, e.g.
Income Certificate -> Income Verification -> Eligibility Rule Evaluation -> PMAY.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, Evidence


def link_evidence(db: Session, decision_id: str, document_id: str, role: str) -> Evidence:
    row = Evidence(decision_id=decision_id, document_id=document_id, role=role)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def evidence_chain(db: Session, decision_id: str) -> list[dict]:
    """The ordered chain of documents that supported a decision."""
    links = db.execute(
        select(Evidence).where(Evidence.decision_id == decision_id)
    ).scalars().all()
    chain = []
    for link in links:
        doc = db.get(Document, link.document_id)
        chain.append({
            "document_id": link.document_id,
            "document_type": doc.document_type if doc else None,
            "verification_status": doc.verification_status if doc else None,
            "role": link.role,
        })
    return chain

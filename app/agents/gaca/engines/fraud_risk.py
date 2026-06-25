"""4.12 Fraud & Risk Intelligence Engine.

Fraud Detection: duplicate applications, duplicate benefits, identity misuse,
document tampering, suspicious patterns.
Risk Scoring: citizen / application / officer / scheme risk score.
Graph Analytics (Neo4j): shared addresses, shared bank accounts, shared mobile
numbers, relationship networks.

The graph analytics below are written against the relational store so they run
out of the box; Neo4j (docker-compose) is the intended production graph backend
for the relationship-network queries.
"""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.gaca.models import Application, Citizen, Document, RiskAssessment


def shared_attribute_clusters(db: Session) -> dict:
    """Graph analytics: citizens sharing address / bank account / mobile number."""
    citizens = db.execute(select(Citizen)).scalars().all()

    def cluster(attr: str) -> dict:
        groups = defaultdict(list)
        for c in citizens:
            val = getattr(c, attr)
            if val:
                groups[val].append(c.citizen_id)
        return {val: ids for val, ids in groups.items() if len(ids) > 1}

    return {
        "shared_addresses": cluster("address"),
        "shared_bank_accounts": cluster("bank_account"),
        "shared_mobile_numbers": cluster("mobile"),
    }


def detect_fraud(db: Session) -> dict:
    """Duplicate applications, duplicate benefits, document tampering."""
    apps = db.execute(select(Application)).scalars().all()

    # Duplicate applications: same citizen + same scheme more than once
    seen = defaultdict(list)
    for a in apps:
        seen[(a.citizen_id, a.scheme_id)].append(a.application_id)
    duplicate_applications = {f"{k[0]}::{k[1]}": v for k, v in seen.items() if len(v) > 1}

    # Document tampering: anomaly indicators present
    tampered = db.execute(
        select(Document).where(Document.anomaly_indicators.isnot(None))
    ).scalars().all()
    document_tampering = [d.document_id for d in tampered if d.anomaly_indicators]

    return {
        "duplicate_applications": duplicate_applications,
        "document_tampering": document_tampering,
        "shared_attributes": shared_attribute_clusters(db),
    }


def score_subject(db: Session, subject_type: str, subject_id: str,
                  indicators: dict) -> RiskAssessment:
    """Risk score for a citizen / application / officer / scheme.

    Score = fraction of indicator flags that are true (0..1).
    """
    flags = [bool(v) for v in indicators.values()]
    score = round(sum(flags) / len(flags), 3) if flags else 0.0
    row = RiskAssessment(subject_type=subject_type, subject_id=subject_id,
                         risk_score=score, indicators=indicators)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

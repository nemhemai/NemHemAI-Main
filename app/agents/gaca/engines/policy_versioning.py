"""4.2 Policy Versioning Engine - version history of policies, regulations, scheme rules.

Benefit: historical decision reconstruction and policy traceability.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.gaca.models import Policy


def add_policy_version(db: Session, **fields) -> Policy:
    row = Policy(
        policy_id=fields["policy_id"],
        policy_name=fields["policy_name"],
        circular_number=fields.get("circular_number"),
        rule_version=fields.get("rule_version"),
        effective_date=fields.get("effective_date"),
        expiry_date=fields.get("expiry_date"),
        issuing_authority=fields.get("issuing_authority"),
    )
    db.merge(row)
    db.commit()
    return db.get(Policy, fields["policy_id"])


def policy_as_of(db: Session, policy_name: str, as_of: datetime) -> Policy | None:
    """The version of a policy that was effective on a given date.

    Enables historical decision reconstruction (the engine's stated benefit).
    """
    rows = db.execute(
        select(Policy).where(Policy.policy_name == policy_name)
        .order_by(Policy.effective_date.desc())
    ).scalars().all()
    for p in rows:
        eff_ok = p.effective_date is None or p.effective_date <= as_of
        exp_ok = p.expiry_date is None or p.expiry_date >= as_of
        if eff_ok and exp_ok:
            return p
    return None


def list_versions(db: Session, policy_name: str) -> list[Policy]:
    return db.execute(
        select(Policy).where(Policy.policy_name == policy_name)
        .order_by(Policy.effective_date.asc())
    ).scalars().all()

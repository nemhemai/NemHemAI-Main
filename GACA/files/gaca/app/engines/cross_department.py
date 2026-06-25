"""4.15 Cross-Department Governance Engine - visibility across departments.

Departments: Housing, Revenue, Health, Education, Social Welfare, Municipal Services.
Output: Citizen Governance Timeline.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, Scheme


def citizen_timeline(db: Session, citizen_id: str) -> list[dict]:
    """Chronological cross-department activity for a citizen."""
    apps = db.execute(
        select(Application).where(Application.citizen_id == citizen_id)
        .order_by(Application.submitted_at.asc())
    ).scalars().all()

    timeline = []
    for a in apps:
        scheme = db.get(Scheme, a.scheme_id)
        timeline.append({
            "date": a.submitted_at.isoformat() if a.submitted_at else None,
            "department": scheme.department if scheme else None,
            "scheme": scheme.name if scheme else a.scheme_id,
            "status": a.status,
        })
    return timeline

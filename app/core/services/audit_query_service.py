"""
Audit Query Service — search and filter the audit log.

Separate from audit_service.py (which only writes).
This one only reads — a clean read/write separation.

Key concept — immutable audit logs:
  AuditLog rows are never updated or deleted.
  This service only SELECTs from them.
  The separation enforces this at the code level — if you're in this file
  you can't accidentally write to the audit log.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.models.models import AuditLog, User


@dataclass
class AuditFilters:
    user_id:      Optional[int] = None
    action:       Optional[str] = None
    entity_type:  Optional[str] = None
    date_from:    Optional[dt.date] = None
    date_to:      Optional[dt.date] = None
    description_contains: Optional[str] = None


@dataclass
class AuditRow:
    """Flat row for UI display — no ORM object escapes the session."""
    id:           int
    timestamp:    str
    username:     str
    action:       str
    entity_type:  str
    entity_id:    Optional[str]
    description:  Optional[str]


class AuditQueryService:

    def __init__(self, session: Session) -> None:
        self.session = session

    def query(
        self,
        filters: AuditFilters,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[AuditRow], int]:

        q = (
            self.session.query(AuditLog, User)
            .outerjoin(User, User.id == AuditLog.user_id)
        )

        conditions = []

        if filters.user_id:
            conditions.append(AuditLog.user_id == filters.user_id)
        if filters.action:
            conditions.append(AuditLog.action == filters.action)
        if filters.entity_type:
            conditions.append(AuditLog.entity_type == filters.entity_type)
        if filters.date_from:
            conditions.append(AuditLog.timestamp >= dt.datetime.combine(
                filters.date_from, dt.time.min))
        if filters.date_to:
            conditions.append(AuditLog.timestamp <= dt.datetime.combine(
                filters.date_to, dt.time.max))
        if filters.description_contains:
            conditions.append(AuditLog.description.ilike(
                f"%{filters.description_contains}%"))

        if conditions:
            q = q.filter(and_(*conditions))

        total = q.count()

        rows = (
            q.order_by(AuditLog.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # Extract primitives while session is open
        results = [
            AuditRow(
                id=log.id,
                timestamp=log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                username=user.username if user else "system",
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                description=log.description,
            )
            for log, user in rows
        ]

        return results, total

    def get_distinct_actions(self) -> List[str]:
        rows = self.session.query(AuditLog.action).distinct().all()
        return sorted(r.action for r in rows)

    def get_distinct_entity_types(self) -> List[str]:
        rows = self.session.query(AuditLog.entity_type).distinct().all()
        return sorted(r.entity_type for r in rows)

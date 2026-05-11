"""
Participant Repository.

Key concept — pagination:
  Biorepositories can have thousands of participants.
  We add a paginated query so the UI never loads everything at once.
  page=1, page_size=50 → rows 1-50; page=2 → rows 51-100, etc.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.models.models import Participant, Study
from app.core.repositories.base_repository import BaseRepository


class ParticipantRepository(BaseRepository[Participant]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Participant)

    # ── Lookups ────────────────────────────────────────────────────────────

    def get_by_pid(self, pid: str) -> Optional[Participant]:
        return (
            self.session.query(Participant)
            .filter(Participant.pid == pid)
            .first()
        )

    def get_by_study(self, study_id: int) -> List[Participant]:
        return (
            self.session.query(Participant)
            .filter(Participant.study_id == study_id)
            .order_by(Participant.pid)
            .all()
        )

    def pid_exists(self, pid: str) -> bool:
        return self.get_by_pid(pid) is not None

    # ── Search (AND/OR multi-criteria) ─────────────────────────────────────
    #
    # Key concept — dynamic query building:
    #   SQLAlchemy lets you build a query incrementally.
    #   We start with a base query and .filter() more conditions onto it.
    #   filters dict = {field_name: value}
    #   use_or=True  → ANY condition matches (OR)
    #   use_or=False → ALL conditions must match (AND)

    def search(
        self,
        filters: dict,
        use_or: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Participant], int]:
        """
        Returns (results, total_count).
        filters keys: study_id, sex, age_min, age_max, cohort, pid_like
        """
        query = self.session.query(Participant)
        conditions = []

        if "study_id" in filters and filters["study_id"]:
            conditions.append(Participant.study_id == filters["study_id"])

        if "pid_like" in filters and filters["pid_like"]:
            conditions.append(
                Participant.pid.ilike(f"%{filters['pid_like']}%")
            )

        if "sex" in filters and filters["sex"]:
            conditions.append(Participant.sex == filters["sex"])

        if "age_min" in filters and filters["age_min"] is not None:
            conditions.append(Participant.age >= filters["age_min"])

        if "age_max" in filters and filters["age_max"] is not None:
            conditions.append(Participant.age <= filters["age_max"])

        if "cohort" in filters and filters["cohort"]:
            conditions.append(Participant.cohort == filters["cohort"])

        if conditions:
            query = query.filter(or_(*conditions) if use_or else
                                 query.filter(*conditions).whereclause or conditions[0])
            # Cleaner approach for AND:
            if not use_or:
                query = self.session.query(Participant)
                for cond in conditions:
                    query = query.filter(cond)

        total = query.count()
        results = (
            query.order_by(Participant.pid)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return results, total

    # ── Bulk presence check (for Excel import) ─────────────────────────────

    def get_existing_pids(self, pids: List[str]) -> set[str]:
        """Return the subset of pids that already exist in the DB."""
        rows = (
            self.session.query(Participant.pid)
            .filter(Participant.pid.in_(pids))
            .all()
        )
        return {row.pid for row in rows}

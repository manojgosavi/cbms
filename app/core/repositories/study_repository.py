"""
Study Repository — DB queries specific to Studies.

Key concept — why separate from the service?
  The repository ONLY knows about the database.
  It never makes decisions like "is this allowed?" — that's the service's job.
  This separation means you can unit-test business rules without a real DB.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.models.models import Study, VisitDefinition
from app.core.repositories.base_repository import BaseRepository


class StudyRepository(BaseRepository[Study]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Study)

    # ── Lookups ────────────────────────────────────────────────────────────

    def get_by_short_id(self, project_id_short: str) -> Optional[Study]:
        """Find a study by its short project code (e.g. 'COH')."""
        return (
            self.session.query(Study)
            .filter(Study.project_id_short == project_id_short.upper())
            .first()
        )

    def get_active(self) -> List[Study]:
        """All studies that are not archived."""
        return (
            self.session.query(Study)
            .filter(Study.is_active == True)
            .order_by(Study.name)
            .all()
        )

    def short_id_exists(self, short_id: str) -> bool:
        return self.get_by_short_id(short_id) is not None

    def name_exists(self, name: str) -> bool:
        return (
            self.session.query(Study)
            .filter(Study.name == name)
            .first()
        ) is not None

    # ── Visit definitions ──────────────────────────────────────────────────

    def add_visit(self, visit: VisitDefinition) -> VisitDefinition:
        self.session.add(visit)
        self.session.flush()
        return visit

    def get_visits(self, study_id: int) -> List[VisitDefinition]:
        return (
            self.session.query(VisitDefinition)
            .filter(VisitDefinition.study_id == study_id)
            .order_by(VisitDefinition.order_index)
            .all()
        )

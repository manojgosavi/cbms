"""
Sample Repository.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session, selectinload

from app.core.models.models import Sample, SampleAliquot
from app.core.repositories.base_repository import BaseRepository


class SampleRepository(BaseRepository[Sample]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Sample)

    def get_by_sample_id(self, sample_id: str) -> Optional[Sample]:
        return (
            self.session.query(Sample)
            .filter(Sample.sample_id == sample_id)
            .first()
        )

    def get_by_participant(self, participant_id: int) -> List[Sample]:
        return (
            self.session.query(Sample)
            .options(selectinload(Sample.aliquots))
            .filter(Sample.participant_id == participant_id)
            .order_by(Sample.collection_date)
            .all()
        )

    def get_by_study(self, study_id: int) -> List[Sample]:
        return (
            self.session.query(Sample)
            .filter(Sample.study_id == study_id)
            .all()
        )


class AliquotRepository(BaseRepository[SampleAliquot]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, SampleAliquot)

    def get_by_sample(self, sample_id: int) -> List[SampleAliquot]:
        return (
            self.session.query(SampleAliquot)
            .filter(SampleAliquot.sample_id == sample_id)
            .order_by(SampleAliquot.aliquot_number)
            .all()
        )

    def get_available(self, study_id: int) -> List[SampleAliquot]:
        """Aliquots that are not blocked, shipped, or used up."""
        return (
            self.session.query(SampleAliquot)
            .join(Sample)
            .filter(
                Sample.study_id == study_id,
                SampleAliquot.is_available == True,
                SampleAliquot.is_blocked == False,
                SampleAliquot.is_shipped == False,
            )
            .all()
        )

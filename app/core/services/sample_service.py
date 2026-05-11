"""
Sample Service — sample registration and aliquot management.
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.models.models import Sample, SampleAliquot
from app.core.repositories.participant_repository import ParticipantRepository
from app.core.repositories.sample_repository import SampleRepository, AliquotRepository
from app.core.repositories.study_repository import StudyRepository
from app.core.services.audit_service import log
from app.core.services.auth_service import app_session
from app.core.services.id_generator import (
    generate_sample_id, generate_aliquot_id, next_aliquot_number
)
from app.config import AuditAction


class SampleService:

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = SampleRepository(session)
        self.aliquot_repo = AliquotRepository(session)
        self.participant_repo = ParticipantRepository(session)
        self.study_repo = StudyRepository(session)

    # ── Create/Update sample with Excel columns ────────────────────────────

    def create_sample(
        self,
        participant_id: int,
        sample_type: str,
        collection_date: Optional[dt.date] = None,
        visit_code: Optional[str] = None,
        visit_time: Optional[str] = None,
        visit_name: Optional[str] = None,
        collected_volume_ml: Optional[float] = None,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[Sample]]:
        """Create a sample with Excel column mapping."""
        app_session.require("sample.create")

        participant = self.participant_repo.get_by_id(participant_id)
        if not participant:
            return False, "Participant not found.", None

        study_id = participant.study_id

        if not sample_type.strip():
            return False, "Sample type is required.", None

        sample_id_str = generate_sample_id(self.session, participant.study)

        sample = Sample(
            sample_id=sample_id_str,
            participant_id=participant_id,
            study_id=study_id,
            sample_type=sample_type.strip(),
            collection_date=collection_date,
            visit_code=visit_code.strip() if visit_code else None,
            visit_time=visit_time.strip() if visit_time else None,
            visit_name=visit_name,
            collected_volume_ml=collected_volume_ml,
            notes=notes.strip(),
        )
        self.repo.add(sample)

        # Create default aliquot
        aliquot_id_str = generate_aliquot_id(sample_id_str, 1)
        aliquot = SampleAliquot(
            aliquot_id=aliquot_id_str,
            sample_id=sample.id,
            aliquot_number=1,
            volume_ul=collected_volume_ml,
        )
        self.aliquot_repo.add(aliquot)

        log(self.session, AuditAction.CREATE, "Sample", sample_id_str,
            f"Sample '{sample_id_str}' created with aliquot.")

        return True, f"Sample {sample_id_str} created.", sample

    def update_sample(
        self,
        sample_id: int,
        collection_date: Optional[dt.date] = None,
        visit_code: Optional[str] = None,
        visit_time: Optional[str] = None,
        visit_name: Optional[str] = None,
        sample_type: Optional[str] = None,
        collected_volume_ml: Optional[float] = None,
        notes: str = "",
    ) -> Tuple[bool, str]:
        """Update a sample with Excel column mapping."""
        app_session.require("sample.edit")

        sample = self.repo.get_by_id(sample_id)
        if not sample:
            return False, "Sample not found."

        if collection_date is not None:
            sample.collection_date = collection_date
        if visit_code is not None:
            sample.visit_code = visit_code.strip() if visit_code else None
        if visit_time is not None:
            sample.visit_time = visit_time.strip() if visit_time else None
        if visit_name is not None:
            sample.visit_name = visit_name
        if sample_type is not None:
            sample.sample_type = sample_type.strip()
        if collected_volume_ml is not None:
            sample.collected_volume_ml = collected_volume_ml
        if notes:
            sample.notes = notes.strip()

        self.repo.update(sample)
        log(self.session, AuditAction.UPDATE, "Sample", sample.sample_id,
            f"Sample updated.")

        return True, "Sample updated."

    # ── Register sample ────────────────────────────────────────────────────

    def register_sample(
        self,
        participant_id: int,
        study_id: int,
        sample_type: str,
        num_aliquots: int = 1,
        volume_ul_per_aliquot: Optional[float] = None,
        visit_id: Optional[int] = None,
        collection_date: Optional[dt.date] = None,
        collection_time: Optional[str] = None,
        collected_volume_ml: Optional[float] = None,
        condition: str = "Fresh",
        notes: str = "",
    ) -> Tuple[bool, str, Optional[Sample]]:
        """
        Register a new sample and create N aliquots from it.

        Key concept — flush vs commit:
          session.flush() sends SQL to the DB but doesn't finalise the transaction.
          This lets us get the sample.id (needed for aliquot IDs) before committing.
          The outer get_session() context manager does the final commit.
        """
        app_session.require("sample.create")

        study = self.study_repo.get_by_id(study_id)
        if not study:
            return False, "Study not found.", None

        participant = self.participant_repo.get_by_id(participant_id)
        if not participant:
            return False, "Participant not found.", None

        if not sample_type.strip():
            return False, "Sample type is required.", None

        if num_aliquots < 1:
            return False, "Must create at least 1 aliquot.", None

        # Generate system sample ID
        sample_id_str = generate_sample_id(self.session, study)

        sample = Sample(
            sample_id=sample_id_str,
            participant_id=participant_id,
            study_id=study_id,
            visit_id=visit_id,
            sample_type=sample_type.strip(),
            collection_date=collection_date,
            collection_time=collection_time,
            collected_volume_ml=collected_volume_ml,
            condition=condition,
            notes=notes,
        )
        self.repo.add(sample)  # flush assigns sample.id

        # Create aliquots
        for i in range(1, num_aliquots + 1):
            aliquot_id_str = generate_aliquot_id(sample_id_str, i)
            aliquot = SampleAliquot(
                aliquot_id=aliquot_id_str,
                sample_id=sample.id,
                aliquot_number=i,
                volume_ul=volume_ul_per_aliquot,
            )
            self.aliquot_repo.add(aliquot)

        log(self.session, AuditAction.CREATE, "Sample", sample_id_str,
            f"Sample '{sample_id_str}' registered with {num_aliquots} aliquot(s).")

        return True, f"Sample {sample_id_str} created with {num_aliquots} aliquot(s).", sample

    # ── Add aliquots to existing sample ────────────────────────────────────

    def add_aliquots(
        self,
        sample_id: int,
        count: int,
        volume_ul: Optional[float] = None,
    ) -> Tuple[bool, str]:
        app_session.require("sample.edit")

        sample = self.repo.get_by_id(sample_id)
        if not sample:
            return False, "Sample not found."

        start = next_aliquot_number(self.session, sample_id)
        for i in range(start, start + count):
            aliquot_id_str = generate_aliquot_id(sample.sample_id, i)
            self.aliquot_repo.add(SampleAliquot(
                aliquot_id=aliquot_id_str,
                sample_id=sample_id,
                aliquot_number=i,
                volume_ul=volume_ul,
            ))

        log(self.session, AuditAction.UPDATE, "Sample", sample.sample_id,
            f"{count} aliquot(s) added.")
        return True, f"{count} aliquot(s) added."

    # ── Read ───────────────────────────────────────────────────────────────

    def get_samples_for_participant(self, participant_id: int) -> List[Sample]:
        return self.repo.get_by_participant(participant_id)

    def get_aliquots_for_sample(self, sample_id: int) -> List[SampleAliquot]:
        return self.aliquot_repo.get_by_sample(sample_id)

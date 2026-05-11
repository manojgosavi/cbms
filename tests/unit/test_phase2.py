"""
Phase 2 unit tests — services and repositories.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models.models import Base, Study, User
from app.core.services.auth_service import seed_admin, login, app_session
from app.core.services.study_service import StudyService
from app.core.services.participant_service import ParticipantService
from app.core.services.sample_service import SampleService
from app.config import Role


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    # Seed and log in as admin so permission checks pass
    seed_admin(session)
    session.commit()
    login(session, "admin", "Admin@1234")
    yield session
    session.close()
    app_session.logout()


# ── Study service ──────────────────────────────────────────────────────────

class TestStudyService:

    def test_create_study(self, db):
        svc = StudyService(db)
        ok, msg, study = svc.create_study("COH", "Cohort Study")
        assert ok, msg
        assert study.project_id_short == "COH"

    def test_short_id_uppercased_automatically(self, db):
        svc = StudyService(db)
        ok, msg, study = svc.create_study("abc", "Some Study")
        assert ok
        assert study.project_id_short == "ABC"

    def test_duplicate_short_id_rejected(self, db):
        svc = StudyService(db)
        svc.create_study("DUP", "Study One")
        ok, msg, _ = svc.create_study("DUP", "Study Two")
        assert not ok
        assert "already exists" in msg

    def test_cannot_delete_study_with_participants(self, db):
        svc = StudyService(db)
        _, _, study = svc.create_study("ND", "No Delete")
        db.commit()

        psvc = ParticipantService(db)
        psvc.register_participant(study.id, "JD")
        db.commit()

        ok, msg = svc.delete_study(study.id, "test reason")
        assert not ok
        assert "participant" in msg.lower()

    def test_delete_empty_study(self, db):
        svc = StudyService(db)
        _, _, study = svc.create_study("DEL", "Delete Me")
        db.commit()
        ok, msg = svc.delete_study(study.id, "no longer needed")
        assert ok

    def test_lock_unlock(self, db):
        svc = StudyService(db)
        _, _, study = svc.create_study("LK", "Lock Test")
        db.commit()
        ok, _ = svc.set_lock(study.id, True)
        assert ok
        db.refresh(study)
        assert study.is_locked
        svc.set_lock(study.id, False)
        db.refresh(study)
        assert not study.is_locked


# ── Participant service ────────────────────────────────────────────────────

class TestParticipantService:

    def _make_study(self, db):
        svc = StudyService(db)
        _, _, study = svc.create_study("TS", "Test Study")
        db.commit()
        return study

    def test_register_participant_generates_pid(self, db):
        study = self._make_study(db)
        svc = ParticipantService(db)
        ok, msg, p = svc.register_participant(study.id, "AB", age=30, sex="Male")
        assert ok, msg
        assert p.pid.startswith("TS-")
        assert p.initials == "AB"

    def test_initials_uppercased(self, db):
        study = self._make_study(db)
        svc = ParticipantService(db)
        _, _, p = svc.register_participant(study.id, "jd")
        assert p.initials == "JD"

    def test_sequential_pids(self, db):
        study = self._make_study(db)
        svc = ParticipantService(db)
        _, _, p1 = svc.register_participant(study.id, "AA")
        _, _, p2 = svc.register_participant(study.id, "BB")
        db.commit()
        # Extract serial number from end of PID
        serial1 = int(p1.pid.split("-")[-1])
        serial2 = int(p2.pid.split("-")[-1])
        assert serial2 == serial1 + 1

    def test_edit_requires_reason(self, db):
        study = self._make_study(db)
        svc = ParticipantService(db)
        _, _, p = svc.register_participant(study.id, "XY")
        db.commit()
        ok, msg = svc.update_participant(p.id, "", age=25)
        assert not ok
        assert "reason" in msg.lower()

    def test_edit_participant(self, db):
        study = self._make_study(db)
        svc = ParticipantService(db)
        _, _, p = svc.register_participant(study.id, "XY", age=20)
        db.commit()
        ok, _ = svc.update_participant(p.id, "age correction", age=21)
        assert ok
        db.refresh(p)
        assert p.age == 21


# ── Sample service ─────────────────────────────────────────────────────────

class TestSampleService:

    def _setup(self, db):
        study_svc = StudyService(db)
        _, _, study = study_svc.create_study("SMP", "Sample Study")
        db.commit()
        p_svc = ParticipantService(db)
        _, _, participant = p_svc.register_participant(study.id, "JD")
        db.commit()
        return study, participant

    def test_register_sample_creates_aliquots(self, db):
        study, participant = self._setup(db)
        svc = SampleService(db)
        ok, msg, sample = svc.register_sample(
            participant_id=participant.id,
            study_id=study.id,
            sample_type="Blood",
            num_aliquots=3,
        )
        assert ok, msg
        assert len(sample.aliquots) == 3

    def test_aliquot_ids_formatted_correctly(self, db):
        study, participant = self._setup(db)
        svc = SampleService(db)
        _, _, sample = svc.register_sample(
            participant_id=participant.id,
            study_id=study.id,
            sample_type="Serum",
            num_aliquots=2,
        )
        ids = [a.aliquot_id for a in sample.aliquots]
        assert ids[0].endswith("-A1")
        assert ids[1].endswith("-A2")

    def test_add_aliquots_to_existing(self, db):
        study, participant = self._setup(db)
        svc = SampleService(db)
        _, _, sample = svc.register_sample(
            participant_id=participant.id,
            study_id=study.id,
            sample_type="PBMC",
            num_aliquots=2,
        )
        db.commit()
        ok, msg = svc.add_aliquots(sample.id, count=2)
        assert ok, msg
        db.refresh(sample)
        assert len(sample.aliquots) == 4

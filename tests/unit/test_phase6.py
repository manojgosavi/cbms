"""
Phase 6 tests — sample processing and backup utility.
"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models.models import Base
from app.core.services.auth_service import seed_admin, login, app_session
from app.core.services.study_service import StudyService
from app.core.services.participant_service import ParticipantService
from app.core.services.sample_service import SampleService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    seed_admin(session)
    session.commit()
    login(session, "admin", "Admin@1234")
    yield session
    session.close()
    app_session.logout()


@pytest.fixture
def setup(db):
    study_svc = StudyService(db)
    _, _, study = study_svc.create_study("S6", "Phase 6 Study")
    db.commit()
    p_svc = ParticipantService(db)
    _, _, p = p_svc.register_participant(study.id, "XY", age=28, sex="Male")
    db.commit()
    return study, p


class TestSampleService:

    def test_register_sample_with_aliquots(self, db, setup):
        study, p = setup
        svc = SampleService(db)
        ok, msg, sample = svc.register_sample(
            p.id, study.id, "Serum", num_aliquots=4,
            volume_ul_per_aliquot=500.0
        )
        assert ok, msg
        assert len(sample.aliquots) == 4
        assert all(a.volume_ul == 500.0 for a in sample.aliquots)

    def test_aliquot_ids_sequential(self, db, setup):
        study, p = setup
        svc = SampleService(db)
        _, _, sample = svc.register_sample(p.id, study.id, "PBMC", num_aliquots=3)
        ids = [a.aliquot_id for a in sample.aliquots]
        assert ids[0].endswith("-A1")
        assert ids[1].endswith("-A2")
        assert ids[2].endswith("-A3")

    def test_add_aliquots_to_existing_sample(self, db, setup):
        study, p = setup
        svc = SampleService(db)
        _, _, sample = svc.register_sample(p.id, study.id, "Serum", num_aliquots=2)
        db.commit()
        ok, msg = svc.add_aliquots(sample.id, count=3, volume_ul=250.0)
        assert ok, msg
        db.refresh(sample)
        assert len(sample.aliquots) == 5

    def test_new_aliquots_continue_numbering(self, db, setup):
        study, p = setup
        svc = SampleService(db)
        _, _, sample = svc.register_sample(p.id, study.id, "Serum", num_aliquots=2)
        db.commit()
        svc.add_aliquots(sample.id, count=2)
        db.refresh(sample)
        numbers = sorted(a.aliquot_number for a in sample.aliquots)
        assert numbers == [1, 2, 3, 4]

    def test_multiple_sample_types_per_participant(self, db, setup):
        study, p = setup
        svc = SampleService(db)
        svc.register_sample(p.id, study.id, "Serum",     num_aliquots=2)
        svc.register_sample(p.id, study.id, "ED Plasma", num_aliquots=3)
        svc.register_sample(p.id, study.id, "PBMC",      num_aliquots=1)
        db.commit()
        samples = svc.get_samples_for_participant(p.id)
        assert len(samples) == 3
        types = {s.sample_type for s in samples}
        assert types == {"Serum", "ED Plasma", "PBMC"}

    def test_sample_id_format(self, db, setup):
        import datetime as dt
        study, p = setup
        svc = SampleService(db)
        _, _, sample = svc.register_sample(p.id, study.id, "Serum")
        year = str(dt.date.today().year)[-2:]
        assert sample.sample_id.startswith(f"S6-{year}-")

    def test_cannot_register_without_sample_type(self, db, setup):
        study, p = setup
        svc = SampleService(db)
        ok, msg, _ = svc.register_sample(p.id, study.id, "")
        assert not ok
        assert "type" in msg.lower()


class TestBackupUtility:

    def test_backup_fails_if_no_db(self, tmp_path, monkeypatch):
        import app.utils.backup as backup_mod
        monkeypatch.setattr(backup_mod, "DB_PATH", tmp_path / "nonexistent.db")
        monkeypatch.setattr(backup_mod, "BACKUP_DIR", tmp_path / "backups")
        ok, msg = backup_mod.run_backup()
        assert not ok

    def test_backup_creates_file(self, tmp_path, monkeypatch):
        import app.utils.backup as backup_mod

        # Create a fake DB file
        fake_db = tmp_path / "cbms.db"
        fake_db.write_bytes(b"SQLite fake content")
        backup_dir = tmp_path / "backups"

        monkeypatch.setattr(backup_mod, "DB_PATH", fake_db)
        monkeypatch.setattr(backup_mod, "BACKUP_DIR", backup_dir)

        ok, path = backup_mod.run_backup()
        assert ok
        assert os.path.exists(path)
        assert "cbms_" in path

    def test_backup_uses_timestamp_in_filename(self, tmp_path, monkeypatch):
        import app.utils.backup as backup_mod
        import datetime as dt

        fake_db = tmp_path / "cbms.db"
        fake_db.write_bytes(b"SQLite content")
        backup_dir = tmp_path / "backups"

        monkeypatch.setattr(backup_mod, "DB_PATH", fake_db)
        monkeypatch.setattr(backup_mod, "BACKUP_DIR", backup_dir)

        ok, path = backup_mod.run_backup()
        today = dt.date.today().strftime("%Y%m%d")
        assert today in path

    def test_multiple_backups_unique_names(self, tmp_path, monkeypatch):
        import app.utils.backup as backup_mod

        fake_db = tmp_path / "cbms.db"
        fake_db.write_bytes(b"content")
        backup_dir = tmp_path / "backups"

        monkeypatch.setattr(backup_mod, "DB_PATH", fake_db)
        monkeypatch.setattr(backup_mod, "BACKUP_DIR", backup_dir)

        import time
        _, path1 = backup_mod.run_backup()
        time.sleep(1)   # ensure different timestamp
        _, path2 = backup_mod.run_backup()

        assert path1 != path2

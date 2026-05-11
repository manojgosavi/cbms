"""
Phase 3 tests — storage hierarchy.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models.models import Base, SampleAliquot, Sample, Participant
from app.core.services.auth_service import seed_admin, login, app_session
from app.core.services.storage_service import StorageService
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
def storage(db):
    svc = StorageService(db)
    _, _, freezer = svc.create_freezer("Freezer-1", temperature="-80°C")
    db.commit()
    _, _, box = svc.create_box("Box-A", freezer.id, rows=9, cols=9)
    db.commit()
    return svc, freezer, box


@pytest.fixture
def aliquot(db):
    """Create a study → participant → sample → aliquot chain."""
    study_svc = StudyService(db)
    _, _, study = study_svc.create_study("ALQ", "Aliquot Study")
    db.commit()
    p_svc = ParticipantService(db)
    _, _, participant = p_svc.register_participant(study.id, "JD")
    db.commit()
    s_svc = SampleService(db)
    _, _, sample = s_svc.register_sample(
        participant.id, study.id, "Blood", num_aliquots=3
    )
    db.commit()
    return sample.aliquots[0]


class TestFreezerService:

    def test_create_freezer(self, db):
        svc = StorageService(db)
        ok, msg, f = svc.create_freezer("F1", temperature="-80°C")
        assert ok, msg
        assert f.name == "F1"

    def test_duplicate_freezer_name_rejected(self, db):
        svc = StorageService(db)
        svc.create_freezer("SAME")
        ok, msg, _ = svc.create_freezer("SAME")
        assert not ok

    def test_lock_prevents_new_box(self, db):
        svc = StorageService(db)
        _, _, f = svc.create_freezer("Locked")
        db.commit()
        svc.set_freezer_lock(f.id, True)
        db.commit()
        ok, msg, _ = svc.create_box("B1", f.id)
        assert not ok
        assert "locked" in msg.lower()


class TestBoxService:

    def test_create_box_pre_populates_positions(self, db):
        svc = StorageService(db)
        _, _, f = svc.create_freezer("F2")
        db.commit()
        _, _, box = svc.create_box("B1", f.id, rows=3, cols=4)
        db.commit()
        assert len(box.positions) == 12   # 3 × 4

    def test_box_capacity_count(self, db):
        svc = StorageService(db)
        _, _, f = svc.create_freezer("F3")
        db.commit()
        _, _, box = svc.create_box("B2", f.id, rows=9, cols=9)
        db.commit()
        assert box.total_positions == 81
        assert box.occupied_positions == 0

    def test_duplicate_box_name_in_same_freezer(self, db):
        svc = StorageService(db)
        _, _, f = svc.create_freezer("F4")
        db.commit()
        svc.create_box("DUP", f.id)
        db.commit()
        ok, msg, _ = svc.create_box("DUP", f.id)
        assert not ok

    def test_same_box_name_in_different_freezer_allowed(self, db):
        svc = StorageService(db)
        _, _, f1 = svc.create_freezer("FA")
        _, _, f2 = svc.create_freezer("FB")
        db.commit()
        ok1, _, _ = svc.create_box("BOX1", f1.id)
        ok2, _, _ = svc.create_box("BOX1", f2.id)
        assert ok1 and ok2


class TestAliquotPlacement:

    def test_place_aliquot(self, storage, aliquot):
        svc, freezer, box = storage
        ok, msg = svc.place_aliquot(aliquot.id, box.id, 0, 0)
        assert ok, msg

    def test_cannot_place_same_aliquot_twice(self, storage, aliquot):
        svc, freezer, box = storage
        svc.place_aliquot(aliquot.id, box.id, 0, 0)
        ok, msg = svc.place_aliquot(aliquot.id, box.id, 0, 1)
        assert not ok
        assert "already located" in msg

    def test_cannot_place_in_occupied_position(self, storage, aliquot, db):
        svc, freezer, box = storage
        # Get a second aliquot
        other_aliquot = db.query(SampleAliquot).filter(
            SampleAliquot.id != aliquot.id
        ).first()
        svc.place_aliquot(aliquot.id, box.id, 1, 1)
        db.commit()
        ok, msg = svc.place_aliquot(other_aliquot.id, box.id, 1, 1)
        assert not ok
        assert "occupied" in msg

    def test_move_aliquot(self, storage, aliquot, db):
        svc, freezer, box = storage
        svc.place_aliquot(aliquot.id, box.id, 0, 0)
        db.commit()
        ok, msg = svc.move_aliquot(aliquot.id, box.id, 2, 3, reason="reorganising")
        assert ok, msg
        # Old position should now be free
        from app.core.repositories.storage_repository import BoxPositionRepository
        pos_repo = BoxPositionRepository(db)
        old_pos = pos_repo.get_position(box.id, 0, 0)
        assert old_pos.aliquot_location is None

    def test_move_requires_reason(self, storage, aliquot, db):
        svc, freezer, box = storage
        svc.place_aliquot(aliquot.id, box.id, 0, 0)
        db.commit()
        ok, msg = svc.move_aliquot(aliquot.id, box.id, 1, 1, reason="")
        assert not ok
        assert "reason" in msg.lower()

    def test_remove_aliquot_from_position(self, storage, aliquot, db):
        svc, freezer, box = storage
        svc.place_aliquot(aliquot.id, box.id, 3, 3)
        db.commit()
        ok, msg = svc.remove_aliquot_from_position(aliquot.id, "error correction")
        assert ok, msg


class TestBoxGridWidget:
    """Test CellData logic (no Qt needed — pure Python)."""

    def test_cell_data_defaults(self):
        from app.ui.widgets.box_grid_widget import CellData
        c = CellData(row=0, col=0, position_id=1)
        assert c.aliquot_id is None
        assert not c.is_blocked
        assert not c.is_shipped

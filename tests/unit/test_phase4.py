"""
Phase 4 tests — search, blocking, shipment.
"""

import datetime as dt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models.models import Base
from app.core.services.auth_service import seed_admin, login, app_session
from app.core.services.study_service import StudyService
from app.core.services.participant_service import ParticipantService
from app.core.services.sample_service import SampleService
from app.core.services.storage_service import StorageService
from app.core.services.blocking_service import BlockingService
from app.core.services.shipment_service import ShipmentService
from app.core.services.search_service import SearchFilters, SearchService


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
def full_data(db):
    """Create study → participant → sample → aliquots (3) for all tests."""
    study_svc = StudyService(db)
    _, _, study = study_svc.create_study("TST", "Test Study")
    db.commit()

    p_svc = ParticipantService(db)
    _, _, p1 = p_svc.register_participant(study.id, "AB", age=30, sex="Male",
                                           disease="TB", cohort="UN")
    _, _, p2 = p_svc.register_participant(study.id, "CD", age=45, sex="Female",
                                           disease="CVD", cohort="IN")
    db.commit()

    s_svc = SampleService(db)
    _, _, s1 = s_svc.register_sample(p1.id, study.id, "Serum",     num_aliquots=2)
    _, _, s2 = s_svc.register_sample(p2.id, study.id, "ED Plasma", num_aliquots=2)
    db.commit()

    return study, p1, p2, s1, s2


# ══════════════════════════════════════════════════════════════════════════
# SEARCH
# ══════════════════════════════════════════════════════════════════════════

class TestSearchService:

    def test_search_all(self, db, full_data):
        svc = SearchService(db)
        results, total = svc.search(SearchFilters())
        assert total == 4   # 2 aliquots each for 2 samples

    def test_search_by_pid(self, db, full_data):
        study, p1, *_ = full_data
        svc = SearchService(db)
        results, total = svc.search(SearchFilters(pid=p1.pid))
        assert all(r.pid == p1.pid for r in results)

    def test_search_by_sex(self, db, full_data):
        svc = SearchService(db)
        results, _ = svc.search(SearchFilters(sex="Male"))
        assert all(r.sex == "Male" for r in results)

    def test_search_by_disease(self, db, full_data):
        svc = SearchService(db)
        results, _ = svc.search(SearchFilters(disease="TB"))
        assert all(r.disease == "TB" for r in results)

    def test_search_by_sample_type(self, db, full_data):
        svc = SearchService(db)
        results, _ = svc.search(SearchFilters(sample_type="Serum"))
        assert all(r.sample_type == "Serum" for r in results)

    def test_or_mode_returns_more(self, db, full_data):
        svc = SearchService(db)
        # AND: age 30 AND Female → 0 results (p1 is Male aged 30, p2 is Female aged 45)
        and_results, _ = svc.search(SearchFilters(age_min=30, age_max=30, sex="Female"))
        # OR: age 30 OR Female → both participants
        or_results, _  = svc.search(SearchFilters(age_min=30, age_max=30, sex="Female", use_or=True))
        assert len(or_results) > len(and_results)

    def test_age_range_filter(self, db, full_data):
        svc = SearchService(db)
        results, _ = svc.search(SearchFilters(age_min=40, age_max=50))
        assert all(40 <= r.age <= 50 for r in results)

    def test_available_only_filter(self, db, full_data):
        svc = SearchService(db)
        results, _ = svc.search(SearchFilters(available_only=True))
        assert all(r.is_available for r in results)


# ══════════════════════════════════════════════════════════════════════════
# BLOCKING
# ══════════════════════════════════════════════════════════════════════════

class TestBlockingService:

    def _get_aliquot_ids(self, full_data):
        _, _, _, s1, _ = full_data
        return [a.id for a in s1.aliquots]

    def test_block_aliquots(self, db, full_data):
        ids = self._get_aliquot_ids(full_data)
        svc = BlockingService(db)
        future = dt.date.today() + dt.timedelta(days=30)
        ok, msg, details = svc.block_aliquots(ids, "Dr. Smith", future, "For study XYZ")
        assert ok, msg
        assert details["blocked"] == len(ids)

    def test_blocked_aliquot_shows_in_search(self, db, full_data):
        ids = self._get_aliquot_ids(full_data)
        svc = BlockingService(db)
        future = dt.date.today() + dt.timedelta(days=30)
        svc.block_aliquots(ids, "Dr. Smith", future, "test")
        db.commit()

        search_svc = SearchService(db)
        results, _ = search_svc.search(SearchFilters(blocked_only=True))
        assert len(results) == len(ids)

    def test_cannot_block_already_blocked(self, db, full_data):
        ids = self._get_aliquot_ids(full_data)
        svc = BlockingService(db)
        future = dt.date.today() + dt.timedelta(days=30)
        svc.block_aliquots(ids, "Dr. Smith", future, "first block")
        db.commit()
        _, _, details = svc.block_aliquots(ids, "Dr. Jones", future, "second block")
        assert details["blocked"] == 0
        assert len(details["skipped"]) == len(ids)

    def test_release_block(self, db, full_data):
        ids = self._get_aliquot_ids(full_data)
        svc = BlockingService(db)
        future = dt.date.today() + dt.timedelta(days=30)
        svc.block_aliquots(ids, "Dr. Smith", future, "test")
        db.commit()
        ok, msg = svc.release_block(ids[0], "no longer needed")
        assert ok, msg

    def test_extend_block(self, db, full_data):
        ids = self._get_aliquot_ids(full_data)
        svc = BlockingService(db)
        future = dt.date.today() + dt.timedelta(days=30)
        svc.block_aliquots([ids[0]], "Dr. Smith", future, "test")
        db.commit()
        new_date = dt.date.today() + dt.timedelta(days=60)
        ok, msg = svc.extend_block(ids[0], new_date, "need more time")
        assert ok, msg

    def test_past_unblock_date_rejected(self, db, full_data):
        ids = self._get_aliquot_ids(full_data)
        svc = BlockingService(db)
        past = dt.date.today() - dt.timedelta(days=1)
        ok, msg, _ = svc.block_aliquots(ids, "Dr. Smith", past, "test")
        assert not ok
        assert "future" in msg.lower()

    def test_overdue_blocks_detected(self, db, full_data):
        from app.core.models.models import SampleBlock, SampleAliquot
        import datetime as dt2
        ids = self._get_aliquot_ids(full_data)
        aliquot = db.get(SampleAliquot, ids[0])
        aliquot.is_blocked = True
        db.add(SampleBlock(
            aliquot_id=ids[0],
            blocked_by="Dr. Old",
            unblock_at=dt2.datetime.utcnow() - dt2.timedelta(days=5),
            reason="expired",
        ))
        db.commit()
        svc = BlockingService(db)
        overdue = svc.get_overdue_blocks()
        assert len(overdue) >= 1


# ══════════════════════════════════════════════════════════════════════════
# SHIPMENT
# ══════════════════════════════════════════════════════════════════════════

class TestShipmentService:

    def _block_aliquots(self, db, full_data):
        _, _, _, s1, _ = full_data
        ids = [a.id for a in s1.aliquots]
        b_svc = BlockingService(db)
        future = dt.date.today() + dt.timedelta(days=30)
        b_svc.block_aliquots(ids, "Dr. Smith", future, "for shipment test")
        db.commit()
        return ids

    def test_create_shipment(self, db, full_data):
        ids = self._block_aliquots(db, full_data)
        svc = ShipmentService(db)
        ok, msg, shipment = svc.create_shipment(
            ids, "Prof. Jones", "Oxford Uni", "jones@oxford.ac.uk"
        )
        assert ok, msg
        assert shipment.shipment_ref.startswith("SHIP-")

    def test_shipment_removes_location(self, db, full_data):
        # Place aliquot in a box first
        study, p1, _, s1, _ = full_data
        st_svc = StorageService(db)
        _, _, freezer = st_svc.create_freezer("F1")
        _, _, box = st_svc.create_box("B1", freezer.id, rows=9, cols=9)
        db.commit()
        aliquot = s1.aliquots[0]
        st_svc.place_aliquot(aliquot.id, box.id, 0, 0)
        db.commit()

        # Block then ship
        b_svc = BlockingService(db)
        future = dt.date.today() + dt.timedelta(days=30)
        b_svc.block_aliquots([aliquot.id], "Dr. X", future, "test")
        db.commit()

        svc = ShipmentService(db)
        ok, msg, _ = svc.create_shipment([aliquot.id], "Recipient", "Inst")
        assert ok, msg

        # Aliquot should have no location
        from app.core.models.models import AliquotLocation
        loc = db.query(AliquotLocation).filter_by(aliquot_id=aliquot.id).first()
        assert loc is None

    def test_cannot_ship_unblocked_aliquot(self, db, full_data):
        _, _, _, s1, _ = full_data
        ids = [s1.aliquots[0].id]
        svc = ShipmentService(db)
        ok, msg, _ = svc.create_shipment(ids, "Someone", "Somewhere")
        assert not ok
        assert "block" in msg.lower()

    def test_shipment_ref_sequential(self, db, full_data):
        ids = self._block_aliquots(db, full_data)
        svc = ShipmentService(db)
        _, _, ship1 = svc.create_shipment([ids[0]], "R1", "I1")
        db.commit()
        # Re-block remaining
        future = dt.date.today() + dt.timedelta(days=30)
        b_svc = BlockingService(db)
        b_svc.block_aliquots([ids[1]], "Dr. X", future, "second shipment")
        db.commit()
        _, _, ship2 = svc.create_shipment([ids[1]], "R2", "I2")
        assert ship1.shipment_ref != ship2.shipment_ref

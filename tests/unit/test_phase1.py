"""
Unit tests — Phase 1 core logic.
Run with:  pytest tests/ -v
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models.models import Base, Study, Sample, SampleAliquot, User
from app.core.models.database import get_session
from app.core.services.id_generator import (
    generate_sample_id, generate_aliquot_id, next_aliquot_number
)
from app.core.services.auth_service import (
    hash_password, verify_password, register_user, login, seed_admin
)
from app.config import Role


# ── In-memory test DB ──────────────────────────────────────────────────────

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ── ID Generator ───────────────────────────────────────────────────────────

class TestSampleIDGenerator:

    def test_first_sample_id(self, db):
        import datetime as dt
        study = Study(project_id_short="COH", name="Test Study")
        db.add(study)
        db.flush()

        sample_id = generate_sample_id(db, study)
        year = str(dt.date.today().year)[-2:]
        assert sample_id == f"COH-{year}-1"

    def test_sequential_ids(self, db):
        import datetime as dt
        study = Study(project_id_short="DIAB", name="Diabetes Study")
        db.add(study)
        db.flush()

        year = str(dt.date.today().year)[-2:]

        # Simulate 3 existing samples
        for i in range(1, 4):
            s = Sample(
                sample_id=f"DIAB-{year}-{i}",
                participant_id=1,
                study_id=study.id,
                sample_type="Blood",
            )
            db.add(s)
        db.flush()

        next_id = generate_sample_id(db, study)
        assert next_id == f"DIAB-{year}-4"

    def test_different_studies_independent_serials(self, db):
        import datetime as dt
        s1 = Study(project_id_short="AA", name="Study A")
        s2 = Study(project_id_short="BB", name="Study B")
        db.add_all([s1, s2])
        db.flush()

        year = str(dt.date.today().year)[-2:]
        id1 = generate_sample_id(db, s1)
        id2 = generate_sample_id(db, s2)

        assert id1 == f"AA-{year}-1"
        assert id2 == f"BB-{year}-1"

    def test_aliquot_id_format(self):
        assert generate_aliquot_id("COH-26-1", 1) == "COH-26-1-A1"
        assert generate_aliquot_id("COH-26-1", 3) == "COH-26-1-A3"

    def test_next_aliquot_number(self, db):
        study = Study(project_id_short="TS", name="Test")
        db.add(study)
        db.flush()

        sample = Sample(
            sample_id="TS-26-1", participant_id=1,
            study_id=study.id, sample_type="Serum"
        )
        db.add(sample)
        db.flush()

        assert next_aliquot_number(db, sample.id) == 1

        db.add(SampleAliquot(
            aliquot_id="TS-26-1-A1", sample_id=sample.id, aliquot_number=1
        ))
        db.flush()
        assert next_aliquot_number(db, sample.id) == 2


# ── Auth ───────────────────────────────────────────────────────────────────

class TestAuth:

    def test_password_hash_and_verify(self):
        h = hash_password("SecurePass123")
        assert verify_password("SecurePass123", h)
        assert not verify_password("WrongPass", h)

    def test_hash_is_not_plaintext(self):
        h = hash_password("MyPassword")
        assert h != "MyPassword"

    def test_register_and_login(self, db):
        ok, msg = register_user(db, "jdoe", "j@lab.org", "Pass@123", Role.LAB_TECH, auto_approve=True)
        assert ok, msg

        success, msg = login(db, "jdoe", "Pass@123")
        assert success, msg

    def test_duplicate_username_rejected(self, db):
        register_user(db, "alice", "alice@lab.org", "pass", Role.PI, auto_approve=True)
        ok, msg = register_user(db, "alice", "other@lab.org", "pass", Role.PI, auto_approve=True)
        assert not ok
        assert "already exists" in msg

    def test_unapproved_user_cannot_login(self, db):
        register_user(db, "bob", "bob@lab.org", "pass", Role.LAB_TECH, auto_approve=False)
        success, msg = login(db, "bob", "pass")
        assert not success
        assert "pending approval" in msg

    def test_wrong_password(self, db):
        register_user(db, "carol", "c@lab.org", "correct", Role.MANAGER, auto_approve=True)
        success, msg = login(db, "carol", "wrong")
        assert not success

    def test_seed_admin_creates_user(self, db):
        seed_admin(db)
        user = db.query(User).filter_by(username="admin").first()
        assert user is not None
        assert user.role == Role.PI
        assert user.is_approved

    def test_seed_admin_idempotent(self, db):
        seed_admin(db)
        seed_admin(db)
        count = db.query(User).filter_by(username="admin").count()
        assert count == 1


# ── RBAC ───────────────────────────────────────────────────────────────────

class TestRBAC:

    def test_pi_can_do_everything(self):
        assert Role.can(Role.PI, "admin.users")
        assert Role.can(Role.PI, "study.delete")
        assert Role.can(Role.PI, "sample.create")

    def test_lab_tech_limited(self):
        assert Role.can(Role.LAB_TECH, "sample.create")
        assert not Role.can(Role.LAB_TECH, "admin.users")
        assert not Role.can(Role.LAB_TECH, "study.delete")

    def test_invalid_role_has_no_permissions(self):
        assert not Role.can("GHOST", "sample.create")

"""
Unit tests — storage hierarchy column mapping fix.

Verifies that:
  - container_name (Excel col O) becomes the StorageBox name (not "Box-1")
  - shelf_name (Excel col Q)   becomes the Compartment name
  - rack_letter from col R     becomes the StorageRack name
  - drawer_number from col R   becomes the StorageDrawer name
  - cylindrical freezers get the sentinel compartment/drawer structure
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models.models import Base
from app.core.services.excel_import_service import (
    ExcelImportService,
    CYLINDRICAL_SENTINEL_COMPARTMENT,
    CYLINDRICAL_SENTINEL_DRAWER,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


class TestUprightHierarchy:

    def test_box_named_from_container_not_hardcoded(self, session):
        svc = ExcelImportService(session)
        _, _, _, _, box = svc._get_or_create_storage_hierarchy(
            "TEST-FREEZER", "MY-BOX-CONTAINER", "III", "D-02"
        )
        assert box.name == "MY-BOX-CONTAINER"
        assert box.name != "Box-1"

    def test_compartment_named_from_shelf_not_container(self, session):
        svc = ExcelImportService(session)
        _, comp, _, _, _ = svc._get_or_create_storage_hierarchy(
            "TEST-FREEZER", "CONTAINER-NAME", "II", "A-01"
        )
        assert comp.name == "II"
        assert comp.name != "CONTAINER-NAME"

    def test_rack_and_drawer_parsed_from_combined(self, session):
        svc = ExcelImportService(session)
        _, _, rack, drawer, _ = svc._get_or_create_storage_hierarchy(
            "TEST-FREEZER", "BOX-NAME", "I", "D-02"
        )
        assert rack.name == "D"
        assert drawer.name == "02"

    def test_idempotent_returns_same_box(self, session):
        svc = ExcelImportService(session)
        _, _, _, _, box1 = svc._get_or_create_storage_hierarchy(
            "TEST-FREEZER", "BOX-A", "III", "B-03"
        )
        _, _, _, _, box2 = svc._get_or_create_storage_hierarchy(
            "TEST-FREEZER", "BOX-A", "III", "B-03"
        )
        assert box1.id == box2.id

    def test_different_containers_create_different_boxes(self, session):
        svc = ExcelImportService(session)
        _, _, _, _, box1 = svc._get_or_create_storage_hierarchy(
            "TEST-FREEZER", "BOX-SERUM", "I", "A-01"
        )
        _, _, _, _, box2 = svc._get_or_create_storage_hierarchy(
            "TEST-FREEZER", "BOX-PLASMA", "I", "A-01"
        )
        assert box1.id != box2.id
        assert box1.name == "BOX-SERUM"
        assert box2.name == "BOX-PLASMA"

    def test_box_has_100_positions(self, session):
        svc = ExcelImportService(session)
        _, _, _, _, box = svc._get_or_create_storage_hierarchy(
            "TEST-FREEZER", "MY-BOX", "IV", "F-05"
        )
        assert len(box.positions) == 100


class TestCylindricalHierarchy:

    def test_sentinel_compartment_created(self, session):
        svc = ExcelImportService(session)
        _, comp, _, _, _ = svc._get_or_create_storage_hierarchy_cylindrical(
            "CYL-FREEZER", "CYL-BOX", "07"
        )
        assert comp.name == CYLINDRICAL_SENTINEL_COMPARTMENT

    def test_rack_number_preserved(self, session):
        svc = ExcelImportService(session)
        _, _, rack, _, _ = svc._get_or_create_storage_hierarchy_cylindrical(
            "CYL-FREEZER", "CYL-BOX", "07"
        )
        assert rack.name == "07"

    def test_sentinel_drawer_created(self, session):
        svc = ExcelImportService(session)
        _, _, _, drawer, _ = svc._get_or_create_storage_hierarchy_cylindrical(
            "CYL-FREEZER", "CYL-BOX", "13"
        )
        assert drawer.name == CYLINDRICAL_SENTINEL_DRAWER

    def test_box_named_from_container(self, session):
        svc = ExcelImportService(session)
        _, _, _, _, box = svc._get_or_create_storage_hierarchy_cylindrical(
            "CYL-FREEZER", "MY-CYL-BOX", "01"
        )
        assert box.name == "MY-CYL-BOX"

    def test_cylindrical_idempotent(self, session):
        svc = ExcelImportService(session)
        _, _, _, _, box1 = svc._get_or_create_storage_hierarchy_cylindrical(
            "CYL-FREEZER", "CYL-BOX", "05"
        )
        _, _, _, _, box2 = svc._get_or_create_storage_hierarchy_cylindrical(
            "CYL-FREEZER", "CYL-BOX", "05"
        )
        assert box1.id == box2.id

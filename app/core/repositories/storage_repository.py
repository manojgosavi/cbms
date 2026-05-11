"""
Storage Repository — Freezer, Compartment, Rack, Drawer, StorageBox,
                     BoxPosition, AliquotLocation.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.models.models import (
    AliquotLocation, BoxPosition, Compartment, Freezer, SampleAliquot,
    Sample, Participant, StorageBox, StorageDrawer, StorageRack,
)
from app.core.repositories.base_repository import BaseRepository


class FreezerRepository(BaseRepository[Freezer]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Freezer)

    def get_by_name(self, name: str) -> Optional[Freezer]:
        return (
            self.session.query(Freezer)
            .filter(Freezer.name == name)
            .first()
        )

    def name_exists(self, name: str) -> bool:
        return self.get_by_name(name) is not None

    def get_all_with_hierarchy(self) -> List[Freezer]:
        """Eagerly load full hierarchy so UI doesn't trigger N+1 queries."""
        return (
            self.session.query(Freezer)
            .options(
                joinedload(Freezer.compartments)
                .joinedload(Compartment.racks)
                .joinedload(StorageRack.drawers)
                .joinedload(StorageDrawer.boxes)
            )
            .order_by(Freezer.name)
            .all()
        )


class CompartmentRepository(BaseRepository[Compartment]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Compartment)

    def get_by_freezer(self, freezer_id: int) -> List[Compartment]:
        return (
            self.session.query(Compartment)
            .filter(Compartment.freezer_id == freezer_id)
            .order_by(Compartment.name)
            .all()
        )

    def name_exists_in_freezer(self, name: str, freezer_id: int) -> bool:
        return (
            self.session.query(Compartment)
            .filter(
                Compartment.name == name,
                Compartment.freezer_id == freezer_id,
            )
            .first()
        ) is not None


class StorageRackRepository(BaseRepository[StorageRack]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, StorageRack)

    def get_by_compartment(self, compartment_id: int) -> List[StorageRack]:
        return (
            self.session.query(StorageRack)
            .filter(StorageRack.compartment_id == compartment_id)
            .order_by(StorageRack.name)
            .all()
        )

    def name_exists_in_compartment(self, name: str, compartment_id: int) -> bool:
        return (
            self.session.query(StorageRack)
            .filter(
                StorageRack.name == name,
                StorageRack.compartment_id == compartment_id,
            )
            .first()
        ) is not None


class StorageDrawerRepository(BaseRepository[StorageDrawer]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, StorageDrawer)

    def get_by_rack(self, rack_id: int) -> List[StorageDrawer]:
        return (
            self.session.query(StorageDrawer)
            .filter(StorageDrawer.rack_id == rack_id)
            .order_by(StorageDrawer.name)
            .all()
        )

    def name_exists_in_rack(self, name: str, rack_id: int) -> bool:
        return (
            self.session.query(StorageDrawer)
            .filter(
                StorageDrawer.name == name,
                StorageDrawer.rack_id == rack_id,
            )
            .first()
        ) is not None


class StorageBoxRepository(BaseRepository[StorageBox]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, StorageBox)

    def get_by_drawer(self, drawer_id: int) -> List[StorageBox]:
        return (
            self.session.query(StorageBox)
            .filter(StorageBox.drawer_id == drawer_id)
            .order_by(StorageBox.name)
            .all()
        )

    def name_exists_in_drawer(self, name: str, drawer_id: int) -> bool:
        return (
            self.session.query(StorageBox)
            .filter(
                StorageBox.name == name,
                StorageBox.drawer_id == drawer_id,
            )
            .first()
        ) is not None

    def get_with_positions(self, box_id: int) -> Optional[StorageBox]:
        """
        Load a box with all its positions AND each position's aliquot location.
        """
        return (
            self.session.query(StorageBox)
            .options(
                joinedload(StorageBox.positions)
                .joinedload(BoxPosition.aliquot_location)
                .joinedload(AliquotLocation.aliquot)
            )
            .filter(StorageBox.id == box_id)
            .first()
        )


class BoxPositionRepository(BaseRepository[BoxPosition]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, BoxPosition)

    def get_position(self, box_id: int, row: int, col: int) -> Optional[BoxPosition]:
        return (
            self.session.query(BoxPosition)
            .filter(
                BoxPosition.box_id == box_id,
                BoxPosition.row == row,
                BoxPosition.col == col,
            )
            .first()
        )

    def get_free_positions(self, box_id: int) -> List[BoxPosition]:
        """Positions that have no aliquot assigned."""
        return (
            self.session.query(BoxPosition)
            .outerjoin(BoxPosition.aliquot_location)
            .filter(
                BoxPosition.box_id == box_id,
                AliquotLocation.id == None,
            )
            .all()
        )


class AliquotLocationRepository(BaseRepository[AliquotLocation]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, AliquotLocation)

    def get_by_aliquot(self, aliquot_id: int) -> Optional[AliquotLocation]:
        return (
            self.session.query(AliquotLocation)
            .filter(AliquotLocation.aliquot_id == aliquot_id)
            .first()
        )

    def get_by_position(self, position_id: int) -> Optional[AliquotLocation]:
        return (
            self.session.query(AliquotLocation)
            .filter(AliquotLocation.position_id == position_id)
            .first()
        )

    def get_unplaced_aliquots(self, search: str = "") -> List[SampleAliquot]:
        """
        Return aliquots that are available to be placed in a box.

        Conditions:
          - is_available = True
          - is_shipped   = False
          - no AliquotLocation record exists (outerjoin + NULL check)
        """
        query = (
            self.session.query(SampleAliquot)
            .outerjoin(SampleAliquot.location)
            .filter(
                SampleAliquot.is_available == True,
                SampleAliquot.is_shipped   == False,
                AliquotLocation.id         == None,
            )
            .options(
                joinedload(SampleAliquot.sample)
                .joinedload(Sample.participant)
            )
            .order_by(SampleAliquot.aliquot_id)
        )

        if search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                SampleAliquot.aliquot_id.ilike(term)
                | Participant.pid.ilike(term)
            ).join(SampleAliquot.sample).join(Sample.participant)

        return query.all()

"""
Storage Service — Freezer, Compartment, Rack, Drawer, Box, Position, and
                  Aliquot location management.

Hierarchy:  Freezer → Compartment → Rack → Drawer → Box → Position
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.models.models import (
    AliquotLocation, BoxPosition, Compartment, Freezer,
    SampleAliquot, StorageBox, StorageDrawer, StorageRack,
)
from app.core.repositories.storage_repository import (
    AliquotLocationRepository, BoxPositionRepository,
    CompartmentRepository, FreezerRepository,
    StorageBoxRepository, StorageDrawerRepository, StorageRackRepository,
)
from app.core.services.audit_service import log
from app.core.services.auth_service import app_session
from app.config import AuditAction, BOX_GRID_SIZES


class StorageService:

    def __init__(self, session: Session) -> None:
        self.session        = session
        self.freezer_repo   = FreezerRepository(session)
        self.comp_repo      = CompartmentRepository(session)
        self.rack_repo      = StorageRackRepository(session)
        self.drawer_repo    = StorageDrawerRepository(session)
        self.box_repo       = StorageBoxRepository(session)
        self.position_repo  = BoxPositionRepository(session)
        self.location_repo  = AliquotLocationRepository(session)

    # ════════════════════════════════════════════════════════════════════
    # FREEZER
    # ════════════════════════════════════════════════════════════════════

    def create_freezer(
        self,
        name: str,
        location: str = "",
        temperature: str = "",
        capacity_boxes: Optional[int] = None,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[Freezer]]:
        app_session.require("storage.create")

        name = name.strip()
        if not name:
            return False, "Freezer name is required.", None
        if self.freezer_repo.name_exists(name):
            return False, f"Freezer '{name}' already exists.", None

        freezer = Freezer(
            name=name,
            location=location.strip(),
            temperature=temperature.strip(),
            capacity_boxes=capacity_boxes,
            notes=notes.strip(),
        )
        self.freezer_repo.add(freezer)
        log(self.session, AuditAction.CREATE, "Freezer", str(freezer.id),
            f"Freezer '{name}' created.")
        return True, "Freezer created.", freezer

    def update_freezer(
        self, freezer_id: int, **fields
    ) -> Tuple[bool, str]:
        app_session.require("storage.edit")
        freezer = self.freezer_repo.get_by_id(freezer_id)
        if not freezer:
            return False, "Freezer not found."
        if freezer.is_locked:
            return False, "Freezer is locked."

        allowed = {"name", "location", "temperature", "capacity_boxes", "notes"}
        for k, v in fields.items():
            if k in allowed:
                setattr(freezer, k, v)
        self.freezer_repo.update(freezer)
        log(self.session, AuditAction.UPDATE, "Freezer", str(freezer_id),
            f"Freezer '{freezer.name}' updated.")
        return True, "Freezer updated."

    def get_all_freezers(self) -> List[Freezer]:
        return self.freezer_repo.get_all_with_hierarchy()

    def set_freezer_lock(self, freezer_id: int, locked: bool) -> Tuple[bool, str]:
        app_session.require("storage.edit")
        freezer = self.freezer_repo.get_by_id(freezer_id)
        if not freezer:
            return False, "Freezer not found."
        freezer.is_locked = locked
        self.freezer_repo.update(freezer)
        action = "locked" if locked else "unlocked"
        log(self.session, AuditAction.UPDATE, "Freezer", str(freezer_id),
            f"Freezer '{freezer.name}' {action}.")
        return True, f"Freezer {action}."

    # ════════════════════════════════════════════════════════════════════
    # COMPARTMENT
    # ════════════════════════════════════════════════════════════════════

    def create_compartment(
        self,
        name: str,
        freezer_id: int,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[Compartment]]:
        app_session.require("storage.create")

        name = name.strip()
        if not name:
            return False, "Compartment name is required.", None
        freezer = self.freezer_repo.get_by_id(freezer_id)
        if not freezer:
            return False, "Freezer not found.", None
        if freezer.is_locked:
            return False, "Freezer is locked.", None
        if self.comp_repo.name_exists_in_freezer(name, freezer_id):
            return False, f"Compartment '{name}' already exists in this freezer.", None

        comp = Compartment(name=name, freezer_id=freezer_id, notes=notes.strip())
        self.comp_repo.add(comp)
        log(self.session, AuditAction.CREATE, "Compartment", str(comp.id),
            f"Compartment '{name}' created in freezer '{freezer.name}'.")
        return True, "Compartment created.", comp

    def update_compartment(self, comp_id: int, **fields) -> Tuple[bool, str]:
        app_session.require("storage.edit")
        comp = self.comp_repo.get_by_id(comp_id)
        if not comp:
            return False, "Compartment not found."
        for k, v in fields.items():
            if k in {"name", "notes"}:
                setattr(comp, k, v)
        self.comp_repo.update(comp)
        return True, "Compartment updated."

    # ════════════════════════════════════════════════════════════════════
    # RACK
    # ════════════════════════════════════════════════════════════════════

    def create_rack(
        self,
        name: str,
        compartment_id: int,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[StorageRack]]:
        app_session.require("storage.create")

        name = name.strip()
        if not name:
            return False, "Rack name is required.", None
        comp = self.comp_repo.get_by_id(compartment_id)
        if not comp:
            return False, "Compartment not found.", None
        if self.rack_repo.name_exists_in_compartment(name, compartment_id):
            return False, f"Rack '{name}' already exists in this compartment.", None

        rack = StorageRack(name=name, compartment_id=compartment_id, notes=notes.strip())
        self.rack_repo.add(rack)
        log(self.session, AuditAction.CREATE, "StorageRack", str(rack.id),
            f"Rack '{name}' created in compartment '{comp.name}'.")
        return True, "Rack created.", rack

    def update_rack(self, rack_id: int, **fields) -> Tuple[bool, str]:
        app_session.require("storage.edit")
        rack = self.rack_repo.get_by_id(rack_id)
        if not rack:
            return False, "Rack not found."
        for k, v in fields.items():
            if k in {"name", "notes"}:
                setattr(rack, k, v)
        self.rack_repo.update(rack)
        return True, "Rack updated."

    # ════════════════════════════════════════════════════════════════════
    # DRAWER
    # ════════════════════════════════════════════════════════════════════

    def create_drawer(
        self,
        name: str,
        rack_id: int,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[StorageDrawer]]:
        app_session.require("storage.create")

        name = name.strip()
        if not name:
            return False, "Drawer name is required.", None
        rack = self.rack_repo.get_by_id(rack_id)
        if not rack:
            return False, "Rack not found.", None
        if self.drawer_repo.name_exists_in_rack(name, rack_id):
            return False, f"Drawer '{name}' already exists in this rack.", None

        drawer = StorageDrawer(name=name, rack_id=rack_id, notes=notes.strip())
        self.drawer_repo.add(drawer)
        log(self.session, AuditAction.CREATE, "StorageDrawer", str(drawer.id),
            f"Drawer '{name}' created in rack '{rack.name}'.")
        return True, "Drawer created.", drawer

    def update_drawer(self, drawer_id: int, **fields) -> Tuple[bool, str]:
        app_session.require("storage.edit")
        drawer = self.drawer_repo.get_by_id(drawer_id)
        if not drawer:
            return False, "Drawer not found."
        for k, v in fields.items():
            if k in {"name", "notes"}:
                setattr(drawer, k, v)
        self.drawer_repo.update(drawer)
        return True, "Drawer updated."

    # ════════════════════════════════════════════════════════════════════
    # BOX
    # ════════════════════════════════════════════════════════════════════

    def create_box(
        self,
        name: str,
        drawer_id: int,
        rows: int = 9,
        cols: int = 9,
        study_id: Optional[int] = None,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[StorageBox]]:
        app_session.require("storage.create")

        name = name.strip()
        if not name:
            return False, "Box name is required.", None

        drawer = self.drawer_repo.get_by_id(drawer_id)
        if not drawer:
            return False, "Drawer not found.", None
        if self.box_repo.name_exists_in_drawer(name, drawer_id):
            return False, f"Box '{name}' already exists in this drawer.", None
        if rows < 1 or cols < 1 or rows > 20 or cols > 20:
            return False, "Grid size must be between 1×1 and 20×20.", None

        box = StorageBox(
            name=name,
            drawer_id=drawer_id,
            rows=rows,
            cols=cols,
            study_id=study_id,
            notes=notes.strip(),
        )
        self.box_repo.add(box)  # flush → box.id is now set

        # Pre-populate every grid position as an empty BoxPosition row.
        for r in range(rows):
            for c in range(cols):
                self.session.add(BoxPosition(
                    box_id=box.id, row=r, col=c
                ))
        self.session.flush()

        log(self.session, AuditAction.CREATE, "StorageBox", str(box.id),
            f"Box '{name}' ({rows}×{cols}) created in drawer '{drawer.name}'.")
        return True, "Box created.", box

    def duplicate_box(
        self, source_box_id: int, new_name: str, target_drawer_id: int
    ) -> Tuple[bool, str, Optional[StorageBox]]:
        """Copy a box layout (dimensions only, not contents)."""
        app_session.require("storage.create")
        source = self.box_repo.get_by_id(source_box_id)
        if not source:
            return False, "Source box not found.", None
        return self.create_box(
            name=new_name,
            drawer_id=target_drawer_id,
            rows=source.rows,
            cols=source.cols,
            study_id=source.study_id,
        )

    def get_box_grid(self, box_id: int) -> Optional[StorageBox]:
        """Return box with all positions and their aliquot data loaded."""
        return self.box_repo.get_with_positions(box_id)

    # ════════════════════════════════════════════════════════════════════
    # ALIQUOT PLACEMENT
    # ════════════════════════════════════════════════════════════════════

    def place_aliquot(
        self,
        aliquot_id: int,
        box_id: int,
        row: int,
        col: int,
    ) -> Tuple[bool, str]:
        app_session.require("storage.edit")

        aliquot = self.session.get(SampleAliquot, aliquot_id)
        if not aliquot:
            return False, "Aliquot not found."
        if not aliquot.is_available:
            return False, "Aliquot is not available."
        if aliquot.is_shipped:
            return False, "Aliquot has already been shipped."

        position = self.position_repo.get_position(box_id, row, col)
        if not position:
            return False, "Position not found."
        if self.location_repo.get_by_position(position.id):
            return False, "Position is already occupied."

        existing = self.location_repo.get_by_aliquot(aliquot_id)
        if existing:
            return False, "Aliquot is already located in another position."

        # Get box hierarchy for denormalization
        box = self.box_repo.get_by_id(box_id)
        drawer = self.drawer_repo.get_by_id(box.drawer_id) if box else None
        rack = self.rack_repo.get_by_id(drawer.rack_id) if drawer else None
        compartment = self.comp_repo.get_by_id(rack.compartment_id) if rack else None
        freezer = self.freezer_repo.get_by_id(compartment.freezer_id) if compartment else None

        loc = AliquotLocation(
            aliquot_id=aliquot_id,
            position_id=position.id,
            freezer_name=freezer.name if freezer else None,
            compartment_name=compartment.name if compartment else None,
            rack_name=rack.name if rack else None,
            drawer_name=drawer.name if drawer else None,
            box_name=box.name if box else None,
        )
        self.location_repo.add(loc)
        log(self.session, AuditAction.MOVE, "AliquotLocation",
            str(aliquot_id),
            f"Aliquot {aliquot.aliquot_id} placed at box={box_id} [{row},{col}].")
        return True, "Aliquot placed."

    def move_aliquot(
        self,
        aliquot_id: int,
        target_box_id: int,
        target_row: int,
        target_col: int,
        reason: str = "",
    ) -> Tuple[bool, str]:
        app_session.require("storage.edit")

        if not reason.strip():
            return False, "A reason is required for moving a sample."

        existing = self.location_repo.get_by_aliquot(aliquot_id)
        if not existing:
            return False, "Aliquot is not currently located anywhere."

        target_pos = self.position_repo.get_position(
            target_box_id, target_row, target_col
        )
        if not target_pos:
            return False, "Target position not found."
        if self.location_repo.get_by_position(target_pos.id):
            return False, "Target position is already occupied."

        self.location_repo.delete(existing)

        # Get target box hierarchy
        target_box = self.box_repo.get_by_id(target_box_id)
        target_drawer = self.drawer_repo.get_by_id(target_box.drawer_id) if target_box else None
        target_rack = self.rack_repo.get_by_id(target_drawer.rack_id) if target_drawer else None
        target_compartment = self.comp_repo.get_by_id(target_rack.compartment_id) if target_rack else None
        target_freezer = self.freezer_repo.get_by_id(target_compartment.freezer_id) if target_compartment else None

        self.session.add(AliquotLocation(
            aliquot_id=aliquot_id,
            position_id=target_pos.id,
            moved_reason=reason,
            freezer_name=target_freezer.name if target_freezer else None,
            compartment_name=target_compartment.name if target_compartment else None,
            rack_name=target_rack.name if target_rack else None,
            drawer_name=target_drawer.name if target_drawer else None,
            box_name=target_box.name if target_box else None,
        ))
        self.session.flush()

        aliquot = self.session.get(SampleAliquot, aliquot_id)
        log(self.session, AuditAction.MOVE, "AliquotLocation", str(aliquot_id),
            f"Aliquot {aliquot.aliquot_id} moved to box={target_box_id} "
            f"[{target_row},{target_col}]. Reason: {reason}")
        return True, "Aliquot moved."

    def remove_aliquot_from_position(
        self, aliquot_id: int, reason: str = ""
    ) -> Tuple[bool, str]:
        app_session.require("storage.edit")
        existing = self.location_repo.get_by_aliquot(aliquot_id)
        if not existing:
            return False, "Aliquot is not currently located anywhere."
        self.location_repo.delete(existing)
        log(self.session, AuditAction.MOVE, "AliquotLocation", str(aliquot_id),
            f"Aliquot removed from position. Reason: {reason}")
        return True, "Aliquot removed from position."

    def delete_freezer(self, freezer_id: int) -> Tuple[bool, str]:
        """Delete a freezer and all its contents."""
        app_session.require("storage.edit")
        try:
            freezer = self.session.get(Freezer, freezer_id)
            if not freezer:
                return False, "Freezer not found."
            
            self.session.delete(freezer)
            self.session.commit()
            log(self.session, AuditAction.DELETE, "Freezer", str(freezer_id), f"Deleted freezer: {freezer.name}")
            return True, "Freezer deleted."
        except Exception as e:
            self.session.rollback()
            return False, f"Error deleting freezer: {str(e)}"

    def delete_compartment(self, compartment_id: int) -> Tuple[bool, str]:
        """Delete a compartment and all its contents."""
        app_session.require("storage.edit")
        try:
            compartment = self.session.get(Compartment, compartment_id)
            if not compartment:
                return False, "Compartment not found."
            
            self.session.delete(compartment)
            self.session.commit()
            log(self.session, AuditAction.DELETE, "Compartment", str(compartment_id), f"Deleted compartment: {compartment.name}")
            return True, "Compartment deleted."
        except Exception as e:
            self.session.rollback()
            return False, f"Error deleting compartment: {str(e)}"

    def delete_rack(self, rack_id: int) -> Tuple[bool, str]:
        """Delete a rack and all its contents."""
        app_session.require("storage.edit")
        try:
            rack = self.session.get(StorageRack, rack_id)
            if not rack:
                return False, "Rack not found."
            
            self.session.delete(rack)
            self.session.commit()
            log(self.session, AuditAction.DELETE, "StorageRack", str(rack_id), f"Deleted rack: {rack.name}")
            return True, "Rack deleted."
        except Exception as e:
            self.session.rollback()
            return False, f"Error deleting rack: {str(e)}"

    def delete_drawer(self, drawer_id: int) -> Tuple[bool, str]:
        """Delete a drawer and all its contents."""
        app_session.require("storage.edit")
        try:
            drawer = self.session.get(StorageDrawer, drawer_id)
            if not drawer:
                return False, "Drawer not found."
            
            self.session.delete(drawer)
            self.session.commit()
            log(self.session, AuditAction.DELETE, "StorageDrawer", str(drawer_id), f"Deleted drawer: {drawer.name}")
            return True, "Drawer deleted."
        except Exception as e:
            self.session.rollback()
            return False, f"Error deleting drawer: {str(e)}"

    def delete_box(self, box_id: int) -> Tuple[bool, str]:
        """Delete a box."""
        app_session.require("storage.edit")
        try:
            box = self.session.get(StorageBox, box_id)
            if not box:
                return False, "Box not found."
            
            self.session.delete(box)
            self.session.commit()
            log(self.session, AuditAction.DELETE, "StorageBox", str(box_id), f"Deleted box: {box.name}")
            return True, "Box deleted."
        except Exception as e:
            self.session.rollback()
            return False, f"Error deleting box: {str(e)}"
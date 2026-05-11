"""
CBMS — SQLAlchemy ORM models (SQLite backend).

Table hierarchy:
  User  ←─ AuditLog
  Study ←─ Participant ←─ Sample ←─ SampleAliquot ←─ AliquotLocation
  Freezer ←─ Compartment ←─ Rack ←─ Drawer ←─ StorageBox ←─ BoxPosition
  Shipment ←─ ShipmentItem
  SampleBlock
"""

from __future__ import annotations

import datetime as dt
from typing import Optional, List

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint, event
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ── Base ───────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


# ══════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════

class User(Base):
    """Registered application user."""
    __tablename__ = "users"

    id: Mapped[int]          = mapped_column(Integer, primary_key=True)
    username: Mapped[str]    = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str]       = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str]        = mapped_column(String(32), nullable=False)   # PI / MANAGER / LAB_TECH
    is_active: Mapped[bool]  = mapped_column(Boolean, default=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    last_login: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)

    # Study co-ownership (many-to-many via association)
    co_owned_studies: Mapped[List["StudyCoOwner"]] = relationship(back_populates="user")
    audit_logs: Mapped[List["AuditLog"]]            = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.username} [{self.role}]>"


class StudyCoOwner(Base):
    """Association: user co-owns a study (admin-assigned)."""
    __tablename__ = "study_co_owners"

    id: Mapped[int]       = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int]  = mapped_column(ForeignKey("users.id"), nullable=False)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), nullable=False)

    user: Mapped["User"]   = relationship(back_populates="co_owned_studies")
    study: Mapped["Study"] = relationship(back_populates="co_owners")

    __table_args__ = (UniqueConstraint("user_id", "study_id"),)


# ══════════════════════════════════════════════════════════════════════════
# STUDY / PROJECT
# ══════════════════════════════════════════════════════════════════════════

class Study(Base):
    """A research study / project."""
    __tablename__ = "studies"

    id: Mapped[int]              = mapped_column(Integer, primary_key=True)
    project_id_short: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str]            = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    site_name: Mapped[Optional[str]]   = mapped_column(String(128), nullable=True)
    pi_name: Mapped[Optional[str]]     = mapped_column(String(128), nullable=True)
    start_date: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[dt.datetime]]   = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    participants: Mapped[List["Participant"]] = relationship(back_populates="study", cascade="all, delete-orphan")
    co_owners:    Mapped[List["StudyCoOwner"]] = relationship(back_populates="study", cascade="all, delete-orphan")
    visits:       Mapped[List["VisitDefinition"]] = relationship(back_populates="study", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Study {self.project_id_short}: {self.name}>"


class VisitDefinition(Base):
    """Named visit timepoints for a study (e.g. Baseline, Month-3)."""
    __tablename__ = "visit_definitions"

    id: Mapped[int]       = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), nullable=False)
    visit_name: Mapped[str]  = mapped_column(String(64), nullable=False)
    visit_code: Mapped[str]  = mapped_column(String(16), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    study: Mapped["Study"] = relationship(back_populates="visits")


# ══════════════════════════════════════════════════════════════════════════
# PARTICIPANT
# ══════════════════════════════════════════════════════════════════════════

class Participant(Base):
    """
    A study participant. PID is user-provided (not auto-generated).
    Auto-increment id is used internally for joins but not exposed.
    """
    __tablename__ = "participants"

    id: Mapped[int]        = mapped_column(Integer, primary_key=True)
    pid: Mapped[str]       = mapped_column(String(32), nullable=False, index=True)  # User-provided
    study_id: Mapped[int]  = mapped_column(ForeignKey("studies.id"), nullable=False)

    # Demographics — match Excel column names
    age: Mapped[Optional[int]]               = mapped_column(Integer,     nullable=True)
    gender: Mapped[Optional[str]]            = mapped_column(String(32),  nullable=True)  # Male/Female/Transgender
    population: Mapped[Optional[str]]        = mapped_column(String(64),  nullable=True)  # FSW/MSM/PWID/etc
    disease: Mapped[Optional[str]]           = mapped_column(String(128), nullable=True)  # Diabetes/TB/None/etc
    cohort_name: Mapped[Optional[str]]       = mapped_column(String(64),  nullable=True)  # HIV UNINFECTED/etc
    site_name: Mapped[Optional[str]]         = mapped_column(String(128), nullable=True)  # GHTM/ICMAR-NARI/etc

    # Legacy fields (kept for backward compat)
    initials: Mapped[Optional[str]]          = mapped_column(String(8),  nullable=True)
    date_of_birth: Mapped[Optional[dt.datetime]] = mapped_column(DateTime,    nullable=True)
    comorbidity: Mapped[Optional[str]]       = mapped_column(Text,        nullable=True)
    notes: Mapped[Optional[str]]             = mapped_column(Text,        nullable=True)

    # Audit
    edit_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime]    = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime]    = mapped_column(DateTime, default=_now, onupdate=_now)

    study: Mapped["Study"]           = relationship(back_populates="participants")
    samples: Mapped[List["Sample"]]  = relationship(back_populates="participant", cascade="all, delete-orphan")
    custom_fields: Mapped[List["ParticipantCustomField"]] = relationship(back_populates="participant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Participant {self.pid}>"


class ParticipantCustomField(Base):
    """Admin-defined custom fields per participant."""
    __tablename__ = "participant_custom_fields"

    id: Mapped[int]             = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), nullable=False)
    field_name: Mapped[str]     = mapped_column(String(64), nullable=False)
    field_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    participant: Mapped["Participant"] = relationship(back_populates="custom_fields")


# ══════════════════════════════════════════════════════════════════════════
# SAMPLE
# ══════════════════════════════════════════════════════════════════════════

class Sample(Base):
    """
    A biological sample collected from a participant at a visit.
    Maps to Excel: Date Collected, Visit Code, Visit Time, Visit Name, Sample Type
    """
    __tablename__ = "samples"

    id: Mapped[int]             = mapped_column(Integer, primary_key=True)
    sample_id: Mapped[str]      = mapped_column(String(32), unique=True, nullable=False, index=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), nullable=False)
    study_id: Mapped[int]       = mapped_column(ForeignKey("studies.id"), nullable=False)
    visit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("visit_definitions.id"), nullable=True)

    # Excel columns — Sample details
    sample_type: Mapped[str]               = mapped_column(String(64), nullable=False)   # Serum/ED Plasma/Hep Plasma/PBMC
    collection_date: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    visit_code: Mapped[Optional[str]]          = mapped_column(String(16), nullable=True)   # SCR(NA)/M0/etc
    visit_time: Mapped[Optional[str]]          = mapped_column(String(16), nullable=True)   # Visit time in form of decimal
    visit_name: Mapped[Optional[str]]          = mapped_column(String(64), nullable=True)  # Screening/Enrollment/Follow-up
    
    # Legacy fields (kept for compatibility)
    collected_volume_ml: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    collection_site: Mapped[Optional[str]]       = mapped_column(String(128), nullable=True)
    condition: Mapped[Optional[str]]             = mapped_column(String(64), nullable=True)   # Fresh/Frozen/…
    notes: Mapped[Optional[str]]                 = mapped_column(Text, nullable=True)

    # Audit
    edit_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime]    = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime]    = mapped_column(DateTime, default=_now, onupdate=_now)

    participant: Mapped["Participant"]         = relationship(back_populates="samples")
    visit: Mapped[Optional["VisitDefinition"]] = relationship()
    aliquots: Mapped[List["SampleAliquot"]]    = relationship(back_populates="sample", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Sample {self.sample_id} [{self.sample_type}]>"


class SampleAliquot(Base):
    """
    An individual aliquot derived from a Sample.
    Maps to Excel: Aliquot ID, Descripancy Remark, Descripancy For
    """
    __tablename__ = "sample_aliquots"

    id: Mapped[int]         = mapped_column(Integer, primary_key=True)
    aliquot_id: Mapped[str] = mapped_column(String(48), unique=True, nullable=False, index=True)
    sample_id: Mapped[int]  = mapped_column(ForeignKey("samples.id"), nullable=False)

    aliquot_number: Mapped[int]               = mapped_column(Integer, nullable=False)   # 1, 2, 3…
    volume_ul: Mapped[Optional[float]]        = mapped_column(Float, nullable=True)       # µL
    concentration: Mapped[Optional[float]]    = mapped_column(Float, nullable=True)
    legacy_id: Mapped[Optional[str]]          = mapped_column(String(64), nullable=True)  # original system's Unique ID
    
    # Excel discrepancy fields
    discrepancy_remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)        # Descripancy Remark column
    discrepancy_field: Mapped[Optional[str]]  = mapped_column(String(64), nullable=True)  # Descripancy For column
    
    is_available: Mapped[bool]                = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool]                  = mapped_column(Boolean, default=False)
    is_shipped: Mapped[bool]                  = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime]           = mapped_column(DateTime, default=_now)

    sample: Mapped["Sample"]                       = relationship(back_populates="aliquots")
    location: Mapped[Optional["AliquotLocation"]]  = relationship(back_populates="aliquot", uselist=False, cascade="all, delete-orphan")
    block: Mapped[Optional["SampleBlock"]]         = relationship(back_populates="aliquot", uselist=False)

    def __repr__(self) -> str:
        return f"<Aliquot {self.aliquot_id}>"


# ══════════════════════════════════════════════════════════════════════════
# STORAGE
# ══════════════════════════════════════════════════════════════════════════

class Freezer(Base):
    """A physical freezer unit."""
    __tablename__ = "freezers"

    id: Mapped[int]      = mapped_column(Integer, primary_key=True)
    name: Mapped[str]    = mapped_column(String(128), unique=True, nullable=False)
    location: Mapped[Optional[str]]    = mapped_column(String(256), nullable=True)
    temperature: Mapped[Optional[str]] = mapped_column(String(16),  nullable=True)  # e.g. -80°C
    capacity_boxes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    compartments: Mapped[List["Compartment"]] = relationship(back_populates="freezer", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Freezer {self.name}>"


class Compartment(Base):
    """A compartment (section/shelf-group) inside a freezer."""
    __tablename__ = "compartments"

    id: Mapped[int]         = mapped_column(Integer, primary_key=True)
    name: Mapped[str]       = mapped_column(String(128), nullable=False)
    freezer_id: Mapped[int] = mapped_column(ForeignKey("freezers.id"), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    freezer: Mapped["Freezer"]      = relationship(back_populates="compartments")
    racks: Mapped[List["StorageRack"]] = relationship(back_populates="compartment", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("name", "freezer_id"),)

    def __repr__(self) -> str:
        return f"<Compartment {self.name}>"


class StorageRack(Base):
    """A rack inside a compartment."""
    __tablename__ = "storage_racks"

    id: Mapped[int]             = mapped_column(Integer, primary_key=True)
    name: Mapped[str]           = mapped_column(String(128), nullable=False)
    compartment_id: Mapped[int] = mapped_column(ForeignKey("compartments.id"), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    compartment: Mapped["Compartment"]    = relationship(back_populates="racks")
    drawers: Mapped[List["StorageDrawer"]] = relationship(back_populates="rack", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("name", "compartment_id"),)

    def __repr__(self) -> str:
        return f"<StorageRack {self.name}>"


class StorageDrawer(Base):
    """A drawer inside a rack."""
    __tablename__ = "storage_drawers"

    id: Mapped[int]      = mapped_column(Integer, primary_key=True)
    name: Mapped[str]    = mapped_column(String(128), nullable=False)
    rack_id: Mapped[int] = mapped_column(ForeignKey("storage_racks.id"), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    rack: Mapped["StorageRack"]        = relationship(back_populates="drawers")
    boxes: Mapped[List["StorageBox"]]  = relationship(back_populates="drawer", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("name", "rack_id"),)

    def __repr__(self) -> str:
        return f"<StorageDrawer {self.name}>"


class StorageBox(Base):
    """A storage box inside a drawer, with a defined grid layout."""
    __tablename__ = "storage_boxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    drawer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("storage_drawers.id"), nullable=True)
    parent_box_id: Mapped[Optional[int]] = mapped_column(ForeignKey("storage_boxes.id"), nullable=True)  # ← NEW
    
    rows: Mapped[int] = mapped_column(Integer, default=10)
    cols: Mapped[int] = mapped_column(Integer, default=10)
    
    # Relationships
    drawer: Mapped[Optional["StorageDrawer"]] = relationship(back_populates="boxes", foreign_keys=[drawer_id])
    parent_box: Mapped[Optional["StorageBox"]] = relationship("StorageBox", remote_side=[id], back_populates="child_boxes", foreign_keys=[parent_box_id])  # ← NEW
    child_boxes: Mapped[List["StorageBox"]] = relationship("StorageBox", back_populates="parent_box", foreign_keys=[parent_box_id], cascade="all, delete-orphan")  # ← NEW
    
    positions: Mapped[List["BoxPosition"]] = relationship(back_populates="box", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("name", "drawer_id"),)

    @property
    def total_positions(self) -> int:
        return self.rows * self.cols

    @property
    def occupied_positions(self) -> int:
        return sum(1 for p in self.positions if p.aliquot_location is not None)

    def __repr__(self) -> str:
        return f"<StorageBox {self.name} [{self.rows}×{self.cols}]>"


class BoxPosition(Base):
    """A single cell in the StorageBox grid."""
    __tablename__ = "box_positions"

    id: Mapped[int]      = mapped_column(Integer, primary_key=True)
    box_id: Mapped[int]  = mapped_column(ForeignKey("storage_boxes.id"), nullable=False)
    row: Mapped[int]     = mapped_column(Integer, nullable=False)   # 0-indexed
    col: Mapped[int]     = mapped_column(Integer, nullable=False)   # 0-indexed

    box: Mapped["StorageBox"]                            = relationship(back_populates="positions")
    aliquot_location: Mapped[Optional["AliquotLocation"]] = relationship(back_populates="position", uselist=False)

    __table_args__ = (UniqueConstraint("box_id", "row", "col"),)

    def __repr__(self) -> str:
        return f"<BoxPosition box={self.box_id} [{self.row},{self.col}]>"


class AliquotLocation(Base):
    """
    Maps an aliquot to its physical position in a box.
    Stores denormalized storage hierarchy for Excel export:
    Freezer/Tank, Container (Compartment/Rack/Drawer), Slot Position (Box), Position (Row/Col)
    """
    __tablename__ = "aliquot_locations"

    id: Mapped[int]          = mapped_column(Integer, primary_key=True)
    aliquot_id: Mapped[int]  = mapped_column(ForeignKey("sample_aliquots.id"), unique=True, nullable=False)
    position_id: Mapped[int] = mapped_column(ForeignKey("box_positions.id"),   unique=True, nullable=False)
    
    # Denormalized hierarchy for Excel export (optional, can be computed from position.box)
    freezer_name: Mapped[Optional[str]]     = mapped_column(String(128), nullable=True)
    compartment_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    rack_name: Mapped[Optional[str]]        = mapped_column(String(128), nullable=True)
    drawer_name: Mapped[Optional[str]]      = mapped_column(String(128), nullable=True)
    box_name: Mapped[Optional[str]]         = mapped_column(String(128), nullable=True)
    
    stored_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    moved_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    aliquot:  Mapped["SampleAliquot"] = relationship(back_populates="location")
    position: Mapped["BoxPosition"]   = relationship(back_populates="aliquot_location")


# ══════════════════════════════════════════════════════════════════════════
# BLOCKING & SHIPMENT
# ══════════════════════════════════════════════════════════════════════════

class SampleBlock(Base):
    """Locks an aliquot for a researcher for a defined period."""
    __tablename__ = "sample_blocks"

    id: Mapped[int]          = mapped_column(Integer, primary_key=True)
    aliquot_id: Mapped[int]  = mapped_column(ForeignKey("sample_aliquots.id"), unique=True, nullable=False)
    blocked_by: Mapped[str]  = mapped_column(String(64), nullable=False)   # researcher name/id
    blocked_at: Mapped[dt.datetime]  = mapped_column(DateTime, default=_now)
    unblock_at: Mapped[dt.datetime]  = mapped_column(DateTime, nullable=False)
    reason: Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    is_released: Mapped[bool]        = mapped_column(Boolean, default=False)
    released_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)

    aliquot: Mapped["SampleAliquot"] = relationship(back_populates="block")


class Shipment(Base):
    """A batch shipment of aliquots to a researcher."""
    __tablename__ = "shipments"

    id: Mapped[int]           = mapped_column(Integer, primary_key=True)
    shipment_ref: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    recipient_name: Mapped[str]    = mapped_column(String(128), nullable=False)
    recipient_institution: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    recipient_email: Mapped[Optional[str]]       = mapped_column(String(128), nullable=True)
    shipped_by: Mapped[str]        = mapped_column(String(64), nullable=False)
    shipped_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    courier: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]]   = mapped_column(Text, nullable=True)

    items: Mapped[List["ShipmentItem"]] = relationship(back_populates="shipment", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Shipment {self.shipment_ref}>"


class ShipmentItem(Base):
    """One aliquot in a shipment."""
    __tablename__ = "shipment_items"

    id: Mapped[int]           = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int]  = mapped_column(ForeignKey("shipments.id"), nullable=False)
    aliquot_id: Mapped[int]   = mapped_column(ForeignKey("sample_aliquots.id"), nullable=False)

    shipment: Mapped["Shipment"]        = relationship(back_populates="items")
    aliquot: Mapped["SampleAliquot"]    = relationship()


# ══════════════════════════════════════════════════════════════════════════
# AUDIT
# ══════════════════════════════════════════════════════════════════════════

class AuditLog(Base):
    """Immutable record of every significant action in the system."""
    __tablename__ = "audit_logs"

    id: Mapped[int]           = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str]       = mapped_column(String(32), nullable=False)   # AuditAction constant
    entity_type: Mapped[str]  = mapped_column(String(64), nullable=False)   # e.g. "Sample"
    entity_id: Mapped[Optional[str]]  = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[dt.datetime]     = mapped_column(DateTime, default=_now, index=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")


# ══════════════════════════════════════════════════════════════════════════
# CUSTOM FIELD DEFINITIONS (admin-managed)
# ══════════════════════════════════════════════════════════════════════════

class CustomFieldDefinition(Base):
    """Admin can define extra fields that appear on participant forms."""
    __tablename__ = "custom_field_definitions"

    id: Mapped[int]        = mapped_column(Integer, primary_key=True)
    field_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    field_label: Mapped[str] = mapped_column(String(128), nullable=False)
    field_type: Mapped[str]  = mapped_column(String(32), default="text")   # text/number/date/select
    is_active: Mapped[bool]  = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

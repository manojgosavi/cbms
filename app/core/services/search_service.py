"""
Search Service — multi-criteria AND/OR search across the full sample catalogue.

Key concept — building dynamic queries:
  SQLAlchemy conditions are Python objects, not strings.
  We collect them in a list, then combine at the end:

    conditions = [Participant.age >= 30, Participant.sex == "Male"]
    query.filter(and_(*conditions))   # AND mode
    query.filter(or_(*conditions))    # OR mode

  This means we never build SQL strings manually — no injection risk,
  and the query adapts to any combination of filled/empty filter fields.

Key concept — joined queries:
  Our data spans multiple tables: Participant → Sample → SampleAliquot →
  AliquotLocation → BoxPosition → StorageBox → StorageDrawer → StorageRack →
  Compartment → Freezer.
  We JOIN them so a single search can filter on participant age AND sample type
  AND freezer name all in one query.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.models.models import (
    AliquotLocation, BoxPosition, Compartment, Freezer,
    Participant, Sample, SampleAliquot, StorageBox,
    StorageDrawer, StorageRack, Study,
)


# ── Search filters dataclass ───────────────────────────────────────────────

@dataclass
class SearchFilters:
    # Participant fields
    pid:          Optional[str]  = None
    age:      Optional[int]  = None
    gender:       Optional[str]  = None
    disease:      Optional[str]  = None
    cohort_name:       Optional[str]  = None
    population:   Optional[str]  = None
    site_name:    Optional[str]  = None
    visit_time:   Optional[str] = None

    # Sample fields
    sample_type:          Optional[str]      = None
    visit_code:           Optional[str]      = None
    collection_date_from: Optional[dt.date]  = None
    collection_date_to:   Optional[dt.date]  = None

    # Storage fields — full 6-level hierarchy
    freezer_name:     Optional[str] = None
    compartment_name: Optional[str] = None
    rack_name:        Optional[str] = None
    drawer_name:      Optional[str] = None
    box_name:         Optional[str] = None

    # Aliquot state
    available_only:  bool = False
    blocked_only:    bool = False
    has_discrepancy: bool = False

    # Blank field search
    blank_field: Optional[str] = None

    # Logic mode
    use_or: bool = False


# ── Result row dataclass ───────────────────────────────────────────────────

@dataclass
class SearchResult:
    # Participant
    pid:      str
    age:      Optional[int]
    gender:   Optional[str]
    disease:  Optional[str]
    cohort:   Optional[str]
    site_name: Optional[str]
    visit_time: Optional[str]

    # Sample
    sample_id:       str
    sample_type:     str
    collection_date: Optional[dt.date]
    visit_name:      Optional[str]

    # Aliquot
    aliquot_id:         str
    aliquot_db_id:      int
    volume_ul:          Optional[float]
    is_blocked:         bool
    is_shipped:         bool
    is_available:       bool
    discrepancy_remark: Optional[str]

    # Location — full hierarchy
    freezer_name:     Optional[str]
    compartment_name: Optional[str]
    rack_name:        Optional[str]
    drawer_name:      Optional[str]
    box_name:         Optional[str]
    position_row:     Optional[int]
    position_col:     Optional[int]


class SearchService:

    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self,
        filters: SearchFilters,
        page: int = 1,
        page_size: int = 200,
    ) -> Tuple[List[SearchResult], int]:
        """
        Execute a multi-criteria search.
        Returns (results, total_count).

        LEFT OUTER JOINs are used for storage so samples without a location
        still appear in results.
        """

        q = (
            self.session.query(
                Participant, Sample, SampleAliquot,
                AliquotLocation, BoxPosition, StorageBox,
                StorageDrawer, StorageRack, Compartment, Freezer,
            )
            .join(Sample,        Sample.participant_id == Participant.id)
            .join(SampleAliquot, SampleAliquot.sample_id == Sample.id)
            .outerjoin(AliquotLocation, AliquotLocation.aliquot_id == SampleAliquot.id)
            .outerjoin(BoxPosition,     BoxPosition.id == AliquotLocation.position_id)
            .outerjoin(StorageBox,      StorageBox.id == BoxPosition.box_id)
            .outerjoin(StorageDrawer,   StorageDrawer.id == StorageBox.drawer_id)
            .outerjoin(StorageRack,     StorageRack.id == StorageDrawer.rack_id)
            .outerjoin(Compartment,     Compartment.id == StorageRack.compartment_id)
            .outerjoin(Freezer,         Freezer.id == Compartment.freezer_id)
        )

        conditions = []

        # Participant filters
        if filters.pid:
            conditions.append(Participant.pid.ilike(f"%{filters.pid}%"))
        if filters.age is not None:
            conditions.append(Participant.age == filters.age)
        if filters.gender:
            conditions.append(Participant.gender == filters.gender)
        if filters.disease:
            conditions.append(Participant.disease.ilike(f"%{filters.disease}%"))
        if filters.cohort:
            conditions.append(Participant.cohort_name.ilike(f"%{filters.cohort_name}%"))
        if filters.population:
            conditions.append(Participant.population.ilike(f"%{filters.population}%"))
        if filters.site_name:
            conditions.append(Participant.site_name.ilike(f"%{filters.site_name}%"))
        
        # Sample filters
        if filters.sample_type:
            conditions.append(Sample.sample_type.ilike(f"%{filters.sample_type}%"))
        if filters.collection_date_from:
            conditions.append(Sample.collection_date >= filters.collection_date_from)
        if filters.collection_date_to:
            conditions.append(Sample.collection_date <= filters.collection_date_to)
        if filters.visit_time:
            conditions.append(Sample.visit_time == filters.visit_time)

        # Storage filters
        if filters.freezer_name:
            conditions.append(Freezer.name.ilike(f"%{filters.freezer_name}%"))
        if filters.compartment_name:
            conditions.append(Compartment.name.ilike(f"%{filters.compartment_name}%"))
        if filters.rack_name:
            conditions.append(StorageRack.name.ilike(f"%{filters.rack_name}%"))
        if filters.drawer_name:
            conditions.append(StorageDrawer.name.ilike(f"%{filters.drawer_name}%"))
        if filters.box_name:
            conditions.append(StorageBox.name.ilike(f"%{filters.box_name}%"))

        # Aliquot state filters (always AND)
        if filters.available_only:
            q = q.filter(SampleAliquot.is_available == True)
        if filters.blocked_only:
            q = q.filter(SampleAliquot.is_blocked == True)
        if filters.has_discrepancy:
            q = q.filter(SampleAliquot.discrepancy_remark != None)

        # Blank field search
        blank_map = {
            "age":             Participant.age,
            "gender":          Participant.gender,
            "disease":         Participant.disease,
            "cohort":          Participant.cohort_name,
            "collection_date": Sample.collection_date,
            "location":        AliquotLocation.id,
        }
        if filters.blank_field and filters.blank_field in blank_map:
            q = q.filter(blank_map[filters.blank_field] == None)

        if conditions:
            combiner = or_ if filters.use_or else and_
            q = q.filter(combiner(*conditions))

        total = q.count()

        rows = (
            q.order_by(Participant.pid, Sample.collection_date)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        results = []
        for (participant, sample, aliquot, loc, pos, box,
             drawer, rack, compartment, freezer) in rows:
            results.append(SearchResult(
                pid=participant.pid,
                age=participant.age,
                gender=participant.gender,
                disease=participant.disease,
                cohort=participant.cohort_name,
                site_name=participant.site_name,
                visit_time=sample.visit_time,
                sample_id=sample.sample_id,
                sample_type=sample.sample_type,
                collection_date=sample.collection_date,
                visit_name=None,
                aliquot_id=aliquot.aliquot_id,
                aliquot_db_id=aliquot.id,
                volume_ul=aliquot.volume_ul,
                is_blocked=aliquot.is_blocked,
                is_shipped=aliquot.is_shipped,
                is_available=aliquot.is_available,
                discrepancy_remark=aliquot.discrepancy_remark,
                freezer_name=loc.freezer_name if loc else None,
                compartment_name=loc.compartment_name if loc else None,
                rack_name=loc.rack_name if loc else None,
                drawer_name=loc.drawer_name if loc else None,
                box_name=loc.box_name if loc else None,
                position_row=pos.row if pos else None,
                position_col=pos.col if pos else None,
            ))

        return results, total

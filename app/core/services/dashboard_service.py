"""
Dashboard Service — summary statistics for graphs.

Returns plain Python dicts/lists — no ORM objects — so the UI can
use them directly without worrying about session lifetime.

Key concept — aggregation queries with SQLAlchemy:
  func.count() and group_by() let us do GROUP BY in the ORM layer.
  This is much faster than loading all rows and counting in Python.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.models.models import (
    Compartment, Freezer, Participant, Sample, SampleAliquot,
    StorageBox, StorageDrawer, StorageRack, Study,
)


class DashboardService:

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Study summary ──────────────────────────────────────────────────────

    def participants_per_study(self) -> List[Dict]:
        """
        Returns [{"study": "COH — Cohort Study", "count": 42}, ...]
        Useful for a bar chart showing study enrollment.
        """
        rows = (
            self.session.query(
                Study.project_id_short,
                Study.name,
                func.count(Participant.id).label("count"),
            )
            .outerjoin(Participant, Participant.study_id == Study.id)
            .group_by(Study.id)
            .order_by(func.count(Participant.id).desc())
            .all()
        )
        return [
            {"study": f"{r.project_id_short} — {r.name}", "count": r.count}
            for r in rows
        ]

    def samples_by_type(self, study_id: Optional[int] = None) -> List[Dict]:
        """
        Count of samples per type, optionally filtered by study.
        Useful for a pie or bar chart.
        """
        q = (
            self.session.query(
                Sample.sample_type,
                func.count(Sample.id).label("count"),
            )
            .group_by(Sample.sample_type)
            .order_by(func.count(Sample.id).desc())
        )
        if study_id:
            q = q.filter(Sample.study_id == study_id)

        return [{"type": r.sample_type, "count": r.count} for r in q.all()]

    # ── Freezer / storage summary ──────────────────────────────────────────

    def aliquots_per_freezer(self) -> List[Dict]:
        """
        Total aliquots stored per freezer.
        Useful for a bar chart showing storage utilisation.
        """
        from app.core.models.models import BoxPosition, AliquotLocation
        rows = (
            self.session.query(
                Freezer.name,
                func.count(AliquotLocation.id).label("count"),
            )
            .join(Compartment,   Compartment.freezer_id    == Freezer.id)
            .join(StorageRack,   StorageRack.compartment_id == Compartment.id)
            .join(StorageDrawer, StorageDrawer.rack_id      == StorageRack.id)
            .join(StorageBox,    StorageBox.drawer_id        == StorageDrawer.id)
            .join(BoxPosition,   BoxPosition.box_id          == StorageBox.id)
            .join(AliquotLocation, AliquotLocation.position_id == BoxPosition.id)
            .group_by(Freezer.id)
            .order_by(Freezer.name)
            .all()
        )
        return [{"freezer": r.name, "count": r.count} for r in rows]

    def storage_utilisation(self) -> List[Dict]:
        """
        For each freezer: total positions vs occupied positions.
        Traverses full hierarchy: Freezer→Compartment→Rack→Drawer→Box.
        """
        from sqlalchemy.orm import joinedload
        freezers = (
            self.session.query(Freezer)
            .options(
                joinedload(Freezer.compartments)
                .joinedload(Compartment.racks)
                .joinedload(StorageRack.drawers)
                .joinedload(StorageDrawer.boxes)
            )
            .all()
        )
        result = []
        for f in freezers:
            boxes = [
                b
                for comp in f.compartments
                for rack in comp.racks
                for drawer in rack.drawers
                for b in drawer.boxes
            ]
            total    = sum(b.total_positions    for b in boxes)
            occupied = sum(b.occupied_positions for b in boxes)
            result.append({
                "freezer":  f.name,
                "total":    total,
                "occupied": occupied,
                "free":     total - occupied,
                "pct":      round(occupied / total * 100, 1) if total else 0,
            })
        return result

    # ── Demographic summary ────────────────────────────────────────────────

    def participants_by_age_group(
        self, study_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Group participants into age bands: 0-17, 18-30, 31-45, 46-60, 60+.
        """
        q = self.session.query(Participant.age)
        if study_id:
            q = q.filter(Participant.study_id == study_id)

        ages = [row.age for row in q.all() if row.age is not None]

        bands = {
            "0–17":  0,
            "18–30": 0,
            "31–45": 0,
            "46–60": 0,
            "60+":   0,
        }
        for age in ages:
            if age <= 17:
                bands["0–17"] += 1
            elif age <= 30:
                bands["18–30"] += 1
            elif age <= 45:
                bands["31–45"] += 1
            elif age <= 60:
                bands["46–60"] += 1
            else:
                bands["60+"] += 1

        return [{"band": k, "count": v} for k, v in bands.items()]

    def participants_by_sex(
        self, study_id: Optional[int] = None
    ) -> List[Dict]:
        q = (
            self.session.query(
                Participant.sex,
                func.count(Participant.id).label("count"),
            )
            .group_by(Participant.sex)
        )
        if study_id:
            q = q.filter(Participant.study_id == study_id)

        return [
            {"sex": r.sex or "Unknown", "count": r.count}
            for r in q.all()
        ]

    def participants_by_disease(
        self, study_id: Optional[int] = None
    ) -> List[Dict]:
        q = (
            self.session.query(
                Participant.disease,
                func.count(Participant.id).label("count"),
            )
            .group_by(Participant.disease)
        )
        if study_id:
            q = q.filter(Participant.study_id == study_id)

        return [
            {"disease": r.disease or "None", "count": r.count}
            for r in q.all()
        ]

    # ── Cohort flowchart data ──────────────────────────────────────────────

    def get_flowchart_data(self, study_id: Optional[int] = None) -> dict:
        """
        Returns nested dict for the dashboard flowchart:
          data[cohort_name][pop_key][visit_name][sample_type] = (n_participants, n_vials)

        For non-UNINFECTED cohorts pop_key is always "_all".
        For HIV UNINFECTED, pop_key is the population sub-group (FSW/PWID/MSM).
        """
        from collections import defaultdict

        UNINFECTED = "HIV UNINFECTED"
        POP_GROUPS = {"FSW", "PWID", "MSM"}

        q = (
            self.session.query(
                Participant.cohort_name,
                Participant.population,
                Sample.visit_name,
                Sample.sample_type,
                func.count(func.distinct(Participant.id)).label("n_part"),
                func.count(SampleAliquot.id).label("n_vials"),
            )
            .join(Sample,        Sample.participant_id == Participant.id)
            .join(SampleAliquot, SampleAliquot.sample_id == Sample.id)
            .group_by(
                Participant.cohort_name,
                Participant.population,
                Sample.visit_name,
                Sample.sample_type,
            )
        )
        if study_id:
            q = q.filter(Participant.study_id == study_id)

        data: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

        for cohort, population, visit_name, sample_type, n_part, n_vials in q.all():
            if not cohort or not visit_name or not sample_type:
                continue
            if cohort == UNINFECTED:
                pop_key = population if population in POP_GROUPS else "Other"
            else:
                pop_key = "_all"
            data[cohort][pop_key][visit_name][sample_type] = (n_part, n_vials)

        return data

    # ── Quick totals (for summary cards) ──────────────────────────────────

    def summary_totals(self) -> Dict:
        return {
            "studies":      self.session.query(Study).filter(Study.is_active).count(),
            "participants": self.session.query(Participant).count(),
            "samples":      self.session.query(Sample).count(),
            "aliquots":     self.session.query(SampleAliquot).count(),
            "available":    self.session.query(SampleAliquot)
                                .filter(SampleAliquot.is_available == True).count(),
            "blocked":      self.session.query(SampleAliquot)
                                .filter(SampleAliquot.is_blocked == True).count(),
            "shipped":      self.session.query(SampleAliquot)
                                .filter(SampleAliquot.is_shipped == True).count(),
        }

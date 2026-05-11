"""
Dashboard Tab — KPI strip + cohort flowchart.

The flowchart mirrors the reference biorepository catalogue layout:
  Four cohort blocks side by side (Adult PLHIV / CLHIV / Early HIV / HIV-ve At Risk).
  Each block is a QTableWidget with columns = visit (S/E/F) and
  rows = participant count + one row per sample type.
  HIV UNINFECTED is further split into FSW / PWID / MSM population sub-groups.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core.models.database import get_session


# ── Flowchart constants ────────────────────────────────────────────────────

COHORT_ORDER = [
    ("HIV INFECTED-ADULT",     "Cohort of Adult PLHIV",       ["Screening", "Enrollment", "Follow-up"]),
    ("HIV INFECTED-PEDIATRIC", "Cohort of CLHIV",             ["Enrollment", "Follow-up"]),
    ("EARLY HIV INFECTED",     "Cohort of Early HIV (F<1yr)", ["Enrollment", "Follow-up"]),
    ("HIV UNINFECTED",         "HIV Negative At Risk Persons", ["Screening", "Enrollment", "Follow-up"]),
]
POP_ORDER   = ["FSW", "PWID", "MSM"]
VISIT_SHORT = {"Screening": "S", "Enrollment": "E", "Follow-up": "F"}
SAMPLE_ROWS = [
    ("Serum",      "Serum"),
    ("ED Plasma",  "ED Plasma"),
    ("HEP Plasma", "HEP Plasma"),
    ("EDTA PBMC",  "EDTA PBMC"),
]

COLOR_N_BG      = QColor("#D9E1F2")   # blue-tint for participant count row
COLOR_VIAL_BG   = QColor("#E2EFDA")   # green-tint for non-zero vial cells
COLOR_HDR_BG    = QColor("#2E75B6")   # cohort group box title bar colour


class DashboardTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Controls ───────────────────────────────────────────────────────
        ctrl = QHBoxLayout()
        self._study_filter = QComboBox()
        self._study_filter.addItem("All studies", None)
        self._load_studies()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)

        ctrl.addWidget(QLabel("Study:"))
        ctrl.addWidget(self._study_filter)
        ctrl.addStretch()
        ctrl.addWidget(btn_refresh)
        layout.addLayout(ctrl)

        # ── KPI strip ──────────────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        self._kpi_participants = self._kpi_card("Participants", "0")
        self._kpi_samples      = self._kpi_card("Samples",      "0")
        self._kpi_aliquots     = self._kpi_card("Aliquots",     "0")
        self._kpi_available    = self._kpi_card("Available",    "0")
        self._kpi_blocked      = self._kpi_card("Blocked",      "0")
        self._kpi_shipped      = self._kpi_card("Shipped",      "0")

        for card in [self._kpi_participants, self._kpi_samples,
                     self._kpi_aliquots, self._kpi_available,
                     self._kpi_blocked, self._kpi_shipped]:
            kpi_row.addWidget(card)
        layout.addLayout(kpi_row)

        # ── Flowchart scroll area ──────────────────────────────────────────
        self._flow_scroll = QScrollArea()
        self._flow_scroll.setWidgetResizable(True)
        self._flow_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._flow_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self._flow_container = QWidget()
        self._flow_layout = QHBoxLayout(self._flow_container)
        self._flow_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._flow_layout.setSpacing(12)
        self._flow_layout.setContentsMargins(4, 4, 4, 4)
        self._flow_scroll.setWidget(self._flow_container)
        layout.addWidget(self._flow_scroll)

    # ── KPI helpers ────────────────────────────────────────────────────────

    def _kpi_card(self, label: str, value: str) -> QGroupBox:
        box = QGroupBox()
        vl  = QVBoxLayout(box)
        vl.setContentsMargins(12, 8, 12, 8)
        lbl_title = QLabel(label)
        lbl_title.setStyleSheet("color: grey; font-size: 11px;")
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet("font-size: 22px; font-weight: 500;")
        vl.addWidget(lbl_title)
        vl.addWidget(lbl_val)
        box.setProperty("value_label", lbl_val)
        return box

    def _set_kpi(self, card: QGroupBox, value) -> None:
        lbl = card.property("value_label")
        if lbl:
            lbl.setText(str(value))

    def _load_studies(self):
        with get_session() as session:
            from app.core.services.study_service import StudyService
            for s in StudyService(session).get_all_active():
                self._study_filter.addItem(s.project_id_short, s.id)

    # ── Refresh ────────────────────────────────────────────────────────────

    def refresh(self):
        study_id = self._study_filter.currentData()
        self._load_kpis(study_id)
        self._draw_flowchart(study_id)

    # ── KPI data load ──────────────────────────────────────────────────────

    def _load_kpis(self, study_id):
        with get_session() as session:
            from app.core.models.models import Participant, Sample, SampleAliquot

            q_base = session.query(Participant)
            if study_id:
                q_base = q_base.filter(Participant.study_id == study_id)
            n_participants = q_base.count()

            q_samples = session.query(Sample)
            if study_id:
                q_samples = q_samples.filter(Sample.study_id == study_id)
            n_samples = q_samples.count()

            q_aliquots = session.query(SampleAliquot).join(Sample)
            if study_id:
                q_aliquots = q_aliquots.filter(Sample.study_id == study_id)

            n_aliquots  = q_aliquots.count()
            n_available = q_aliquots.filter(
                SampleAliquot.is_available == True,
                SampleAliquot.is_shipped   == False,
            ).count()
            n_blocked = q_aliquots.filter(SampleAliquot.is_blocked == True).count()
            n_shipped = q_aliquots.filter(SampleAliquot.is_shipped  == True).count()

        self._set_kpi(self._kpi_participants, n_participants)
        self._set_kpi(self._kpi_samples,      n_samples)
        self._set_kpi(self._kpi_aliquots,     n_aliquots)
        self._set_kpi(self._kpi_available,    n_available)
        self._set_kpi(self._kpi_blocked,      n_blocked)
        self._set_kpi(self._kpi_shipped,      n_shipped)

    # ── Flowchart ──────────────────────────────────────────────────────────

    def _draw_flowchart(self, study_id):
        # Clear previous cohort blocks
        while self._flow_layout.count():
            item = self._flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        with get_session() as session:
            from app.core.services.dashboard_service import DashboardService
            data = DashboardService(session).get_flowchart_data(study_id)

        for cohort_key, cohort_label, visits in COHORT_ORDER:
            cohort_data = data.get(cohort_key, {})

            outer = QGroupBox(cohort_label)
            outer.setStyleSheet(
                "QGroupBox {"
                "  font-weight: bold; font-size: 12px;"
                "  border: 2px solid #2E75B6; border-radius: 6px;"
                "  margin-top: 14px; padding: 6px;"
                "}"
                "QGroupBox::title {"
                "  color: white; background: #2E75B6;"
                "  subcontrol-origin: margin; left: 8px; padding: 2px 6px;"
                "}"
            )
            outer_layout = QHBoxLayout(outer)
            outer_layout.setSpacing(8)
            outer_layout.setContentsMargins(6, 16, 6, 6)

            if cohort_key == "HIV UNINFECTED":
                for pop in POP_ORDER:
                    pop_data = cohort_data.get(pop, {})
                    pop_box = self._make_cohort_table(pop, pop_data, visits)
                    outer_layout.addWidget(pop_box)
            else:
                pop_data = cohort_data.get("_all", {})
                table = self._make_cohort_table(None, pop_data, visits)
                outer_layout.addWidget(table)

            outer.setSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
            )
            self._flow_layout.addWidget(outer)

    def _make_cohort_table(
        self,
        title: Optional[str],
        pop_data: dict,
        visits: list,
    ) -> QGroupBox:
        """One QGroupBox + QTableWidget for a cohort or population sub-group."""
        box = QGroupBox(title or "")
        box.setStyleSheet(
            "QGroupBox {"
            "  font-size: 11px; font-weight: 600;"
            "  border: 1px solid #AAAAAA; border-radius: 4px;"
            "  margin-top: 10px;"
            "}"
            "QGroupBox::title {"
            "  color: #2E75B6; subcontrol-origin: margin; left: 6px; padding: 1px 4px;"
            "}"
        )
        vl = QVBoxLayout(box)
        vl.setContentsMargins(4, 14, 4, 4)
        vl.setSpacing(2)

        n_cols = len(visits)
        n_rows = 1 + len(SAMPLE_ROWS)   # n= row + 4 sample type rows

        tbl = QTableWidget(n_rows, n_cols)
        tbl.setHorizontalHeaderLabels([VISIT_SHORT.get(v, v) for v in visits])

        v_labels = ["n ="] + [sr[1] for sr in SAMPLE_ROWS]
        tbl.setVerticalHeaderLabels(v_labels)

        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tbl.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(False)
        tbl.setShowGrid(True)
        tbl.verticalHeader().setDefaultSectionSize(22)
        tbl.horizontalHeader().setDefaultSectionSize(52)
        tbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        bold_font = QFont()
        bold_font.setBold(True)

        for col_idx, visit in enumerate(visits):
            visit_data = pop_data.get(visit, {})

            # n= row: max participant count across sample types for this visit
            n_total = max((v[0] for v in visit_data.values()), default=0)
            n_item = QTableWidgetItem(str(n_total) if n_total else "")
            n_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            n_item.setFont(bold_font)
            n_item.setBackground(COLOR_N_BG)
            tbl.setItem(0, col_idx, n_item)

            # Sample type rows
            for row_idx, (stype_key, _) in enumerate(SAMPLE_ROWS, start=1):
                _, n_vials = visit_data.get(stype_key, (0, 0))
                cell = QTableWidgetItem(str(n_vials) if n_vials else "")
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if n_vials:
                    cell.setBackground(COLOR_VIAL_BG)
                tbl.setItem(row_idx, col_idx, cell)

        tbl.resizeColumnsToContents()
        tbl.resizeRowsToContents()

        # Fix widget size to content so scroll area tiles them correctly
        tbl.setFixedHeight(
            tbl.horizontalHeader().height()
            + sum(tbl.rowHeight(r) for r in range(n_rows))
            + 4
        )

        vl.addWidget(tbl)
        return box

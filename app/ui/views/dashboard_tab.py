"""
Dashboard Tab — KPI strip + cohort flowchart (v2).

A custom QPainter-rendered CohortFlowchartWidget shows one cohort at a time.
A dropdown below the KPI strip selects which cohort to display.
Styled to match the reference biorepository catalogue layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from app.core.models.database import get_session


# ── Flowchart constants ────────────────────────────────────────────────────

COHORT_ORDER = [
    ("HIV INFECTED-ADULT",     "Cohort of Adult PLHIV",        ["Screening", "Enrollment", "Follow-up"]),
    ("HIV INFECTED-PEDIATRIC", "Cohort of CLHIV",              ["Enrollment", "Follow-up"]),
    ("EARLY HIV INFECTED",     "Cohort of Early HIV (F<1yr)",  ["Enrollment", "Follow-up"]),
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


# ── Data classes ───────────────────────────────────────────────────────────

@dataclass
class ColumnSpec:
    visit_label: str
    group_label: Optional[str]   # FSW / PWID / MSM, or None
    n_participants: int
    sample_counts: dict = field(default_factory=dict)


@dataclass
class FlowchartSpec:
    cohort_label: str
    columns: list
    has_group_headers: bool = False


# ── Custom painted widget ──────────────────────────────────────────────────

class CohortFlowchartWidget(QWidget):
    """Renders the cohort flowchart using QPainter — no QTableWidget."""

    LABEL_W     = 110
    COL_W       = 80
    HEADER_H    = 48
    GROUP_HDR_H = 30
    VISIT_HDR_H = 52   # split evenly: visit letter top, n= bottom
    ROW_H       = 30
    MARGIN      = 16

    # Colours
    C_COHORT_BG = QColor("#1F4E79")
    C_COHORT_FG = QColor("#FFFFFF")
    C_GROUP_BG  = QColor("#2E75B6")
    C_GROUP_FG  = QColor("#FFFFFF")
    C_VISIT_BG  = QColor("#BDD7EE")
    C_VISIT_FG  = QColor("#1F4E79")
    C_N_BG      = QColor("#D9E1F2")
    C_N_FG      = QColor("#1F4E79")
    C_LABEL_BG  = QColor("#F2F2F2")
    C_VIAL_BG   = QColor("#E2EFDA")
    C_EMPTY_BG  = QColor("#FFFFFF")
    C_GRID      = QColor("#AAAAAA")
    C_TEXT      = QColor("#333333")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._spec: Optional[FlowchartSpec] = None
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

    def load(self, spec: FlowchartSpec) -> None:
        self._spec = spec
        self._recalculate_size()
        self.update()

    def _recalculate_size(self) -> None:
        if not self._spec:
            return
        n_cols  = len(self._spec.columns)
        total_w = self.MARGIN * 2 + self.LABEL_W + n_cols * self.COL_W
        total_h = (
            self.MARGIN
            + self.HEADER_H
            + (self.GROUP_HDR_H if self._spec.has_group_headers else 0)
            + self.VISIT_HDR_H
            + len(SAMPLE_ROWS) * self.ROW_H
            + self.MARGIN
        )
        self.setMinimumSize(total_w, total_h)
        self.resize(total_w, total_h)

    # ── Paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if not self._spec:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self._paint(painter)
        painter.end()

    def _paint(self, painter: QPainter) -> None:
        spec   = self._spec
        m      = self.MARGIN
        n_cols = len(spec.columns)
        total_w = self.LABEL_W + n_cols * self.COL_W

        y = m

        # ── 1. Cohort header banner ────────────────────────────────────────
        self._fill(painter, m, y, total_w, self.HEADER_H, self.C_COHORT_BG)
        self._text(painter, m, y, total_w, self.HEADER_H,
                   spec.cohort_label, self.C_COHORT_FG, bold=True, size=14)
        y += self.HEADER_H

        # ── 2. Population group headers (HIV UNINFECTED only) ──────────────
        if spec.has_group_headers:
            x = m
            self._fill(painter, x, y, self.LABEL_W, self.GROUP_HDR_H, self.C_LABEL_BG)
            self._border(painter, x, y, self.LABEL_W, self.GROUP_HDR_H)
            x += self.LABEL_W

            # Merge consecutive columns with the same group_label
            i = 0
            while i < n_cols:
                grp = spec.columns[i].group_label or ""
                span = 0
                while i + span < n_cols and (spec.columns[i + span].group_label or "") == grp:
                    span += 1
                w = span * self.COL_W
                self._fill(painter, x, y, w, self.GROUP_HDR_H, self.C_GROUP_BG)
                self._text(painter, x, y, w, self.GROUP_HDR_H,
                           grp, self.C_GROUP_FG, bold=True, size=11)
                self._border(painter, x, y, w, self.GROUP_HDR_H)
                x   += w
                i   += span

            y += self.GROUP_HDR_H

        # ── 3. Visit header + n= row ───────────────────────────────────────
        half = self.VISIT_HDR_H // 2
        x = m
        # Label column
        self._fill(painter, x, y,        self.LABEL_W, half, self.C_LABEL_BG)
        self._text(painter, x, y,        self.LABEL_W, half,
                   "Visit", self.C_VISIT_FG, bold=False, size=9)
        self._fill(painter, x, y + half, self.LABEL_W, half, self.C_LABEL_BG)
        self._text(painter, x, y + half, self.LABEL_W, half,
                   "n =", self.C_N_FG, bold=True, size=9)
        self._border(painter, x, y, self.LABEL_W, self.VISIT_HDR_H)
        x += self.LABEL_W

        for col in spec.columns:
            # Visit letter
            self._fill(painter, x, y,        self.COL_W, half, self.C_VISIT_BG)
            self._text(painter, x, y,        self.COL_W, half,
                       col.visit_label, self.C_VISIT_FG, bold=True, size=13)
            self._border(painter, x, y, self.COL_W, half)
            # n= number
            self._fill(painter, x, y + half, self.COL_W, half, self.C_N_BG)
            n_txt = str(col.n_participants) if col.n_participants else "—"
            self._text(painter, x, y + half, self.COL_W, half,
                       n_txt, self.C_N_FG, bold=True, size=11)
            self._border(painter, x, y + half, self.COL_W, half)
            x += self.COL_W

        y += self.VISIT_HDR_H

        # ── 4. Sample type rows ────────────────────────────────────────────
        for stype_key, stype_label in SAMPLE_ROWS:
            x = m
            self._fill(painter, x, y, self.LABEL_W, self.ROW_H, self.C_LABEL_BG)
            self._text(painter, x, y, self.LABEL_W, self.ROW_H,
                       stype_label, self.C_TEXT, bold=False, size=10,
                       align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       padding=8)
            self._border(painter, x, y, self.LABEL_W, self.ROW_H)
            x += self.LABEL_W

            for col in spec.columns:
                count = col.sample_counts.get(stype_key, 0)
                bg = self.C_VIAL_BG if count else self.C_EMPTY_BG
                self._fill(painter, x, y, self.COL_W, self.ROW_H, bg)
                if count:
                    self._text(painter, x, y, self.COL_W, self.ROW_H,
                               str(count), self.C_TEXT, bold=False, size=11)
                self._border(painter, x, y, self.COL_W, self.ROW_H)
                x += self.COL_W

            y += self.ROW_H

    # ── Paint helpers ──────────────────────────────────────────────────────

    def _fill(self, p: QPainter, x, y, w, h, color: QColor) -> None:
        p.fillRect(x, y, w, h, QBrush(color))

    def _border(self, p: QPainter, x, y, w, h) -> None:
        p.setPen(QPen(self.C_GRID, 1))
        p.drawRect(x, y, w - 1, h - 1)

    def _text(self, p: QPainter, x, y, w, h, text: str, color: QColor,
              bold: bool = False, size: int = 10,
              align=Qt.AlignmentFlag.AlignCenter,
              padding: int = 0) -> None:
        font = QFont()
        font.setBold(bold)
        font.setPointSize(size)
        p.setFont(font)
        p.setPen(QPen(color))
        p.drawText(QRect(x + padding, y, w - padding * 2, h), int(align), text)


# ── Dashboard tab ──────────────────────────────────────────────────────────

class DashboardTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Study filter + Refresh ─────────────────────────────────────────
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

        # ── Cohort selector ────────────────────────────────────────────────
        cohort_row = QHBoxLayout()
        cohort_row.addStretch()
        cohort_row.addWidget(QLabel("Cohort:"))
        self._cohort_combo = QComboBox()
        self._cohort_combo.setMinimumWidth(260)
        for cohort_key, cohort_label, _ in COHORT_ORDER:
            self._cohort_combo.addItem(cohort_label, cohort_key)
        self._cohort_combo.currentIndexChanged.connect(self._on_cohort_changed)
        cohort_row.addWidget(self._cohort_combo)
        layout.addLayout(cohort_row)

        # ── Flowchart canvas ───────────────────────────────────────────────
        self._flowchart = CohortFlowchartWidget()
        flow_scroll = QScrollArea()
        flow_scroll.setWidget(self._flowchart)
        flow_scroll.setWidgetResizable(False)
        flow_scroll.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(flow_scroll)

    # ── KPI helpers ────────────────────────────────────────────────────────

    def _kpi_card(self, label: str, value: str) -> QGroupBox:
        box = QGroupBox()
        from PyQt6.QtWidgets import QVBoxLayout as VL
        vl = VL(box)
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
        self._redraw_flowchart(study_id)

    def _on_cohort_changed(self):
        self._redraw_flowchart(self._study_filter.currentData())

    def _redraw_flowchart(self, study_id):
        with get_session() as session:
            from app.core.services.dashboard_service import DashboardService
            data = DashboardService(session).get_flowchart_data(study_id)
        cohort_key = self._cohort_combo.currentData()
        spec = self._build_flowchart_spec(cohort_key, data)
        self._flowchart.load(spec)

    # ── KPI data ───────────────────────────────────────────────────────────

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

    # ── Spec builder ───────────────────────────────────────────────────────

    def _build_flowchart_spec(self, cohort_key: str, data: dict) -> FlowchartSpec:
        cohort_map = {c[0]: (c[1], c[2]) for c in COHORT_ORDER}
        label, visits = cohort_map.get(
            cohort_key,
            (cohort_key, ["Screening", "Enrollment", "Follow-up"])
        )
        cohort_data   = data.get(cohort_key, {})
        is_uninfected = cohort_key == "HIV UNINFECTED"

        columns = []
        if is_uninfected:
            for pop in POP_ORDER:
                pop_data = cohort_data.get(pop, {})
                for visit in visits:
                    visit_data = pop_data.get(visit, {})
                    n = max((v[0] for v in visit_data.values()), default=0)
                    counts = {k: v[1] for k, v in visit_data.items()}
                    columns.append(ColumnSpec(
                        visit_label=VISIT_SHORT.get(visit, visit),
                        group_label=pop,
                        n_participants=n,
                        sample_counts=counts,
                    ))
        else:
            pop_data = cohort_data.get("_all", {})
            for visit in visits:
                visit_data = pop_data.get(visit, {})
                n = max((v[0] for v in visit_data.values()), default=0)
                counts = {k: v[1] for k, v in visit_data.items()}
                columns.append(ColumnSpec(
                    visit_label=VISIT_SHORT.get(visit, visit),
                    group_label=None,
                    n_participants=n,
                    sample_counts=counts,
                ))

        return FlowchartSpec(
            cohort_label=label,
            columns=columns,
            has_group_headers=is_uninfected,
        )

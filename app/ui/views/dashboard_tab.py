"""
Dashboard Tab — summary graphs using matplotlib embedded in PyQt6.

Key concept — FigureCanvasQTAgg:
  matplotlib's Qt backend provides FigureCanvasQTAgg.
  This is a QWidget subclass that renders a matplotlib Figure.
  We add it to our layout like any other widget.
  When data updates, we clear the axes and redraw — canvas.draw() refreshes.

  NavigationToolbar2QT adds the standard matplotlib toolbar
  (zoom, pan, save image) automatically.

Four chart panels:
  1. Samples by study       — horizontal bar chart
  2. Aliquot status         — pie chart (available / blocked / shipped)
  3. Sample types breakdown  — horizontal bar
  4. Participants by age group — histogram
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)

from app.core.models.database import get_session


class DashboardTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Controls
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

        # Summary KPI strip
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

        # Matplotlib canvas
        try:
            import matplotlib
            matplotlib.use("QtAgg")
            from matplotlib.backends.backend_qtagg import (
                FigureCanvasQTAgg as FigureCanvas,
                NavigationToolbar2QT as NavToolbar,
            )
            from matplotlib.figure import Figure

            self._fig = Figure(figsize=(12, 6), tight_layout=True)
            self._canvas = FigureCanvas(self._fig)
            toolbar = NavToolbar(self._canvas, self)
            layout.addWidget(toolbar)
            layout.addWidget(self._canvas)
            self._has_matplotlib = True
        except Exception as e:
            import traceback
            self._has_matplotlib = False
            error_details = traceback.format_exc()
            lbl = QLabel(
                f"Charts unavailable.\n\n{type(e).__name__}: {e}\n\n{error_details}"
            )
            lbl.setAlignment(__import__('PyQt6.QtCore', fromlist=['Qt']).Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: grey; font-size: 11px;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

    def _kpi_card(self, label: str, value: str) -> QGroupBox:
        """A small KPI card — label on top, big number below."""
        box = QGroupBox()
        vl  = QVBoxLayout(box)
        vl.setContentsMargins(12, 8, 12, 8)
        lbl_title = QLabel(label)
        lbl_title.setStyleSheet("color: grey; font-size: 11px;")
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet("font-size: 22px; font-weight: 500;")
        vl.addWidget(lbl_title)
        vl.addWidget(lbl_val)
        # Store reference to value label for updates
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

    def refresh(self):
        study_id = self._study_filter.currentData()
        self._load_kpis(study_id)
        if self._has_matplotlib:
            self._draw_charts(study_id)

    def _load_kpis(self, study_id):
        with get_session() as session:
            from app.core.models.models import (
                Participant, Sample, SampleAliquot
            )
            from sqlalchemy import func

            q_base = session.query(Participant)
            if study_id:
                q_base = q_base.filter(Participant.study_id == study_id)

            n_participants = q_base.count()

            q_samples = session.query(Sample)
            if study_id:
                q_samples = q_samples.filter(Sample.study_id == study_id)
            n_samples = q_samples.count()

            # Aliquot counts
            q_aliquots = (
                session.query(SampleAliquot)
                .join(Sample)
            )
            if study_id:
                q_aliquots = q_aliquots.filter(Sample.study_id == study_id)

            n_aliquots  = q_aliquots.count()
            n_available = q_aliquots.filter(
                SampleAliquot.is_available == True,
                SampleAliquot.is_shipped   == False,
            ).count()
            n_blocked   = q_aliquots.filter(SampleAliquot.is_blocked == True).count()
            n_shipped   = q_aliquots.filter(SampleAliquot.is_shipped  == True).count()

        self._set_kpi(self._kpi_participants, n_participants)
        self._set_kpi(self._kpi_samples,      n_samples)
        self._set_kpi(self._kpi_aliquots,     n_aliquots)
        self._set_kpi(self._kpi_available,    n_available)
        self._set_kpi(self._kpi_blocked,      n_blocked)
        self._set_kpi(self._kpi_shipped,      n_shipped)

    def _draw_charts(self, study_id):
        """Draw 4 subplots: sample types, age groups, status pie, study bar."""
        with get_session() as session:
            from app.core.models.models import Participant, Sample, SampleAliquot
            from sqlalchemy import func

            # Sample type counts
            q_types = (
                session.query(Sample.sample_type, func.count(SampleAliquot.id))
                .join(SampleAliquot)
            )
            if study_id:
                q_types = q_types.filter(Sample.study_id == study_id)
            type_data = q_types.group_by(Sample.sample_type).all()

            # Age distribution
            q_ages = session.query(Participant.age).filter(
                Participant.age != None
            )
            if study_id:
                q_ages = q_ages.filter(Participant.study_id == study_id)
            ages = [row[0] for row in q_ages.all()]

            # Aliquot status
            q_al = session.query(SampleAliquot).join(Sample)
            if study_id:
                q_al = q_al.filter(Sample.study_id == study_id)
            all_aliquots = q_al.all()
            n_avail   = sum(1 for a in all_aliquots if a.is_available and not a.is_shipped)
            n_blocked  = sum(1 for a in all_aliquots if a.is_blocked)
            n_shipped  = sum(1 for a in all_aliquots if a.is_shipped)
            n_other    = len(all_aliquots) - n_avail - n_blocked - n_shipped

            # Study breakdown
            if not study_id:
                from app.core.models.models import Study
                study_data = (
                    session.query(Study.project_id_short, func.count(Participant.id))
                    .outerjoin(Participant)
                    .group_by(Study.id)
                    .all()
                )
            else:
                study_data = []

        self._fig.clear()
        axes = self._fig.subplots(2, 2)
        colors = ["#4A90D9", "#2ECC71", "#E8A838", "#E74C3C", "#9B59B6"]

        # Chart 1 — Sample types
        ax1 = axes[0][0]
        if type_data:
            labels1 = [r[0] for r in type_data]
            values1 = [r[1] for r in type_data]
            bars = ax1.barh(labels1, values1,
                            color=colors[:len(labels1)])
            ax1.bar_label(bars, padding=3, fontsize=8)
        ax1.set_title("Aliquots by sample type", fontsize=10)
        ax1.tick_params(labelsize=8)

        # Chart 2 — Age histogram
        ax2 = axes[0][1]
        if ages:
            ax2.hist(ages, bins=10, color="#4A90D9", edgecolor="white")
            ax2.set_xlabel("Age", fontsize=8)
            ax2.set_ylabel("Participants", fontsize=8)
        ax2.set_title("Age distribution", fontsize=10)
        ax2.tick_params(labelsize=8)

        # Chart 3 — Aliquot status pie
        ax3 = axes[1][0]
        pie_vals   = [n_avail, n_blocked, n_shipped, n_other]
        pie_labels = ["Available", "Blocked", "Shipped", "Other"]
        pie_colors = ["#2ECC71", "#E8A838", "#4A90D9", "#CCCCCC"]
        non_zero = [(v, l, c) for v, l, c in
                    zip(pie_vals, pie_labels, pie_colors) if v > 0]
        if non_zero:
            vals, lbls, cols = zip(*non_zero)
            ax3.pie(vals, labels=lbls, colors=cols,
                    autopct="%1.0f%%", textprops={"fontsize": 8})
        ax3.set_title("Aliquot status", fontsize=10)

        # Chart 4 — Participants per study (or placeholder)
        ax4 = axes[1][1]
        if study_data:
            s_labels = [r[0] for r in study_data]
            s_values = [r[1] for r in study_data]
            bars4 = ax4.bar(s_labels, s_values,
                            color=colors[:len(s_labels)])
            ax4.bar_label(bars4, padding=3, fontsize=8)
            ax4.set_ylabel("Participants", fontsize=8)
        else:
            ax4.text(0.5, 0.5, "Select 'All studies'\nto see study breakdown",
                     ha="center", va="center", transform=ax4.transAxes,
                     fontsize=9, color="grey")
        ax4.set_title("Participants by study", fontsize=10)
        ax4.tick_params(labelsize=8)

        self._canvas.draw()

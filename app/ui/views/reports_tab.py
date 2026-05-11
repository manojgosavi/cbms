"""
Reports Tab — catalogue generation and Excel export.

Key concept — embedding matplotlib in PyQt6:
  matplotlib has a Qt backend: FigureCanvasQTAgg.
  We embed it as a normal QWidget inside our layout.
  When data changes, we call canvas.draw() to refresh it.
  NavigationToolbar2QT adds zoom/pan/save controls automatically.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.services.catalogue_service import CatalogueRow, CatalogueService
from app.core.services.study_service import StudyService


class ReportsTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[CatalogueRow] = []
        self._col_headers: List[str]   = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Filter bar ─────────────────────────────────────────────────────
        filter_box = QGroupBox("Catalogue filters")
        fl = QHBoxLayout(filter_box)

        self._study_combo = QComboBox()
        self._study_combo.addItem("All studies", None)
        self._load_studies()

        self._available_only = QCheckBox("Available aliquots only")
        self._available_only.setChecked(False)  # Default: show ALL aliquots (including shipped/blocked)

        btn_generate = QPushButton("Generate Catalogue")
        btn_generate.clicked.connect(self._on_generate)
        
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._on_generate)  # Refresh = regenerate with same filters

        self._btn_export = QPushButton("Export to Excel…")
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._on_export)

        fl.addWidget(QLabel("Study:"))
        fl.addWidget(self._study_combo)
        fl.addWidget(self._available_only)
        fl.addStretch()
        fl.addWidget(btn_generate)
        fl.addWidget(btn_refresh)
        fl.addWidget(self._btn_export)
        layout.addWidget(filter_box)

        # ── Summary label ──────────────────────────────────────────────────
        self._summary_lbl = QLabel("Click 'Generate Catalogue' to build the pivot table.")
        self._summary_lbl.setStyleSheet("color: grey; padding: 4px;")
        layout.addWidget(self._summary_lbl)

        # ── Pivot table ────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self._table)

    def _load_studies(self):
        with get_session() as session:
            svc = StudyService(session)
            for s in svc.get_all_active():
                self._study_combo.addItem(s.project_id_short, s.id)

    def _on_generate(self):
        study_id = self._study_combo.currentData()
        avail    = self._available_only.isChecked()

        with get_session() as session:
            svc = CatalogueService(session)
            self._rows, self._col_headers = svc.generate(
                study_id=study_id, available_only=avail
            )

        if not self._rows:
            self._summary_lbl.setText("No data found for selected filters.")
            self._table.setRowCount(0)
            self._btn_export.setEnabled(False)
            return

        # ── Populate pivot table ───────────────────────────────────────────
        demo_cols    = ["PID", "Study", "Age", "Gender", "Disease", "Cohort", "Site", "Total"]
        all_cols     = demo_cols + self._col_headers

        self._table.setColumnCount(len(all_cols))
        self._table.setHorizontalHeaderLabels(all_cols)
        self._table.setRowCount(len(self._rows))

        for row_idx, row in enumerate(self._rows):
            demo_vals = [
                row.pid, row.study_code, row.age, row.gender,
                row.disease, row.cohort_name, row.site_name, row.total_aliquots,
            ]
            for col_idx, val in enumerate(demo_vals):
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row_idx, col_idx, item)

            for col_idx, stype in enumerate(self._col_headers,
                                             start=len(demo_cols)):
                count = row.sample_counts.get(stype, 0)
                item  = QTableWidgetItem(str(count) if count else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if count > 0:
                    from PyQt6.QtGui import QColor
                    item.setBackground(QColor("#E2EFDA"))
                self._table.setItem(row_idx, col_idx, item)

        total_aliquots = sum(r.total_aliquots for r in self._rows)
        self._summary_lbl.setText(
            f"{len(self._rows)} participant(s)  |  "
            f"{len(self._col_headers)} sample type(s)  |  "
            f"{total_aliquots} total aliquots"
        )
        self._btn_export.setEnabled(True)

    def _on_export(self):
        if not self._rows:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Catalogue", "sample_catalogue.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not path:
            return
        try:
            with get_session() as session:
                svc = CatalogueService(session)
                svc.export_to_excel(self._rows, self._col_headers, path)
            QMessageBox.information(
                self, "Export complete",
                f"Catalogue saved to:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))
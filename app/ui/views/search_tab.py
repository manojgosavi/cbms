"""
Search Tab — multi-criteria AND/OR search with results table.

Layout:
  ┌─ Filter panel (left, collapsible) ─┬─ Results table (right) ─┐
  │ PID, Age, Gender, Disease...          │ All matching aliquots    │
  │ Sample type, Date range...         │ with location details    │
  │ Freezer, Compartment, Rack...      │                          │
  │ [AND] [OR]  [Search] [Clear]       │                          │
  └────────────────────────────────────┴──────────────────────────┘

Location hierarchy: Freezer → Compartment → Rack → Drawer → Box → Position
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QRadioButton,
    QScrollArea, QSplitter, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.services.search_service import SearchFilters, SearchResult, SearchService
from app.utils.exception_handler import slot_safe


class SearchTab(QWidget):

    # Columns shown in results table
    COLUMNS = [
        "PID", "Age", "Gender", "Disease", "Cohort", "Site",
        "Sample ID", "Sample Type", "Collection Date",
        "Aliquot ID", "Vol (µL)", "Status",
        "Freezer", "Compartment", "Rack", "Drawer", "Box", "Position",
        "Discrepancy",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: List[SearchResult] = []
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: filter panel ─────────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(240)
        left.setMaximumWidth(320)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Participant group - ONLY PID
        form.addRow(self._section_label("Participant"))
        self._f_pid  = QLineEdit(); self._f_pid.setPlaceholderText("partial match")
        form.addRow("PID:",        self._f_pid)

        form.addRow(self._section_label("Population"))
        self._f_age = QSpinBox(); self._f_age.setRange(0, 150)
        form.addRow("Age:",        self._f_age)

        form.addRow(self._section_label("Site Name"))
        self._f_site = QLineEdit(); self._f_site.setPlaceholderText("partial match")
        form.addRow("Site:",       self._f_site)

        form.addRow(self._section_label("Visit Time"))
        self._f_visit_time = QLineEdit(); self._f_visit_time.setPlaceholderText("partial match (e.g. M0, M3, etc.)")
        form.addRow("Visit Time:", self._f_visit_time)

        form.addRow(self._section_label("Cohort"))
        self._f_cohort = QLineEdit(); self._f_cohort.setPlaceholderText("partial match")
        form.addRow("Cohort:",       self._f_cohort)

        form.addRow(self._section_label("Disease"))
        self._f_disease = QLineEdit(); self._f_disease.setPlaceholderText("partial match")
        form.addRow("Disease:",    self._f_disease)

        form.addRow(self._section_label("Sample Type"))
        self._f_sample_type = QLineEdit(); self._f_sample_type.setPlaceholderText("partial match")
        form.addRow("Sample Type:", self._f_sample_type)

        scroll.setWidget(form_widget)
        left_layout.addWidget(scroll)

        # AND / OR toggle
        mode_box = QGroupBox("Search mode")
        mode_layout = QHBoxLayout(mode_box)
        self._and_radio = QRadioButton("AND  (all conditions)")
        self._or_radio  = QRadioButton("OR  (any condition)")
        self._and_radio.setChecked(True)
        mode_layout.addWidget(self._and_radio)
        mode_layout.addWidget(self._or_radio)
        left_layout.addWidget(mode_box)

        # Action buttons
        btn_row = QHBoxLayout()
        self._btn_search = QPushButton("Search")
        self._btn_search.setDefault(True)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_clear = QPushButton("Clear")
        self._btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(self._btn_search)
        btn_row.addWidget(self._btn_clear)
        left_layout.addLayout(btn_row)

        # ── Right: results table ───────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)

        results_toolbar = QHBoxLayout()
        self._lbl_count = QLabel("Run a search to see results.")
        self._lbl_count.setStyleSheet("color: grey;")

        self._btn_block  = QPushButton("Block selected…")
        self._btn_ship   = QPushButton("Ship selected…")
        self._btn_export = QPushButton("Export to Excel")
        self._btn_locate = QPushButton("Show in box")

        self._btn_block.setEnabled(False)
        self._btn_ship.setEnabled(False)
        self._btn_locate.setEnabled(False)

        self._btn_block.clicked.connect(self._on_block)
        self._btn_ship.clicked.connect(self._on_ship)
        self._btn_export.clicked.connect(self._on_export)
        self._btn_locate.clicked.connect(self._on_locate)

        results_toolbar.addWidget(self._lbl_count)
        results_toolbar.addStretch()
        results_toolbar.addWidget(self._btn_locate)
        results_toolbar.addWidget(self._btn_block)
        results_toolbar.addWidget(self._btn_ship)
        results_toolbar.addWidget(self._btn_export)
        right_layout.addLayout(results_toolbar)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_row_double_clicked)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        right_layout.addWidget(self._table)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 900])
        layout.addWidget(splitter)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(f"── {text} ──")
        lbl.setStyleSheet(
            "color: var(--color-text-secondary, grey); "
            "font-size: 11px; font-weight: 500; margin-top: 6px;"
        )
        return lbl

    def _build_filters(self) -> SearchFilters:
        f = SearchFilters()

        f.pid        = self._f_pid.text().strip() or None
        f.age        = self._f_age.value() or None
        f.site_name  = self._f_site.text().strip() or None
        f.visit_time = self._f_visit_time.text().strip() if self._f_visit_time.text().strip() else None
        f.cohort     = self._f_cohort.text().strip() or None
        f.disease    = self._f_disease.text().strip() or None
        f.sample_type = self._f_sample_type.text().strip() or None
        return f

    def _col(self, row: int, col: int, value) -> None:
        item = QTableWidgetItem(str(value) if value is not None else "")
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._table.setItem(row, col, item)

    # ── Search ─────────────────────────────────────────────────────────────

    @slot_safe
    def _on_search(self):
        filters = self._build_filters()

        with get_session() as session:
            svc = SearchService(session)
            self._results, total = svc.search(filters)

        self._table.setRowCount(len(self._results))

        for row_idx, r in enumerate(self._results):
            if r.is_shipped:
                status = "Shipped"
            elif r.is_blocked:
                status = "Blocked"
            elif not r.is_available:
                status = "Unavailable"
            else:
                status = "Available"

            pos_label = ""
            if r.position_row is not None and r.position_col is not None:
                col_label = chr(ord('A') + r.position_col) if r.position_col < 26 else str(r.position_col)
                pos_label = f"{r.position_row + 1}{col_label}"

            values = [
                r.pid, r.age, r.gender, r.disease, r.cohort, r.site_name,
                r.sample_id, r.sample_type,
                str(r.collection_date) if r.collection_date else "",
                r.aliquot_id, r.volume_ul, status,
                r.freezer_name, r.compartment_name, r.rack_name,
                r.drawer_name, r.box_name, pos_label,
                "⚠" if r.discrepancy_remark else "",
            ]

            for col_idx, val in enumerate(values):
                self._col(row_idx, col_idx, val)

            self._table.item(row_idx, 0).setData(
                Qt.ItemDataRole.UserRole, r.aliquot_db_id
            )

        mode = "OR" if filters.use_or else "AND"
        self._lbl_count.setText(
            f"{len(self._results)} result(s) of {total} total  [{mode} mode]"
        )
        self._btn_export.setEnabled(len(self._results) > 0)

    @slot_safe
    def _on_clear(self):
        self._f_pid.clear()
        self._f_age.setValue(0)
        self._f_site.clear()
        self._f_visit_time.clear()
        self._f_cohort.clear()
        self._f_disease.clear()
        self._f_sample_type.clear()
        self._table.setRowCount(0)
        self._lbl_count.setText("Run a search to see results.")

    # ── Selection ──────────────────────────────────────────────────────────

    @slot_safe
    def _on_selection_changed(self):
        has = bool(self._table.selectedItems())
        self._btn_block.setEnabled(has)
        self._btn_ship.setEnabled(has)
        self._btn_locate.setEnabled(len(self._table.selectionModel().selectedRows()) == 1)

    def _selected_aliquot_ids(self) -> list[int]:
        rows = set(idx.row() for idx in self._table.selectionModel().selectedRows())
        ids = []
        for row in rows:
            item = self._table.item(row, 0)
            if item:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    # ── Actions ────────────────────────────────────────────────────────────

    @slot_safe
    def _on_block(self):
        aliquot_ids = self._selected_aliquot_ids()
        if not aliquot_ids:
            return
        from app.ui.dialogs.block_dialog import BlockDialog
        dlg = BlockDialog(self, aliquot_ids=aliquot_ids)
        if dlg.exec():
            self._on_search()

    @slot_safe
    def _on_ship(self):
        aliquot_ids = self._selected_aliquot_ids()
        if not aliquot_ids:
            return
        from app.ui.dialogs.shipment_dialog import ShipmentDialog
        dlg = ShipmentDialog(self, aliquot_ids=aliquot_ids)
        if dlg.exec():
            self._on_search()

    @slot_safe
    def _on_export(self):
        from app.ui.dialogs.export_dialog import ExportDialog
        dlg = ExportDialog(self, results=self._results)
        dlg.exec()

    @slot_safe
    def _on_locate(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        result = self._results[row] if row < len(self._results) else None
        if result and result.freezer_name:
            main = self.window()
            if hasattr(main, "show_aliquot_location"):
                main.show_aliquot_location(result.aliquot_db_id)

    @slot_safe
    def _on_row_double_clicked(self, index):
        self._on_locate()

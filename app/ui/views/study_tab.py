"""
Study Tab — lists all studies with toolbar actions.

PyQt6 concepts used here:
  - QTableWidget  : spreadsheet-style table with rows and columns
  - QToolBar      : button bar above the table
  - QHeaderView   : controls how column headers resize
    - Stretch      = last column fills remaining space
    - ResizeToContents = column width fits its content
  - itemSelectionChanged signal : fires when user clicks a row
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.services.study_service import StudyService
from app.utils.exception_handler import slot_safe


class StudyTab(QWidget):

    COLUMNS = ["Short ID", "Study Name", "PI", "Site", "Start Date", "Status", "Locked"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Toolbar ────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self._btn_new = QPushButton("＋  New Study")
        self._btn_new.clicked.connect(self._on_new)

        self._btn_edit = QPushButton("✎  Edit")
        self._btn_edit.setEnabled(False)
        self._btn_edit.clicked.connect(self._on_edit)

        self._btn_delete = QPushButton("🗑  Delete")
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._on_delete)

        self._lbl_count = QLabel("0 studies")
        self._lbl_count.setStyleSheet("color: grey;")

        toolbar.addWidget(self._btn_new)
        toolbar.addWidget(self._btn_edit)
        toolbar.addWidget(self._btn_delete)
        toolbar.addStretch()
        toolbar.addWidget(self._lbl_count)
        layout.addLayout(toolbar)

        # ── Table ──────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)

        # Single row selection only
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)

        # Column sizing
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # name stretches
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self._table)

    # ── Data loading ───────────────────────────────────────────────────────

    def refresh(self):
        """Reload studies from DB and repopulate the table."""
        with get_session() as session:
            service = StudyService(session)
            studies = service.get_all_active()
            # Detach data we need before session closes
            data = [
                (
                    s.project_id_short,
                    s.name,
                    s.pi_name or "",
                    s.site_name or "",
                    str(s.start_date.date()) if s.start_date else "",
                    "Active" if s.is_active else "Archived",
                    "🔒" if s.is_locked else "",
                    s.id,   # hidden — used for edit/delete
                )
                for s in studies
            ]

        self._table.setRowCount(len(data))
        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data[:-1]):  # skip hidden id
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(row_idx, col_idx, item)

            # Store the study ID in the first cell's user data
            # Qt lets you attach arbitrary Python objects to table items
            self._table.item(row_idx, 0).setData(Qt.ItemDataRole.UserRole, row_data[-1])

        self._lbl_count.setText(f"{len(data)} stud{'y' if len(data)==1 else 'ies'}")
        self._btn_edit.setEnabled(False)
        self._btn_delete.setEnabled(False)

    # ── Event handlers ─────────────────────────────────────────────────────

    @slot_safe
    def _on_selection_changed(self):
        has_selection = bool(self._table.selectedItems())
        self._btn_edit.setEnabled(has_selection)
        self._btn_delete.setEnabled(has_selection)

    def _selected_study_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    @slot_safe
    def _on_new(self):
        from app.ui.dialogs.study_dialog import StudyDialog
        dlg = StudyDialog(self)
        if dlg.exec():
            self.refresh()

    @slot_safe
    def _on_edit(self):
        study_id = self._selected_study_id()
        if study_id is None:
            return
        from app.ui.dialogs.study_dialog import StudyDialog
        dlg = StudyDialog(self, study_id=study_id)
        if dlg.exec():
            self.refresh()

    @slot_safe
    def _on_delete(self):
        study_id = self._selected_study_id()
        if study_id is None:
            return

        from app.ui.dialogs.reason_dialog import ReasonDialog
        reason_dlg = ReasonDialog(self, prompt="Reason for deleting this study:")
        if not reason_dlg.exec():
            return

        with get_session() as session:
            service = StudyService(session)
            ok, msg = service.delete_study(study_id, reason_dlg.reason)

        if ok:
            self.refresh()
        else:
            QMessageBox.warning(self, "Cannot Delete", msg)

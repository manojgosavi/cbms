"""
Place Aliquot Dialog — pick an unplaced aliquot to assign to a box cell.

Shows a searchable table of aliquots that are:
  - available (is_available = True)
  - not shipped (is_shipped = False)
  - not already located anywhere

The user selects one row and clicks OK.
The caller receives the chosen SampleAliquot.id via .selected_aliquot_id.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from app.core.models.database import get_session
from app.core.models.models import SampleAliquot
from app.core.repositories.storage_repository import AliquotLocationRepository
from app.utils.exception_handler import slot_safe


class PlaceAliquotDialog(QDialog):
    """
    Searchable picker for unplaced aliquots.

    Usage:
        dlg = PlaceAliquotDialog(parent, position_label="1A")
        if dlg.exec():
            aliquot_id = dlg.selected_aliquot_id
    """

    def __init__(self, parent=None, position_label: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Place Aliquot")
        self.setMinimumWidth(560)
        self.setMinimumHeight(400)

        self.selected_aliquot_id: Optional[int] = None
        self._aliquots: List[SampleAliquot] = []

        self._build_ui(position_label)
        self._load()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self, position_label: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        label_text = f"Select an aliquot to place at position <b>{position_label}</b>:" \
                     if position_label else "Select an aliquot to place:"
        layout.addWidget(QLabel(label_text))

        # Search bar
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Aliquot ID or Participant PID…")
        self._search.textChanged.connect(self._on_search)
        search_row.addWidget(self._search)
        layout.addLayout(search_row)

        # Table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Aliquot ID", "Participant", "Sample Type", "Volume (µL)"]
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

        # Row count label
        self._count_label = QLabel("")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._count_label)

        # Buttons — OK disabled until a row is selected
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    # ── Data loading ──────────────────────────────────────────────────

    def _load(self, search: str = "") -> None:
        with get_session() as session:
            repo = AliquotLocationRepository(session)
            self._aliquots = repo.get_unplaced_aliquots(search)

            self._populate_table(self._aliquots)

    def _populate_table(self, aliquots: List[SampleAliquot]) -> None:
        self._table.setRowCount(0)

        for aliquot in aliquots:
            row = self._table.rowCount()
            self._table.insertRow(row)

            pid = ""
            sample_type = ""
            if aliquot.sample:
                sample_type = aliquot.sample.sample_type or ""
                if aliquot.sample.participant:
                    pid = aliquot.sample.participant.pid or ""

            volume = f"{aliquot.volume_ul:.1f}" if aliquot.volume_ul is not None else "—"

            self._table.setItem(row, 0, QTableWidgetItem(aliquot.aliquot_id))
            self._table.setItem(row, 1, QTableWidgetItem(pid))
            self._table.setItem(row, 2, QTableWidgetItem(sample_type))
            self._table.setItem(row, 3, QTableWidgetItem(volume))

            # Store the integer PK in the first cell for retrieval
            self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, aliquot.id)

        count = self._table.rowCount()
        self._count_label.setText(f"{count} aliquot{'s' if count != 1 else ''} available")
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    # ── Slots ─────────────────────────────────────────────────────────

    @slot_safe
    def _on_search(self, text: str) -> None:
        self._load(search=text)

    @slot_safe
    def _on_selection_changed(self) -> None:
        has_selection = bool(self._table.selectedItems())
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(has_selection)

    @slot_safe
    def _on_double_click(self) -> None:
        """Double-clicking a row is a shortcut for selecting + clicking OK."""
        if self._table.selectedItems():
            self._on_accept()

    def _on_accept(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            return

        row = self._table.currentRow()
        self.selected_aliquot_id = self._table.item(row, 0).data(
            Qt.ItemDataRole.UserRole
        )
        self.accept()
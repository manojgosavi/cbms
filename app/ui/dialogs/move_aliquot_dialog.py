"""
Move Aliquot Dialog — pick a target empty cell within the same box.

Embeds a BoxGridWidget showing the current box layout.
Occupied cells are visible but not selectable as targets.
Only empty cells can be chosen as the move destination.

The caller receives the chosen (row, col) via .target_row / .target_col.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel,
    QScrollArea, QVBoxLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.models.models import StorageBox
from app.core.services.storage_service import StorageService
from app.ui.widgets.box_grid_widget import BoxGridWidget, CellData
from app.utils.exception_handler import slot_safe


class MoveAliquotDialog(QDialog):
    """
    Grid-based target cell picker for moving an aliquot.

    Shows the full box grid. Occupied cells are displayed but clicking
    them is ignored — only empty cells register as a selection.

    Usage:
        dlg = MoveAliquotDialog(parent, box_id=5, source_row=1, source_col=2)
        if dlg.exec():
            row, col = dlg.target_row, dlg.target_col
    """

    def __init__(
        self,
        parent=None,
        box_id: int = 0,
        source_row: int = 0,
        source_col: int = 0,
    ):
        super().__init__(parent)
        self.setWindowTitle("Move Aliquot — Select Target Cell")

        self._box_id     = box_id
        self._source_row = source_row
        self._source_col = source_col

        self.target_row: Optional[int] = None
        self.target_col: Optional[int] = None

        self._build_ui()
        self._load()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Click an <b>empty</b> cell to move the aliquot there:"))

        self._status_label = QLabel("No cell selected.")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        # Wrap the grid in a scroll area in case the box is large
        self._grid = BoxGridWidget()

        # We handle selection ourselves — disable drag/drop in this context
        self._grid.setAcceptDrops(False)
        self._grid.cell_clicked.connect(self._on_cell_clicked)

        scroll = QScrollArea()
        scroll.setWidget(self._grid)
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(scroll)

        # OK disabled until a valid empty cell is selected
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        # Resize dialog to fit grid comfortably (grid has a fixed size)
        self.setMinimumWidth(self._grid.width() + 60)

    # ── Data loading ──────────────────────────────────────────────────

    def _load(self) -> None:
        with get_session() as session:
            svc = StorageService(session)
            box: Optional[StorageBox] = svc.get_box_grid(self._box_id)
            if not box:
                return

            self._grid.set_grid_size(box.rows, box.cols)

            cells = []
            for pos in box.positions:
                loc = pos.aliquot_location
                aliquot_id    = None
                aliquot_label = None
                tooltip       = None
                is_blocked    = False
                is_shipped    = False

                if loc and loc.aliquot:
                    aliquot    = loc.aliquot
                    aliquot_id = aliquot.id
                    pid        = ""
                    if aliquot.sample and aliquot.sample.participant:
                        pid = aliquot.sample.participant.pid or ""
                    aliquot_label = pid or aliquot.aliquot_id
                    tooltip       = aliquot.aliquot_id
                    is_blocked    = aliquot.is_blocked
                    is_shipped    = aliquot.is_shipped

                cells.append(CellData(
                    row=pos.row,
                    col=pos.col,
                    position_id=pos.id,
                    aliquot_id=aliquot_id,
                    aliquot_label=aliquot_label,
                    tooltip=tooltip,
                    is_blocked=is_blocked,
                    is_shipped=is_shipped,
                ))

            self._grid.load_cells(cells)
            self.setMinimumWidth(self._grid.width() + 60)

    # ── Slots ─────────────────────────────────────────────────────────

    @slot_safe
    def _on_cell_clicked(self, row: int, col: int) -> None:
        # Ignore clicks on the source cell itself
        if row == self._source_row and col == self._source_col:
            self._grid.clear_selection()
            self._status_label.setText("That is the current position — pick a different cell.")
            self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return

        # Ignore clicks on occupied cells
        cell = self._grid._cells.get((row, col))
        if cell and cell.aliquot_id is not None:
            self._grid.clear_selection()
            self._status_label.setText("That cell is occupied — pick an empty cell.")
            self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return

        # Valid empty target
        col_label = chr(ord('A') + col) if col < 26 else f"C{col}"
        self._status_label.setText(
            f"Selected: row {row + 1}, column {col_label}"
        )
        self.target_row = row
        self.target_col = col
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
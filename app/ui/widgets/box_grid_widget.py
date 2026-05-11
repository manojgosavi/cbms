"""
BoxGridWidget — interactive visual grid for a storage box.

Key PyQt6 concepts introduced here:

  paintEvent(QPaintEvent):
    Every QWidget has a paintEvent. PyQt calls it whenever the widget
    needs to redraw (on resize, on data change, etc.).
    We override it to draw each cell manually using QPainter.
    This gives us full control — colours, text, borders.

  mousePressEvent / mouseDoubleClickEvent:
    We override these to detect which cell was clicked.
    We translate the pixel (x, y) into a (row, col) using simple math:
      row = y // cell_height,  col = x // cell_width

  Drag and Drop (Qt.DropAction):
    dragEnterEvent  — something is being dragged over us; do we accept it?
    dragMoveEvent   — dragged item is moving across our surface
    dropEvent       — item was dropped; do the actual move here
    startDrag()     — begins a drag from a cell that has an aliquot

  QToolTip.showText():
    Shows a floating tooltip at a given screen position.
    We trigger this in mouseMoveEvent to show aliquot details on hover.

  Signals (pyqtSignal):
    Custom signals let our widget notify the parent tab about events
    without knowing anything about the parent.
    e.g. cell_clicked = pyqtSignal(int, int)  →  emitted with (row, col)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from PyQt6.QtCore import (
    QMimeData, QPoint, QRect, QSize, Qt, pyqtSignal
)
from PyQt6.QtGui import (
    QBrush, QColor, QDrag, QFont, QFontMetrics, QPainter, QPen, QPixmap
)
from PyQt6.QtWidgets import QSizePolicy, QToolTip, QWidget


# ── Cell data model ────────────────────────────────────────────────────────
# A lightweight dataclass (no SQLAlchemy) that the widget works with.
# We decouple the widget from the DB layer — the parent loads data from DB
# and passes these objects in. The widget only knows about CellData.

@dataclass
class CellData:
    row: int
    col: int
    position_id: int
    aliquot_id: Optional[int]     = None
    aliquot_label: Optional[str]  = None   # short label shown in cell (PID)
    tooltip: Optional[str]        = None   # full info on hover
    is_blocked: bool               = False
    is_shipped: bool               = False
    is_selected: bool              = False


# ── Colours ────────────────────────────────────────────────────────────────

COLOR_EMPTY    = QColor("#F8F9FA")
COLOR_OCCUPIED = QColor("#4A90D9")
COLOR_BLOCKED  = QColor("#E8A838")
COLOR_SHIPPED  = QColor("#A0A0A0")
COLOR_SELECTED = QColor("#2ECC71")
COLOR_HOVER    = QColor("#D0E8FF")
COLOR_BORDER   = QColor("#CCCCCC")
COLOR_BORDER_SEL = QColor("#1A7FCC")
COLOR_TEXT     = QColor("#FFFFFF")
COLOR_TEXT_DARK = QColor("#333333")


class BoxGridWidget(QWidget):
    """
    Draws a rows × cols grid. Each cell can be empty or hold an aliquot.

    Signals:
      cell_clicked(row, col)         — single click on any cell
      cell_double_clicked(row, col)  — double click
      aliquot_dropped(aliquot_id, target_row, target_col)
                                     — drag-drop completed
    """

    cell_clicked         = pyqtSignal(int, int)
    cell_double_clicked  = pyqtSignal(int, int)
    aliquot_dropped      = pyqtSignal(int, int, int)  # aliquot_id, row, col

    CELL_SIZE    = 80   # px per cell (square) — increased from 54 for better PID visibility
    CELL_PADDING = 4
    HEADER_SIZE  = 22   # px for row/col labels

    def __init__(self, rows: int = 9, cols: int = 9, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols

        # Grid data: (row, col) → CellData
        self._cells: Dict[Tuple[int, int], CellData] = {}
        self._hover_cell: Optional[Tuple[int, int]] = None
        self._selected_cell: Optional[Tuple[int, int]] = None

        # Enable mouse tracking so we get mouseMoveEvent without button held
        self.setMouseTracking(True)

        # Accept drag drops
        self.setAcceptDrops(True)

        # Fixed size based on grid dimensions
        self._update_size()
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # ── Public API ─────────────────────────────────────────────────────────

    def load_cells(self, cells: list[CellData]) -> None:
        """Replace grid contents. Call after loading data from DB."""
        self._cells = {(c.row, c.col): c for c in cells}
        self.update()   # trigger repaint

    def set_grid_size(self, rows: int, cols: int) -> None:
        self.rows = rows
        self.cols = cols
        self._cells.clear()
        self._update_size()
        self.update()

    def get_selected_cell(self) -> Optional[Tuple[int, int]]:
        return self._selected_cell

    def clear_selection(self) -> None:
        self._selected_cell = None
        self.update()

    # ── Size helpers ───────────────────────────────────────────────────────

    def _update_size(self) -> None:
        w = self.HEADER_SIZE + self.cols * self.CELL_SIZE + 2
        h = self.HEADER_SIZE + self.rows * self.CELL_SIZE + 2
        self.setFixedSize(w, h)

    def _cell_rect(self, row: int, col: int) -> QRect:
        """Return the QRect for a given (row, col) cell."""
        x = self.HEADER_SIZE + col * self.CELL_SIZE
        y = self.HEADER_SIZE + row * self.CELL_SIZE
        return QRect(x, y, self.CELL_SIZE, self.CELL_SIZE)

    def _cell_at(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        """
        Convert pixel coordinates to (row, col).
        Returns None if outside the grid area.
        """
        x -= self.HEADER_SIZE
        y -= self.HEADER_SIZE
        if x < 0 or y < 0:
            return None
        col = int(x // self.CELL_SIZE)
        row = int(y // self.CELL_SIZE)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return (row, col)
        return None

    # ── Paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """
        Called by Qt whenever the widget needs to redraw.
        We use QPainter to draw every cell, header labels, and borders.

        QPainter workflow:
          1. painter.begin(self)  — start drawing on this widget
          2. Set pen (border/line colour) and brush (fill colour)
          3. Draw shapes, text
          4. painter.end()  — finish (or just let it go out of scope)
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font_small = QFont()
        font_small.setPointSize(8)

        # ── Draw column headers (A, B, C...) ──────────────────────────────
        painter.setFont(font_small)
        painter.setPen(QPen(QColor("#666666")))
        for col in range(self.cols):
            x = self.HEADER_SIZE + col * self.CELL_SIZE
            label = chr(ord('A') + col) if col < 26 else f"C{col}"
            painter.drawText(
                QRect(x, 0, self.CELL_SIZE, self.HEADER_SIZE),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        # ── Draw row headers (1, 2, 3...) ─────────────────────────────────
        for row in range(self.rows):
            y = self.HEADER_SIZE + row * self.CELL_SIZE
            painter.drawText(
                QRect(0, y, self.HEADER_SIZE, self.CELL_SIZE),
                Qt.AlignmentFlag.AlignCenter,
                str(row + 1),
            )

        # ── Draw cells ────────────────────────────────────────────────────
        for row in range(self.rows):
            for col in range(self.cols):
                rect = self._cell_rect(row, col)
                cell = self._cells.get((row, col))
                is_hover    = (row, col) == self._hover_cell
                is_selected = (row, col) == self._selected_cell

                # Choose fill colour
                if is_selected:
                    fill = COLOR_SELECTED
                elif is_hover and (cell is None or cell.aliquot_id is None):
                    fill = COLOR_HOVER
                elif cell and cell.is_shipped:
                    fill = COLOR_SHIPPED
                elif cell and cell.is_blocked:
                    fill = COLOR_BLOCKED
                elif cell and cell.aliquot_id:
                    fill = COLOR_OCCUPIED
                else:
                    fill = COLOR_EMPTY

                # Border
                border_color = COLOR_BORDER_SEL if is_selected else COLOR_BORDER
                border_width = 2 if is_selected else 1

                painter.setBrush(QBrush(fill))
                painter.setPen(QPen(border_color, border_width))
                painter.drawRect(rect)

                # Draw label text inside occupied cells
                if cell and cell.aliquot_label:
                    inner = rect.adjusted(
                        self.CELL_PADDING, self.CELL_PADDING,
                        -self.CELL_PADDING, -self.CELL_PADDING
                    )
                    text_color = (COLOR_TEXT_DARK
                                  if fill in (COLOR_EMPTY, COLOR_HOVER)
                                  else COLOR_TEXT)
                    painter.setPen(QPen(text_color))
                    self._draw_fitted_label(painter, inner, cell.aliquot_label)

        painter.end()

    def _draw_fitted_label(self, painter: QPainter, rect: QRect, text: str) -> None:
        """Draw text inside rect, shrinking font until it fits, then elide."""
        for pt in (10, 8, 7, 6):
            font = QFont()
            font.setPointSize(pt)
            font.setBold(pt >= 8)
            fm = QFontMetrics(font)
            if fm.horizontalAdvance(text) <= rect.width():
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
                return
        # Minimum size — elide if still overflowing
        font = QFont()
        font.setPointSize(6)
        font.setBold(False)
        painter.setFont(font)
        fm = QFontMetrics(font)
        elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, rect.width())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, elided)

    # ── Mouse events ───────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        rc = self._cell_at(event.position().x(), event.position().y())
        if rc:
            self._selected_cell = rc
            self.update()
            self.cell_clicked.emit(rc[0], rc[1])

            # Start drag if cell has an aliquot
            cell = self._cells.get(rc)
            if (cell and cell.aliquot_id and
                    event.button() == Qt.MouseButton.LeftButton):
                self._start_drag(cell)

    def mouseDoubleClickEvent(self, event):
        rc = self._cell_at(event.position().x(), event.position().y())
        if rc:
            self.cell_double_clicked.emit(rc[0], rc[1])

    def mouseMoveEvent(self, event):
        rc = self._cell_at(event.position().x(), event.position().y())
        if rc != self._hover_cell:
            self._hover_cell = rc
            self.update()

        # Show tooltip on occupied cells
        if rc:
            cell = self._cells.get(rc)
            if cell and cell.tooltip:
                QToolTip.showText(
                    self.mapToGlobal(event.position().toPoint()),
                    cell.tooltip,
                    self,
                )
            else:
                QToolTip.hideText()

    def leaveEvent(self, event):
        self._hover_cell = None
        self.update()

    # ── Drag and Drop ──────────────────────────────────────────────────────
    #
    # Qt drag/drop uses QMimeData to carry information.
    # We pack the aliquot_id as text in the mime data.
    # The drop target reads it back and fires our signal.

    def _start_drag(self, cell: CellData) -> None:
        """Begin a drag operation from an occupied cell."""
        drag = QDrag(self)
        mime = QMimeData()

        # Pack aliquot_id as plain text
        mime.setText(str(cell.aliquot_id))
        drag.setMimeData(mime)

        # Visual feedback — small colored square during drag
        pixmap = QPixmap(self.CELL_SIZE - 4, self.CELL_SIZE - 4)
        pixmap.fill(COLOR_OCCUPIED)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        """Accept drags that carry an aliquot_id (plain text integer)."""
        if event.mimeData().hasText():
            try:
                int(event.mimeData().text())
                event.acceptProposedAction()
            except ValueError:
                event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Highlight the target cell as drag moves over it."""
        rc = self._cell_at(event.position().x(), event.position().y())
        if rc != self._hover_cell:
            self._hover_cell = rc
            self.update()
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Aliquot dropped — emit signal for parent to handle DB update."""
        rc = self._cell_at(event.position().x(), event.position().y())
        if rc and event.mimeData().hasText():
            try:
                aliquot_id = int(event.mimeData().text())
                self._hover_cell = None
                self.update()
                self.aliquot_dropped.emit(aliquot_id, rc[0], rc[1])
                event.acceptProposedAction()
            except ValueError:
                event.ignore()
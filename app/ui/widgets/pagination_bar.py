from __future__ import annotations

import math

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class PaginationBar(QWidget):
    """Reusable Prev / Next pagination bar."""

    page_changed = pyqtSignal(int)  # emits new page number (1-based)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 1
        self._total_pages = 1
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        self._btn_prev = QPushButton("◀  Prev")
        self._btn_prev.setFixedWidth(80)
        self._btn_prev.clicked.connect(self._on_prev)

        self._lbl = QLabel("Page 1 of 1")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setStyleSheet("color: grey; min-width: 160px;")

        self._btn_next = QPushButton("Next  ▶")
        self._btn_next.setFixedWidth(80)
        self._btn_next.clicked.connect(self._on_next)

        layout.addStretch()
        layout.addWidget(self._btn_prev)
        layout.addWidget(self._lbl)
        layout.addWidget(self._btn_next)
        layout.addStretch()

    def set_page(self, current: int, total_items: int, page_size: int = 100) -> None:
        total_pages = max(1, math.ceil(total_items / page_size))
        self._current = current
        self._total_pages = total_pages
        self._lbl.setText(f"Page {current} of {total_pages}  ({total_items} total)")
        self._btn_prev.setEnabled(current > 1)
        self._btn_next.setEnabled(current < total_pages)
        self.setVisible(total_items > page_size)

    def _on_prev(self):
        if self._current > 1:
            self.page_changed.emit(self._current - 1)

    def _on_next(self):
        if self._current < self._total_pages:
            self.page_changed.emit(self._current + 1)

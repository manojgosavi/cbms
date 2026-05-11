"""
Block Dialog — lock selected aliquots for a researcher.
"""

from __future__ import annotations

import datetime as dt
from typing import List

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QVBoxLayout,
)

from app.core.models.database import get_session
from app.core.services.blocking_service import BlockingService
from app.utils.exception_handler import slot_safe


class BlockDialog(QDialog):

    def __init__(self, parent=None, aliquot_ids: List[int] = None):
        super().__init__(parent)
        self._aliquot_ids = aliquot_ids or []
        self.setWindowTitle("Block Aliquots")
        self.setMinimumWidth(380)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel(
            f"Blocking {len(self._aliquot_ids)} aliquot(s).\n"
            "Blocked aliquots cannot be edited or moved until released."
        ))

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._researcher = QLineEdit()
        self._researcher.setPlaceholderText("Name of researcher")

        self._unblock_date = QDateEdit()
        self._unblock_date.setCalendarPopup(True)
        self._unblock_date.setDate(QDate.currentDate().addMonths(1))
        self._unblock_date.setMinimumDate(QDate.currentDate().addDays(1))

        self._reason = QTextEdit()
        self._reason.setFixedHeight(64)
        self._reason.setPlaceholderText("Reason for blocking (required)")

        form.addRow("Researcher *:", self._researcher)
        form.addRow("Unblock by *:", self._unblock_date)
        form.addRow("Reason *:",     self._reason)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        self._error.hide()
        layout.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Block")
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    @slot_safe
    def _on_save(self):
        researcher = self._researcher.text().strip()
        unblock_date = self._unblock_date.date().toPyDate()
        reason = self._reason.toPlainText().strip()

        with get_session() as session:
            svc = BlockingService(session)
            ok, msg, details = svc.block_aliquots(
                self._aliquot_ids, researcher, unblock_date, reason
            )

        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

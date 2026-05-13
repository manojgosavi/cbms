"""
Unblock Dialog — release blocked aliquots with a mandatory reason.
"""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QVBoxLayout,
)

from app.core.models.database import get_session
from app.core.services.blocking_service import BlockingService
from app.utils.exception_handler import slot_safe


class UnblockDialog(QDialog):

    def __init__(self, parent=None, aliquot_ids: List[int] = None):
        super().__init__(parent)
        self._aliquot_ids = aliquot_ids or []
        self.setWindowTitle("Unblock Aliquots")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel(
            f"Releasing block on {len(self._aliquot_ids)} aliquot(s).\n"
            "Aliquots will return to the available pool."
        ))

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._reason = QLineEdit()
        self._reason.setPlaceholderText("Reason for unblocking (required)")
        form.addRow("Reason *:", self._reason)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        self._error.hide()
        layout.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Unblock")
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    @slot_safe
    def _on_save(self):
        reason = self._reason.text().strip()
        if not reason:
            self._error.setText("A reason is required.")
            self._error.show()
            return

        with get_session() as session:
            svc = BlockingService(session)
            ok, msg = svc.release_multiple(self._aliquot_ids, reason)

        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

"""
Freezer creation / edit dialog.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QTextEdit, QVBoxLayout,
)

from app.core.models.database import get_session
from app.core.services.storage_service import StorageService
from app.utils.exception_handler import slot_safe


class FreezerDialog(QDialog):

    def __init__(self, parent=None, freezer_id: int = None):
        super().__init__(parent)
        self._freezer_id = freezer_id
        self.setWindowTitle("Edit Freezer" if freezer_id else "Create New Freezer")
        self.setMinimumWidth(400)
        self._build_ui()
        if freezer_id:
            self._load(freezer_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name  = QLineEdit()
        self._loc   = QLineEdit()
        self._temp  = QComboBox()
        self._temp.setEditable(True)
        self._temp.addItems(["-80°C", "-20°C", "-196°C (LN2)", "+4°C", "Room Temp"])
        self._cap   = QSpinBox(); self._cap.setRange(0, 9999)
        self._cap.setSpecialValueText("Unlimited")
        self._notes = QTextEdit(); self._notes.setFixedHeight(60)

        form.addRow("Name *:", self._name)
        form.addRow("Location:", self._loc)
        form.addRow("Temperature:", self._temp)
        form.addRow("Max boxes:", self._cap)
        form.addRow("Notes:", self._notes)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        self._error.hide()
        layout.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load(self, freezer_id: int):
        with get_session() as session:
            svc = StorageService(session)
            f = svc.freezer_repo.get_by_id(freezer_id)
            if not f:
                return
            self._name.setText(f.name)
            self._loc.setText(f.location or "")
            self._temp.setCurrentText(f.temperature or "")
            self._cap.setValue(f.capacity_boxes or 0)
            self._notes.setText(f.notes or "")

    @slot_safe
    def _on_save(self):
        with get_session() as session:
            svc = StorageService(session)
            if self._freezer_id:
                ok, msg = svc.update_freezer(
                    self._freezer_id,
                    name=self._name.text().strip(),
                    location=self._loc.text().strip(),
                    temperature=self._temp.currentText().strip(),
                    capacity_boxes=self._cap.value() or None,
                    notes=self._notes.toPlainText().strip(),
                )
            else:
                ok, msg, _ = svc.create_freezer(
                    name=self._name.text().strip(),
                    location=self._loc.text().strip(),
                    temperature=self._temp.currentText().strip(),
                    capacity_boxes=self._cap.value() or None,
                    notes=self._notes.toPlainText().strip(),
                )
        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

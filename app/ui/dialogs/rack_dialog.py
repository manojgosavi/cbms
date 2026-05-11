"""
Rack creation / edit dialog.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QVBoxLayout,
)

from app.core.models.database import get_session
from app.core.services.storage_service import StorageService
from app.utils.exception_handler import slot_safe


class RackDialog(QDialog):

    def __init__(self, parent=None, compartment_id: int = None, rack_id: int = None):
        super().__init__(parent)
        self._compartment_id = compartment_id
        self._rack_id = rack_id
        self.setWindowTitle("Edit Rack" if rack_id else "Create New Rack")
        self.setMinimumWidth(400)
        self._build_ui()
        self._load_compartments()
        if rack_id:
            self._load(rack_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name        = QLineEdit()
        self._compartment = QComboBox()
        self._notes       = QTextEdit(); self._notes.setFixedHeight(60)

        form.addRow("Name *:", self._name)
        form.addRow("Compartment *:", self._compartment)
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

    def _load_compartments(self):
        with get_session() as session:
            svc = StorageService(session)
            freezers = svc.get_all_freezers()
            for f in freezers:
                for comp in f.compartments:
                    self._compartment.addItem(f"{f.name} / {comp.name}", comp.id)
        if self._compartment_id:
            idx = self._compartment.findData(self._compartment_id)
            if idx >= 0:
                self._compartment.setCurrentIndex(idx)

    def _load(self, rack_id: int):
        with get_session() as session:
            svc = StorageService(session)
            rack = svc.rack_repo.get_by_id(rack_id)
            if not rack:
                return
            self._name.setText(rack.name)
            idx = self._compartment.findData(rack.compartment_id)
            if idx >= 0:
                self._compartment.setCurrentIndex(idx)
            self._compartment.setEnabled(False)
            self._notes.setText(rack.notes or "")

    @slot_safe
    def _on_save(self):
        with get_session() as session:
            svc = StorageService(session)
            if self._rack_id:
                ok, msg = svc.update_rack(
                    self._rack_id,
                    name=self._name.text().strip(),
                    notes=self._notes.toPlainText().strip(),
                )
            else:
                ok, msg, _ = svc.create_rack(
                    name=self._name.text().strip(),
                    compartment_id=self._compartment.currentData(),
                    notes=self._notes.toPlainText().strip(),
                )
        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

"""
Compartment creation / edit dialog.
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


class CompartmentDialog(QDialog):

    def __init__(self, parent=None, freezer_id: int = None, compartment_id: int = None):
        super().__init__(parent)
        self._freezer_id = freezer_id
        self._compartment_id = compartment_id
        self.setWindowTitle("Edit Compartment" if compartment_id else "Create New Compartment")
        self.setMinimumWidth(400)
        self._build_ui()
        self._load_freezers()
        if compartment_id:
            self._load(compartment_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name    = QLineEdit()
        self._freezer = QComboBox()
        self._notes   = QTextEdit(); self._notes.setFixedHeight(60)

        form.addRow("Name *:", self._name)
        form.addRow("Freezer *:", self._freezer)
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

    def _load_freezers(self):
        with get_session() as session:
            svc = StorageService(session)
            for f in svc.get_all_freezers():
                self._freezer.addItem(f.name, f.id)
        if self._freezer_id:
            idx = self._freezer.findData(self._freezer_id)
            if idx >= 0:
                self._freezer.setCurrentIndex(idx)

    def _load(self, compartment_id: int):
        with get_session() as session:
            svc = StorageService(session)
            comp = svc.comp_repo.get_by_id(compartment_id)
            if not comp:
                return
            self._name.setText(comp.name)
            idx = self._freezer.findData(comp.freezer_id)
            if idx >= 0:
                self._freezer.setCurrentIndex(idx)
            self._freezer.setEnabled(False)
            self._notes.setText(comp.notes or "")

    @slot_safe
    def _on_save(self):
        with get_session() as session:
            svc = StorageService(session)
            if self._compartment_id:
                ok, msg = svc.update_compartment(
                    self._compartment_id,
                    name=self._name.text().strip(),
                    notes=self._notes.toPlainText().strip(),
                )
            else:
                ok, msg, _ = svc.create_compartment(
                    name=self._name.text().strip(),
                    freezer_id=self._freezer.currentData(),
                    notes=self._notes.toPlainText().strip(),
                )
        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

"""
Drawer creation / edit dialog.
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


class DrawerDialog(QDialog):

    def __init__(self, parent=None, rack_id: int = None, drawer_id: int = None):
        super().__init__(parent)
        self._rack_id = rack_id
        self._drawer_id = drawer_id
        self.setWindowTitle("Edit Drawer" if drawer_id else "Create New Drawer")
        self.setMinimumWidth(400)
        self._build_ui()
        self._load_racks()
        if drawer_id:
            self._load(drawer_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name  = QLineEdit()
        self._rack  = QComboBox()
        self._notes = QTextEdit(); self._notes.setFixedHeight(60)

        form.addRow("Name *:", self._name)
        form.addRow("Rack *:", self._rack)
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

    def _load_racks(self):
        with get_session() as session:
            svc = StorageService(session)
            freezers = svc.get_all_freezers()
            for f in freezers:
                for comp in f.compartments:
                    for rack in comp.racks:
                        label = f"{f.name} / {comp.name} / {rack.name}"
                        self._rack.addItem(label, rack.id)
        if self._rack_id:
            idx = self._rack.findData(self._rack_id)
            if idx >= 0:
                self._rack.setCurrentIndex(idx)

    def _load(self, drawer_id: int):
        with get_session() as session:
            svc = StorageService(session)
            drawer = svc.drawer_repo.get_by_id(drawer_id)
            if not drawer:
                return
            self._name.setText(drawer.name)
            idx = self._rack.findData(drawer.rack_id)
            if idx >= 0:
                self._rack.setCurrentIndex(idx)
            self._rack.setEnabled(False)
            self._notes.setText(drawer.notes or "")

    @slot_safe
    def _on_save(self):
        with get_session() as session:
            svc = StorageService(session)
            if self._drawer_id:
                ok, msg = svc.update_drawer(
                    self._drawer_id,
                    name=self._name.text().strip(),
                    notes=self._notes.toPlainText().strip(),
                )
            else:
                ok, msg, _ = svc.create_drawer(
                    name=self._name.text().strip(),
                    rack_id=self._rack.currentData(),
                    notes=self._notes.toPlainText().strip(),
                )
        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

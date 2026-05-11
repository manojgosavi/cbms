"""
Storage Box creation / edit dialog.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QTextEdit, QVBoxLayout,
)

from app.config import BOX_GRID_SIZES
from app.core.models.database import get_session
from app.core.services.storage_service import StorageService
from app.core.services.study_service import StudyService
from app.utils.exception_handler import slot_safe


class BoxDialog(QDialog):

    def __init__(self, parent=None, drawer_id: int = None, box_id: int = None):
        super().__init__(parent)
        self._drawer_id = drawer_id
        self._box_id = box_id
        self.setWindowTitle("Edit Box" if box_id else "Create New Storage Box")
        self.setMinimumWidth(440)
        self._build_ui()
        self._load_data()
        if box_id:
            self._load_box(box_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name   = QLineEdit()
        self._drawer = QComboBox()
        self._study  = QComboBox()
        self._study.addItem("— None —", None)

        self._preset = QComboBox()
        for r, c in BOX_GRID_SIZES:
            self._preset.addItem(f"{r} × {c}", (r, c))
        self._preset.addItem("Custom…", None)
        self._preset.currentIndexChanged.connect(self._on_preset_changed)

        size_row = QHBoxLayout()
        self._rows = QSpinBox(); self._rows.setRange(1, 20); self._rows.setValue(9)
        self._cols = QSpinBox(); self._cols.setRange(1, 20); self._cols.setValue(9)
        size_row.addWidget(QLabel("Rows:")); size_row.addWidget(self._rows)
        size_row.addWidget(QLabel("  Cols:")); size_row.addWidget(self._cols)

        self._notes = QTextEdit(); self._notes.setFixedHeight(56)

        form.addRow("Name *:", self._name)
        form.addRow("Drawer *:", self._drawer)
        form.addRow("Study:", self._study)
        form.addRow("Grid preset:", self._preset)
        form.addRow("Grid size:", size_row)
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

    def _load_data(self):
        with get_session() as session:
            storage_svc = StorageService(session)
            study_svc   = StudyService(session)

            freezers = storage_svc.get_all_freezers()
            for f in freezers:
                for comp in f.compartments:
                    for rack in comp.racks:
                        for drawer in rack.drawers:
                            label = f"{f.name} / {comp.name} / {rack.name} / {drawer.name}"
                            self._drawer.addItem(label, drawer.id)

            for s in study_svc.get_all_active():
                self._study.addItem(s.project_id_short, s.id)

        if self._drawer_id:
            idx = self._drawer.findData(self._drawer_id)
            if idx >= 0:
                self._drawer.setCurrentIndex(idx)

    def _load_box(self, box_id: int):
        with get_session() as session:
            svc = StorageService(session)
            box = svc.box_repo.get_by_id(box_id)
            if not box:
                return
            self._name.setText(box.name)
            idx = self._drawer.findData(box.drawer_id)
            if idx >= 0:
                self._drawer.setCurrentIndex(idx)
            self._rows.setValue(box.rows)
            self._cols.setValue(box.cols)
            self._rows.setEnabled(False)
            self._cols.setEnabled(False)
            self._preset.setEnabled(False)
            self._notes.setText(box.notes or "")

    @slot_safe
    def _on_preset_changed(self, idx: int):
        val = self._preset.currentData()
        if val:
            rows, cols = val
            self._rows.setValue(rows)
            self._cols.setValue(cols)
            self._rows.setEnabled(False)
            self._cols.setEnabled(False)
        else:
            self._rows.setEnabled(True)
            self._cols.setEnabled(True)

    @slot_safe
    def _on_save(self):
        with get_session() as session:
            svc = StorageService(session)
            if self._box_id:
                box = svc.box_repo.get_by_id(self._box_id)
                if box:
                    box.name = self._name.text().strip()
                    box.notes = self._notes.toPlainText()
                    svc.box_repo.update(box)
                ok, msg = True, "Box updated."
            else:
                ok, msg, _ = svc.create_box(
                    name=self._name.text().strip(),
                    drawer_id=self._drawer.currentData(),
                    rows=self._rows.value(),
                    cols=self._cols.value(),
                    study_id=self._study.currentData(),
                    notes=self._notes.toPlainText(),
                )
        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

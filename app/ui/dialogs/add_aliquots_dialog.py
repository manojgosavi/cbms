"""Add aliquots to an existing sample."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLabel, QSpinBox, QVBoxLayout,
)
from app.core.models.database import get_session
from app.core.services.sample_service import SampleService


class AddAliquotsDialog(QDialog):

    def __init__(self, parent=None, sample_id: int = None):
        super().__init__(parent)
        self._sample_id = sample_id
        self.setWindowTitle("Add Aliquots")
        self.setMinimumWidth(300)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._count = QSpinBox()
        self._count.setRange(1, 200)
        self._count.setValue(1)

        self._vol = QDoubleSpinBox()
        self._vol.setRange(0, 9999)
        self._vol.setSuffix(" µL")
        self._vol.setSpecialValueText("Not recorded")

        form.addRow("Number to add:", self._count)
        form.addRow("Volume each:",   self._vol)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        self._error.hide()
        layout.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_save(self):
        with get_session() as session:
            svc = SampleService(session)
            ok, msg = svc.add_aliquots(
                self._sample_id,
                count=self._count.value(),
                volume_ul=self._vol.value() or None,
            )
        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

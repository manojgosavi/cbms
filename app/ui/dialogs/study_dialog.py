"""
Study registration / edit dialog.

PyQt6 concepts:
  - QDateEdit       : date picker with calendar popup
  - QTextEdit       : multi-line text input
  - QScrollArea     : makes the form scrollable if the window is small
  - setData()       : attach arbitrary Python value to a combo box item
"""

from __future__ import annotations

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QMessageBox, QScrollArea,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.services.study_service import StudyService
from app.utils.exception_handler import slot_safe


class StudyDialog(QDialog):
    """Create a new study or edit an existing one."""

    def __init__(self, parent=None, study_id: int = None):
        super().__init__(parent)
        self._study_id = study_id
        self.setWindowTitle("Edit Study" if study_id else "New Study / Project")
        self.setMinimumWidth(460)
        self._build_ui()
        if study_id:
            self._load_study(study_id)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        # Scrollable form area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        self._short_id  = QLineEdit(); self._short_id.setPlaceholderText("e.g. COH")
        self._name      = QLineEdit(); self._name.setPlaceholderText("Full study name")
        self._pi        = QLineEdit(); self._pi.setPlaceholderText("Principal Investigator name")
        self._site      = QLineEdit(); self._site.setPlaceholderText("Site / institution")
        self._desc      = QTextEdit(); self._desc.setFixedHeight(72)

        self._start = QDateEdit(); self._start.setCalendarPopup(True)
        self._start.setDate(QDate.currentDate())
        self._end   = QDateEdit(); self._end.setCalendarPopup(True)
        self._end.setDate(QDate.currentDate().addYears(1))

        form.addRow("Short ID *:", self._short_id)
        form.addRow("Study Name *:", self._name)
        form.addRow("PI Name:", self._pi)
        form.addRow("Site:", self._site)
        form.addRow("Description:", self._desc)
        form.addRow("Start Date:", self._start)
        form.addRow("End Date:", self._end)

        scroll.setWidget(content)
        root.addWidget(scroll)

        # Error label
        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        self._error.hide()
        root.addWidget(self._error)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_study(self, study_id: int):
        """Pre-fill form when editing an existing study."""
        with get_session() as session:
            service = StudyService(session)
            study = service.get_by_id(study_id)
            if not study:
                return
            self._short_id.setText(study.project_id_short)
            self._short_id.setEnabled(False)   # short ID is immutable after creation
            self._name.setText(study.name)
            self._pi.setText(study.pi_name or "")
            self._site.setText(study.site_name or "")
            self._desc.setText(study.description or "")
            if study.start_date:
                d = study.start_date
                self._start.setDate(QDate(d.year, d.month, d.day))
            if study.end_date:
                d = study.end_date
                self._end.setDate(QDate(d.year, d.month, d.day))

    @slot_safe
    def _on_save(self):
        short_id = self._short_id.text().strip()
        name     = self._name.text().strip()

        with get_session() as session:
            service = StudyService(session)

            if self._study_id:
                ok, msg = service.update_study(
                    self._study_id,
                    name=name,
                    pi_name=self._pi.text().strip(),
                    site_name=self._site.text().strip(),
                    description=self._desc.toPlainText().strip(),
                )
            else:
                start = self._start.date().toPyDate()
                end   = self._end.date().toPyDate()
                ok, msg, _ = service.create_study(
                    project_id_short=short_id,
                    name=name,
                    description=self._desc.toPlainText().strip(),
                    site_name=self._site.text().strip(),
                    pi_name=self._pi.text().strip(),
                    start_date=start,
                    end_date=end,
                )

        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

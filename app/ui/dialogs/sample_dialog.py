"""
Sample registration / edit dialog.
Uses Excel column names: Date Collected, Visit Code, Visit Time, Visit Name, Sample Type
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QMessageBox, QScrollArea, QSpinBox,
    QTextEdit, QTimeEdit, QVBoxLayout, QWidget,
)

from app.config import SampleType, VisitName
from app.core.models.database import get_session
from app.core.services.sample_service import SampleService
from app.core.services.study_service import StudyService
from app.core.services.participant_service import ParticipantService
from app.utils.exception_handler import slot_safe


class SampleDialog(QDialog):

    def __init__(self, parent=None, participant_id: int = None, sample_id: int = None, study_id: int = None):
        super().__init__(parent)
        self._participant_id = participant_id
        self._sample_id = sample_id
        self._study_id = study_id
        self.setWindowTitle("Edit Sample" if sample_id else "Register Sample")
        self.setMinimumWidth(440)
        self._build_ui()
        self._load_data()
        if sample_id:
            self._load_sample(sample_id)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        self._participant_combo = QComboBox()

        # Excel columns
        self._date_collected = QDateEdit()
        self._date_collected.setCalendarPopup(True)
        self._date_collected.setDate(QDate.currentDate())

        self._visit_code = QLineEdit()
        self._visit_code.setPlaceholderText("e.g. SCR(NA), M0, M3")

        self._visit_time = QLineEdit()
        self._visit_time.setPlaceholderText("e.g. 09:30, 14.5 (decimal)")

        self._visit_name = QComboBox()
        self._visit_name.addItem("", None)
        for choice in VisitName:
            self._visit_name.addItem(choice.value, choice.value)

        self._sample_type = QComboBox()
        self._sample_type.addItem("", None)
        for choice in SampleType:
            self._sample_type.addItem(choice.value, choice.value)

        self._collected_volume = QLineEdit()
        self._collected_volume.setPlaceholderText("e.g. 5.0")

        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)

        form.addRow("Participant *:",    self._participant_combo)
        form.addRow("Date Collected:",   self._date_collected)
        form.addRow("Visit Code:",       self._visit_code)
        form.addRow("Visit Time:",       self._visit_time)
        form.addRow("Visit Name:",       self._visit_name)
        form.addRow("Sample Type *:",    self._sample_type)
        form.addRow("Volume (mL):",      self._collected_volume)
        form.addRow("Notes:",            self._notes)

        scroll.setWidget(content)
        root.addWidget(scroll)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        self._error.hide()
        root.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load_data(self):
        with get_session() as session:
            participant_svc = ParticipantService(session)
            if self._study_id:
                participants, _ = participant_svc.search({"study_id": self._study_id}, page_size=500)
            else:
                # Fallback: load all if no study specified (e.g., in edit mode from stored sample)
                participants = participant_svc.get_all()
            
            # Remove duplicates by participant ID (safety check)
            seen = set()
            unique_participants = []
            for p in participants:
                if p.id not in seen:
                    seen.add(p.id)
                    unique_participants.append(p)
            
            for p in unique_participants:
                self._participant_combo.addItem(p.pid, p.id)

        if self._participant_id:
            idx = self._participant_combo.findData(self._participant_id)
            if idx >= 0:
                self._participant_combo.setCurrentIndex(idx)

    def _load_sample(self, sample_id: int):
        with get_session() as session:
            svc = SampleService(session)
            sample = svc.get_by_id(sample_id)
            if not sample:
                return
            idx = self._participant_combo.findData(sample.participant_id)
            if idx >= 0:
                self._participant_combo.setCurrentIndex(idx)
            self._participant_combo.setEnabled(False)

            if sample.collection_date:
                self._date_collected.setDate(sample.collection_date)
            self._visit_code.setText(sample.visit_code or "")
            self._visit_time.setText(sample.visit_time or "")
            self._visit_name.setCurrentText(sample.visit_name or "")
            self._sample_type.setCurrentText(sample.sample_type or "")
            self._collected_volume.setText(str(sample.collected_volume_ml) if sample.collected_volume_ml else "")
            self._notes.setText(sample.notes or "")

    @slot_safe
    def _on_save(self):
        participant_id = self._participant_combo.currentData()
        if not participant_id:
            self._error.setText("Participant is required.")
            self._error.show()
            return

        sample_type = self._sample_type.currentData()
        if not sample_type:
            self._error.setText("Sample Type is required.")
            self._error.show()
            return

        try:
            volume = float(self._collected_volume.text()) if self._collected_volume.text().strip() else None
        except ValueError:
            self._error.setText("Volume must be a number.")
            self._error.show()
            return

        with get_session() as session:
            svc = SampleService(session)
            if self._sample_id:
                ok, msg = svc.update_sample(
                    self._sample_id,
                    collection_date=self._date_collected.date().toPyDate(),
                    visit_code=self._visit_code.text().strip() or None,
                    visit_time=self._visit_time.text().strip() or None,
                    visit_name=self._visit_name.currentData(),
                    sample_type=sample_type,
                    collected_volume_ml=volume,
                    notes=self._notes.toPlainText().strip(),
                )
            else:
                ok, msg, _ = svc.create_sample(
                    participant_id=participant_id,
                    sample_type=sample_type,
                    collection_date=self._date_collected.date().toPyDate(),
                    visit_code=self._visit_code.text().strip() or None,
                    visit_time=self._visit_time.text().strip() or None,
                    visit_name=self._visit_name.currentData(),
                    collected_volume_ml=volume,
                    notes=self._notes.toPlainText().strip(),
                )

        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

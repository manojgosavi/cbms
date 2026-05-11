"""
Participant registration / edit dialog.
Uses Excel column names: PID, Age, Gender, Population, Disease, Site Name, Cohort Name
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QMessageBox, QScrollArea,
    QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from app.config import (
    Gender, Population, Disease, Site, CohortName
)
from app.core.models.database import get_session
from app.core.services.participant_service import ParticipantService
from app.core.services.study_service import StudyService
from app.utils.exception_handler import slot_safe


class ParticipantDialog(QDialog):

    def __init__(self, parent=None, study_id: int = None,
                 participant_id: int = None, preselect_study_id: int = None):
        super().__init__(parent)
        self._participant_id = participant_id
        self._preselect_study_id = preselect_study_id or study_id
        self.setWindowTitle("Edit Participant" if participant_id else "Register Participant")
        self.setMinimumWidth(460)
        self._build_ui()
        self._load_studies()
        if participant_id:
            self._load_participant(participant_id)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        self._study_combo = QComboBox()

        # User-provided PID (not auto-generated)
        self._pid = QLineEdit()
        self._pid.setPlaceholderText("e.g. P001, STUDY-001")

        self._age = QSpinBox()
        self._age.setRange(0, 150)
        self._age.setSpecialValueText("—")

        # Gender dropdown with enums
        self._gender = QComboBox()
        self._gender.addItem("", None)
        for choice in Gender:
            self._gender.addItem(choice.value, choice.value)

        # Population dropdown with enums
        self._population = QComboBox()
        self._population.addItem("", None)
        for choice in Population:
            self._population.addItem(choice.value, choice.value)

        # Disease dropdown with enums
        self._disease = QComboBox()
        self._disease.addItem("", None)
        for choice in Disease:
            self._disease.addItem(choice.value, choice.value)

        # Site dropdown with enums
        self._site = QComboBox()
        self._site.addItem("", None)
        for choice in Site:
            self._site.addItem(choice.value, choice.value)

        # Cohort Name dropdown with enums
        self._cohort_name = QComboBox()
        self._cohort_name.addItem("", None)
        for choice in CohortName:
            self._cohort_name.addItem(choice.value, choice.value)

        self._comorbidity = QTextEdit()
        self._comorbidity.setFixedHeight(56)
        self._notes      = QTextEdit()
        self._notes.setFixedHeight(56)

        form.addRow("Study *:",        self._study_combo)
        form.addRow("PID *:",          self._pid)
        form.addRow("Age:",            self._age)
        form.addRow("Gender:",         self._gender)
        form.addRow("Population:",     self._population)
        form.addRow("Disease:",        self._disease)
        form.addRow("Site Name:",      self._site)
        form.addRow("Cohort Name:",    self._cohort_name)
        form.addRow("Comorbidity:",    self._comorbidity)
        form.addRow("Notes:",          self._notes)

        scroll.setWidget(content)
        root.addWidget(scroll)

        # Buttons
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

    def _load_studies(self):
        with get_session() as session:
            svc = StudyService(session)
            for s in svc.get_all_active():
                self._study_combo.addItem(s.project_id_short, s.id)
        if self._preselect_study_id:
            idx = self._study_combo.findData(self._preselect_study_id)
            if idx >= 0:
                self._study_combo.setCurrentIndex(idx)

    def _load_participant(self, participant_id: int):
        with get_session() as session:
            svc = ParticipantService(session)
            p = svc.get_by_id(participant_id)
            if not p:
                return
            self._pid.setText(p.pid)
            self._pid.setReadOnly(True)
            self._study_combo.setEnabled(False)
            idx = self._study_combo.findData(p.study_id)
            if idx >= 0:
                self._study_combo.setCurrentIndex(idx)
            self._age.setValue(p.age or 0)
            self._gender.setCurrentText(p.gender or "")
            self._population.setCurrentText(p.population or "")
            self._disease.setCurrentText(p.disease or "")
            self._site.setCurrentText(p.site_name or "")
            self._cohort_name.setCurrentText(p.cohort_name or "")
            self._comorbidity.setText(p.comorbidity or "")
            self._notes.setText(p.notes or "")

    @slot_safe
    def _on_save(self):
        pid = self._pid.text().strip()
        if not pid:
            self._error.setText("PID is required.")
            self._error.show()
            return

        study_id = self._study_combo.currentData()
        if not study_id:
            self._error.setText("Study is required.")
            self._error.show()
            return

        with get_session() as session:
            svc = ParticipantService(session)
            if self._participant_id:
                ok, msg = svc.update_participant(
                    self._participant_id,
                    age=self._age.value() or None,
                    gender=self._gender.currentData(),
                    population=self._population.currentData(),
                    disease=self._disease.currentData(),
                    site_name=self._site.currentData(),
                    cohort_name=self._cohort_name.currentData(),
                    comorbidity=self._comorbidity.toPlainText().strip(),
                    notes=self._notes.toPlainText().strip(),
                )
            else:
                ok, msg, _ = svc.create_participant(
                    pid=pid,
                    study_id=study_id,
                    age=self._age.value() or None,
                    gender=self._gender.currentData(),
                    population=self._population.currentData(),
                    disease=self._disease.currentData(),
                    site_name=self._site.currentData(),
                    cohort_name=self._cohort_name.currentData(),
                    comorbidity=self._comorbidity.toPlainText().strip(),
                    notes=self._notes.toPlainText().strip(),
                )

        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

"""
First-run setup wizard.

Shown once on first launch when no studies exist.
Walks the user through:
  Page 1 — Welcome
  Page 2 — Change admin password
  Page 3 — Create first study
  Page 4 — Done

Key concept — QWizard:
  Qt's built-in wizard widget handles the page flow, Back/Next/Finish
  buttons, and progress indicator automatically.
  Each page is a QWizardPage subclass.
  We connect page transitions using validatePage() — returning False
  keeps the user on the current page if validation fails.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QVBoxLayout, QWizard, QWizardPage,
    QFormLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.services.auth_service import app_session, verify_password, hash_password
from app.core.services.study_service import StudyService


# ── Page 1: Welcome ────────────────────────────────────────────────────────

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to CBMS")
        self.setSubTitle(
            "Central Biorepository Management Software\n\n"
            "This wizard will help you complete the initial setup in 3 quick steps."
        )
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "You will:\n\n"
            "  1. Change the default admin password\n"
            "  2. Create your first study / project\n\n"
            "Click Next to begin."
        ))


# ── Page 2: Change admin password ─────────────────────────────────────────

class ChangePasswordPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Set admin password")
        self.setSubTitle(
            "The default password is Admin@1234. "
            "Please change it to something secure before continuing."
        )
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        self._current = QLineEdit()
        self._current.setEchoMode(QLineEdit.EchoMode.Password)
        self._current.setPlaceholderText("Enter current password")

        self._new1 = QLineEdit()
        self._new1.setEchoMode(QLineEdit.EchoMode.Password)
        self._new1.setPlaceholderText("At least 8 characters")

        self._new2 = QLineEdit()
        self._new2.setEchoMode(QLineEdit.EchoMode.Password)
        self._new2.setPlaceholderText("Repeat new password")

        form.addRow("Current password:", self._current)
        form.addRow("New password:",     self._new1)
        form.addRow("Confirm:",          self._new2)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        layout.addWidget(self._error)

    def validatePage(self) -> bool:
        current = self._current.text()
        new1    = self._new1.text()
        new2    = self._new2.text()

        if len(new1) < 8:
            self._error.setText("New password must be at least 8 characters.")
            return False
        if new1 != new2:
            self._error.setText("Passwords do not match.")
            return False

        with get_session() as session:
            from app.core.models.models import User
            user = session.query(User).filter_by(username="admin").first()
            if not user or not verify_password(current, user.password_hash):
                self._error.setText("Current password is incorrect.")
                return False
            user.password_hash = hash_password(new1)

        self._error.setText("")
        return True


# ── Page 3: Create first study ─────────────────────────────────────────────

class FirstStudyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Create your first study")
        self.setSubTitle(
            "Register your first research study or project. "
            "You can add more later from File → New Study."
        )
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        self._short_id = QLineEdit()
        self._short_id.setPlaceholderText("e.g. COH  (max 10 chars, uppercase)")
        self._short_id.setMaximumWidth(140)

        self._name = QLineEdit()
        self._name.setPlaceholderText("Full study name")

        self._pi = QLineEdit()
        self._pi.setPlaceholderText("Principal Investigator")

        form.addRow("Short ID *:", self._short_id)
        form.addRow("Study name *:", self._name)
        form.addRow("PI name:", self._pi)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        layout.addWidget(self._error)

    def validatePage(self) -> bool:
        short_id = self._short_id.text().strip()
        name     = self._name.text().strip()

        if not short_id or not name:
            self._error.setText("Short ID and study name are required.")
            return False

        with get_session() as session:
            svc = StudyService(session)
            ok, msg, _ = svc.create_study(
                project_id_short=short_id,
                name=name,
                pi_name=self._pi.text().strip(),
            )

        if not ok:
            self._error.setText(msg)
            return False

        self._error.setText("")
        return True


# ── Page 4: Done ──────────────────────────────────────────────────────────

class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Setup complete!")
        self.setSubTitle("You are ready to start using CBMS.")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Your admin password has been updated and your first study is created.\n\n"
            "Next steps:\n\n"
            "  • Add participants via File → Add New Participant\n"
            "  • Register freezers via File → Create New Freezer\n"
            "  • Bulk import participants via the Participants tab\n\n"
            "Click Finish to open the main application."
        ))


# ── Wizard shell ──────────────────────────────────────────────────────────

class SetupWizard(QWizard):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CBMS — First-time Setup")
        self.setMinimumSize(520, 400)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.addPage(WelcomePage())
        self.addPage(ChangePasswordPage())
        self.addPage(FirstStudyPage())
        self.addPage(FinishPage())

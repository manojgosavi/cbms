"""
Create User Dialog — admin creates a new user account directly.

Admin-created accounts are auto-approved (no pending approval step).
Validates that all fields are filled, email looks plausible,
and that both password fields match before submitting.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QLabel, QLineEdit, QVBoxLayout,
)

from app.config import Role
from app.core.models.database import get_session
from app.core.services.auth_service import register_user


class CreateUserDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create User")
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._username = QLineEdit()
        self._username.setPlaceholderText("Unique username")

        self._email = QLineEdit()
        self._email.setPlaceholderText("user@example.com")

        self._role = QComboBox()
        self._role.addItems(Role.ALL)

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("Minimum 6 characters")

        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm.setPlaceholderText("Re-enter password")

        form.addRow("Username:", self._username)
        form.addRow("Email:",    self._email)
        form.addRow("Role:",     self._role)
        form.addRow("Password:", self._password)
        form.addRow("Confirm:",  self._confirm)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        self._error.setWordWrap(True)
        self._error.hide()
        layout.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _show_error(self, msg: str):
        self._error.setText(msg)
        self._error.show()

    def _on_accept(self):
        self._error.hide()

        username = self._username.text().strip()
        email    = self._email.text().strip()
        role     = self._role.currentText()
        password = self._password.text()
        confirm  = self._confirm.text()

        # Validate
        if not username:
            self._show_error("Username is required.")
            return
        if not email or "@" not in email:
            self._show_error("A valid email address is required.")
            return
        if len(password) < 6:
            self._show_error("Password must be at least 6 characters.")
            return
        if password != confirm:
            self._show_error("Passwords do not match.")
            self._confirm.clear()
            self._confirm.setFocus()
            return

        with get_session() as session:
            ok, msg = register_user(
                session=session,
                username=username,
                email=email,
                password=password,
                role=role,
                auto_approve=True,
            )

        if ok:
            self.accept()
        else:
            self._show_error(msg)
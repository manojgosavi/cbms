"""
Login window.

PyQt6 concepts used here:
  - QDialog       : a modal window (blocks the rest of the app until closed)
  - QFormLayout   : automatically pairs labels with input fields
  - QLineEdit     : single-line text input; setEchoMode hides password chars
  - Signals/Slots : button.clicked.connect(self._on_login) wires the click event
  - exec()        : runs the dialog's own event loop (blocks until accepted/rejected)
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QMessageBox, QVBoxLayout,
)

from app.config import APP_TITLE
from app.core.models.database import get_session
from app.core.services.auth_service import login
from app.utils.exception_handler import slot_safe


class LoginDialog(QDialog):
    """
    Modal login dialog.
    Returns QDialog.Accepted if login succeeded, Rejected otherwise.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_TITLE} — Login")
        self.setFixedWidth(360)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # Title label
        title = QLabel(APP_TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        root.addWidget(title)

        subtitle = QLabel("Please log in to continue")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: grey;")
        root.addWidget(subtitle)

        # Form fields
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        self._username = QLineEdit()
        self._username.setPlaceholderText("Enter username")

        self._password = QLineEdit()
        self._password.setPlaceholderText("Enter password")
        # EchoMode.Password replaces characters with dots
        self._password.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Username:", self._username)
        form.addRow("Password:", self._password)
        root.addLayout(form)

        # Error label (hidden until login fails)
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.hide()
        root.addWidget(self._error_label)

        # Buttons — QDialogButtonBox gives us Ok/Cancel for free
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Login")
        # Connect signals to slots
        buttons.accepted.connect(self._on_login)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        # Allow pressing Enter to submit
        self._password.returnPressed.connect(self._on_login)

    @slot_safe
    def _on_login(self):
        """Slot called when user clicks Login or presses Enter."""
        username = self._username.text().strip()
        password = self._password.text()

        if not username or not password:
            self._show_error("Please enter both username and password.")
            return

        # Call the auth service — it handles DB lookup and bcrypt check
        with get_session() as session:
            success, message = login(session, username, password)

        if success:
            self.accept()   # closes dialog with Accepted result
        else:
            self._show_error(message)

    def _show_error(self, msg: str):
        self._error_label.setText(msg)
        self._error_label.show()
        self._password.clear()
        self._password.setFocus()

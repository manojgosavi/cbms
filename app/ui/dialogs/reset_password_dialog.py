"""Reset user password dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QVBoxLayout,
)
from app.core.models.database import get_session
from app.core.services.admin_service import AdminService


class ResetPasswordDialog(QDialog):
    def __init__(self, parent=None, user_id: int = None):
        super().__init__(parent)
        self._user_id = user_id
        self.setWindowTitle("Reset Password")
        self.setMinimumWidth(300)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._pw1 = QLineEdit()
        self._pw1.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw2 = QLineEdit()
        self._pw2.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw2.setPlaceholderText("Confirm new password")

        form.addRow("New password:", self._pw1)
        form.addRow("Confirm:",      self._pw2)
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
        pw1 = self._pw1.text()
        pw2 = self._pw2.text()
        if pw1 != pw2:
            self._error.setText("Passwords do not match.")
            self._error.show()
            return
        with get_session() as session:
            ok, msg = AdminService(session).reset_password(self._user_id, pw1)
        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

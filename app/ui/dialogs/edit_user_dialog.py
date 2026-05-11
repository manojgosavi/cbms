"""Edit user role and active status."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QLabel, QVBoxLayout,
)
from app.config import Role
from app.core.models.database import get_session
from app.core.services.admin_service import AdminService


class EditUserDialog(QDialog):
    def __init__(self, parent=None, user_id: int = None):
        super().__init__(parent)
        self._user_id = user_id
        self.setWindowTitle("Edit User")
        self.setMinimumWidth(320)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._role = QComboBox()
        self._role.addItems(Role.ALL)
        self._active = QCheckBox("Account active")

        form.addRow("Role:", self._role)
        form.addRow("",      self._active)
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

    def _load(self):
        if not self._user_id:
            return
        with get_session() as session:
            from app.core.models.models import User
            user = session.get(User, self._user_id)
            if user:
                idx = self._role.findText(user.role)
                if idx >= 0:
                    self._role.setCurrentIndex(idx)
                self._active.setChecked(user.is_active)

    def _on_save(self):
        with get_session() as session:
            ok, msg = AdminService(session).update_user(
                self._user_id,
                role=self._role.currentText(),
                is_active=self._active.isChecked(),
            )
        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

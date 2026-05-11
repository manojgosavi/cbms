"""
Reusable "please give a reason" dialog.
Used for edits, deletes, and any action that needs an audit trail reason.
"""

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel,
    QTextEdit, QVBoxLayout,
)


class ReasonDialog(QDialog):

    def __init__(self, parent=None, prompt: str = "Please provide a reason:"):
        super().__init__(parent)
        self.setWindowTitle("Reason Required")
        self.setFixedWidth(360)
        self.reason = ""
        self._build_ui(prompt)

    def _build_ui(self, prompt: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel(prompt))

        self._text = QTextEdit()
        self._text.setFixedHeight(80)
        self._text.setPlaceholderText("Enter reason…")
        layout.addWidget(self._text)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self.reason = self._text.toPlainText().strip()
        if not self.reason:
            self._text.setPlaceholderText("⚠ Reason cannot be empty.")
            return
        self.accept()

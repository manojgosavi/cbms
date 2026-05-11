"""
Shipment Dialog — ship blocked aliquots to a researcher.
Shows a summary of selected aliquots, recipient details, and courier info.
"""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout,
)

from app.core.models.database import get_session
from app.core.services.shipment_service import ShipmentService
from app.core.models.models import SampleAliquot
from app.utils.exception_handler import slot_safe


class ShipmentDialog(QDialog):

    def __init__(self, parent=None, aliquot_ids: List[int] = None):
        super().__init__(parent)
        self._aliquot_ids = aliquot_ids or []
        self.setWindowTitle("Create Shipment")
        self.setMinimumWidth(500)
        self._build_ui()
        self._load_aliquots()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Aliquot summary table
        layout.addWidget(QLabel(f"Aliquots to ship ({len(self._aliquot_ids)}):"))
        self._aliquot_table = QTableWidget(0, 4)
        self._aliquot_table.setHorizontalHeaderLabels(
            ["Aliquot ID", "Sample Type", "Blocked By", "Blocked Until"]
        )
        self._aliquot_table.setMaximumHeight(140)
        self._aliquot_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._aliquot_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._aliquot_table)

        # Recipient form
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._recipient_name  = QLineEdit()
        self._recipient_inst  = QLineEdit()
        self._recipient_email = QLineEdit()
        self._courier         = QLineEdit()
        self._tracking        = QLineEdit()
        self._notes           = QTextEdit(); self._notes.setFixedHeight(52)

        form.addRow("Recipient name *:", self._recipient_name)
        form.addRow("Institution:",      self._recipient_inst)
        form.addRow("Email:",            self._recipient_email)
        form.addRow("Courier:",          self._courier)
        form.addRow("Tracking No.:",     self._tracking)
        form.addRow("Notes:",            self._notes)
        layout.addLayout(form)

        self._warning = QLabel(
            "⚠ Shipped aliquots will be removed from storage locations automatically."
        )
        self._warning.setStyleSheet("color: #E8A838; font-size: 11px;")
        self._warning.setWordWrap(True)
        layout.addWidget(self._warning)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        self._error.hide()
        layout.addWidget(self._error)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Confirm Shipment")
        btns.accepted.connect(self._on_ship)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_aliquots(self):
        """Populate the summary table with aliquot details."""
        with get_session() as session:
            rows = []
            for aid in self._aliquot_ids:
                aliquot = session.get(SampleAliquot, aid)
                if not aliquot:
                    continue
                block = next(
                    (b for b in (aliquot.block,) if b and not b.is_released), None
                ) if hasattr(aliquot, 'block') else None
                rows.append((
                    aliquot.aliquot_id,
                    aliquot.sample.sample_type if aliquot.sample else "",
                    block.blocked_by if block else "—",
                    str(block.unblock_at.date()) if block else "—",
                ))

        self._aliquot_table.setRowCount(len(rows))
        for i, (aid, stype, by, until) in enumerate(rows):
            for j, val in enumerate([aid, stype, by, until]):
                self._aliquot_table.setItem(i, j, QTableWidgetItem(str(val)))

    @slot_safe
    def _on_ship(self):
        with get_session() as session:
            svc = ShipmentService(session)
            ok, msg, shipment = svc.create_shipment(
                aliquot_ids=self._aliquot_ids,
                recipient_name=self._recipient_name.text().strip(),
                recipient_institution=self._recipient_inst.text().strip(),
                recipient_email=self._recipient_email.text().strip(),
                courier=self._courier.text().strip(),
                tracking_number=self._tracking.text().strip(),
                notes=self._notes.toPlainText().strip(),
            )

        if ok:
            self.accept()
        else:
            self._error.setText(msg)
            self._error.show()

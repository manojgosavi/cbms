"""
Shipment Tab — history of all shipments with drill-down to items.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.services.shipment_service import ShipmentService


class ShipmentTab(QWidget):

    SHIP_COLS  = ["Ref", "Recipient", "Institution", "Shipped By",
                  "Date", "Courier", "Tracking", "Items"]
    ITEM_COLS  = ["Aliquot ID", "Sample ID", "Sample Type", "PID"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        toolbar = QHBoxLayout()
        self._lbl = QLabel("Shipment history")
        self._lbl.setStyleSheet("color: grey;")
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(self._lbl)
        toolbar.addStretch()
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: shipment list
        self._ship_table = QTableWidget()
        self._ship_table.setColumnCount(len(self.SHIP_COLS))
        self._ship_table.setHorizontalHeaderLabels(self.SHIP_COLS)
        self._ship_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._ship_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._ship_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._ship_table.setAlternatingRowColors(True)
        self._ship_table.verticalHeader().setVisible(False)
        self._ship_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._ship_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._ship_table.itemSelectionChanged.connect(self._on_shipment_selected)

        # Bottom: items in selected shipment
        bottom = QWidget()
        bot_layout = QVBoxLayout(bottom)
        bot_layout.setContentsMargins(0, 4, 0, 0)
        bot_layout.addWidget(QLabel("Aliquots in selected shipment:"))
        self._item_table = QTableWidget()
        self._item_table.setColumnCount(len(self.ITEM_COLS))
        self._item_table.setHorizontalHeaderLabels(self.ITEM_COLS)
        self._item_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._item_table.setAlternatingRowColors(True)
        self._item_table.verticalHeader().setVisible(False)
        self._item_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        bot_layout.addWidget(self._item_table)

        splitter.addWidget(self._ship_table)
        splitter.addWidget(bottom)
        splitter.setSizes([300, 200])
        layout.addWidget(splitter)

    def refresh(self):
        with get_session() as session:
            svc = ShipmentService(session)
            shipments = svc.get_all_shipments()
            data = [
                (
                    s.shipment_ref,
                    s.recipient_name,
                    s.recipient_institution or "",
                    s.shipped_by,
                    str(s.shipped_at.date()) if s.shipped_at else "",
                    s.courier or "",
                    s.tracking_number or "",
                    len(s.items),
                    s.id,  # hidden
                )
                for s in shipments
            ]

        self._ship_table.setRowCount(len(data))
        for row_idx, row in enumerate(data):
            for col_idx, val in enumerate(row[:-1]):
                item = QTableWidgetItem(str(val))
                self._ship_table.setItem(row_idx, col_idx, item)
            self._ship_table.item(row_idx, 0).setData(
                Qt.ItemDataRole.UserRole, row[-1]
            )

        self._lbl.setText(f"{len(data)} shipment(s) total")
        self._item_table.setRowCount(0)

    def _on_shipment_selected(self):
        row = self._ship_table.currentRow()
        if row < 0:
            return
        shipment_id = self._ship_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        with get_session() as session:
            svc = ShipmentService(session)
            items = svc.get_shipment_items(shipment_id)
            item_data = []
            for item in items:
                aliquot = item.aliquot
                sample  = aliquot.sample if aliquot else None
                participant = sample.participant if sample else None
                item_data.append((
                    aliquot.aliquot_id if aliquot else "",
                    sample.sample_id if sample else "",
                    sample.sample_type if sample else "",
                    participant.pid if participant else "",
                ))

        self._item_table.setRowCount(len(item_data))
        for row_idx, row in enumerate(item_data):
            for col_idx, val in enumerate(row):
                self._item_table.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))

"""
Sample Processing Tab — register samples and manage aliquots per participant visit.

Layout:
  ┌─ Participant selector (top) ──────────────────────────────┐
  ├─ Visit timeline (left) ──┬─ Sample + aliquot table (right)─┤
  │  Screening               │  Sample ID | Type | Aliquots    │
  │  Enrollment  ←selected   │  COH-26-1  | Serum | A1 A2 A3  │
  │  Follow-up               │  COH-26-2  | PBMC  | A1 A2     │
  └──────────────────────────┴─────────────────────────────────┘

Key concept — QTreeWidget for sample/aliquot hierarchy:
  Each sample is a top-level tree item.
  Each aliquot is a child item under its sample.
  Expanding/collapsing is free — the tree handles it.
  This matches how lab staff think: "sample → aliquots from it".
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QPushButton,
    QSplitter, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.services.participant_service import ParticipantService
from app.core.services.sample_service import SampleService
from app.core.services.study_service import StudyService


class SampleTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_participant_id: Optional[int] = None
        self._all_sample_data: list = []  # Cache all samples for filtering by visit
        self._current_visit_filter: Optional[str] = None  # Currently selected visit filter
        self._visits_dict: dict = {}  # Cache visits dict
        self._build_ui()
        self._load_studies()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Participant selector bar ───────────────────────────────────────
        sel_box = QGroupBox("Select participant")
        sel_layout = QHBoxLayout(sel_box)

        self._study_combo = QComboBox()
        self._study_combo.setMinimumWidth(120)
        self._study_combo.currentIndexChanged.connect(self._on_study_changed)

        self._participant_combo = QComboBox()
        self._participant_combo.setMinimumWidth(160)
        self._participant_combo.currentIndexChanged.connect(
            self._on_participant_changed
        )

        self._pid_label = QLabel("")
        self._pid_label.setStyleSheet("font-weight: 500; color: #2E75B6;")

        sel_layout.addWidget(QLabel("Study:"))
        sel_layout.addWidget(self._study_combo)
        sel_layout.addWidget(QLabel("  Participant:"))
        sel_layout.addWidget(self._participant_combo)
        sel_layout.addWidget(self._pid_label)
        sel_layout.addStretch()
        layout.addWidget(sel_box)

        # ── Main splitter: visit list left, sample tree right ─────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: visit list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.addWidget(QLabel("Visits:"))

        self._visit_list = QTreeWidget()
        self._visit_list.setHeaderHidden(True)
        self._visit_list.setMaximumWidth(180)
        self._visit_list.itemClicked.connect(self._on_visit_clicked)
        left_layout.addWidget(self._visit_list)

        # Right: sample + aliquot tree
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)

        # Toolbar
        btn_row = QHBoxLayout()
        self._btn_add_sample  = QPushButton("＋ Add Sample")
        self._btn_add_sample.setEnabled(False)
        self._btn_add_sample.clicked.connect(self._on_add_sample)

        self._btn_add_aliquots = QPushButton("＋ Add Aliquots")
        self._btn_add_aliquots.setEnabled(False)
        self._btn_add_aliquots.clicked.connect(self._on_add_aliquots)

        self._btn_edit = QPushButton("✎ Edit")
        self._btn_edit.setEnabled(False)
        self._btn_edit.clicked.connect(self._on_edit_sample)

        self._sample_count_lbl = QLabel("")
        self._sample_count_lbl.setStyleSheet("color: grey;")

        btn_row.addWidget(self._btn_add_sample)
        btn_row.addWidget(self._btn_add_aliquots)
        btn_row.addWidget(self._btn_edit)
        btn_row.addStretch()
        btn_row.addWidget(self._sample_count_lbl)
        right_layout.addLayout(btn_row)

        # Sample/aliquot tree
        self._sample_tree = QTreeWidget()
        self._sample_tree.setColumnCount(6)
        self._sample_tree.setHeaderLabels(
            ["ID", "Type", "Collection Date", "Vol (µL)",
             "Status", "Discrepancy"]
        )
        self._sample_tree.setAlternatingRowColors(True)
        self._sample_tree.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        header = self._sample_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._sample_tree.itemSelectionChanged.connect(
            self._on_tree_selection_changed
        )

        right_layout.addWidget(self._sample_tree)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([160, 800])
        layout.addWidget(splitter)

    # ── Data loading ───────────────────────────────────────────────────────

    def _load_studies(self):
        with get_session() as session:
            svc = StudyService(session)
            studies = [(s.id, s.project_id_short) for s in svc.get_all_active()]

        self._study_combo.blockSignals(True)
        self._study_combo.clear()
        self._study_combo.addItem("— Select study —", None)
        for sid, short in studies:
            self._study_combo.addItem(short, sid)
        self._study_combo.blockSignals(False)

    def _on_study_changed(self):
        study_id = self._study_combo.currentData()
        self._participant_combo.clear()
        self._participant_combo.addItem("— Select participant —", None)

        if not study_id:
            return

        with get_session() as session:
            svc = ParticipantService(session)
            participants, _ = svc.search({"study_id": study_id}, page_size=500)
            
            # Deduplicate by PID string (show unique participant IDs in dropdown)
            seen = set()
            unique_participants = []
            for p in participants:
                if p.pid not in seen:
                    seen.add(p.pid)
                    unique_participants.append((p.id, p.pid))

        for pid_db, pid_str in unique_participants:
            self._participant_combo.addItem(pid_str, pid_db)

    def _on_participant_changed(self):
        participant_id = self._participant_combo.currentData()
        self._current_participant_id = participant_id

        if not participant_id:
            self._pid_label.setText("")
            self._visit_list.clear()
            self._sample_tree.clear()
            self._btn_add_sample.setEnabled(False)
            return

        pid_text = self._participant_combo.currentText()
        self._pid_label.setText(f"  PID: {pid_text}")
        self._btn_add_sample.setEnabled(True)
        self._load_samples(participant_id)

    def _load_samples(self, participant_id: int):
        """Load all samples for the participant, grouped by visit code."""
        self._visit_list.clear()
        self._sample_tree.clear()
        self._current_visit_filter = None

        with get_session() as session:
            svc = SampleService(session)
            samples = svc.get_samples_for_participant(participant_id)

            visits: dict[str, list] = {}
            sample_data = []

            for s in samples:
                visit_key = s.visit_code or "No Visit"
                if visit_key not in visits:
                    visits[visit_key] = []

                aliquot_data = []
                for a in s.aliquots:
                    status = (
                        "Shipped"   if a.is_shipped  else
                        "Blocked"   if a.is_blocked  else
                        "Available" if a.is_available else
                        "Used"
                    )
                    aliquot_data.append((
                        a.aliquot_id, "", "",
                        str(a.volume_ul) if a.volume_ul else "",
                        status,
                        a.discrepancy_remark or "",
                        a.id,
                    ))

                visits[visit_key].append(s.sample_id)
                sample_data.append((
                    s.sample_id,
                    s.sample_type,
                    str(s.collection_date.date()) if s.collection_date else "",
                    "",
                    f"{len(s.aliquots)} aliquot(s)",
                    "",
                    s.id,
                    aliquot_data,
                    visit_key,  # visit_code stored at index 8 for filtering
                ))

            self._all_sample_data = sample_data.copy()
            self._visits_dict = visits.copy()

        # Populate visit list (insertion order preserved — dict is ordered in Python 3.7+)
        for visit_key in self._visits_dict:
            visit_item = QTreeWidgetItem(self._visit_list)
            visit_item.setText(0, visit_key)
            visit_item.setData(0, Qt.ItemDataRole.UserRole, visit_key)

            for sample_id in self._visits_dict[visit_key]:
                sample_item = QTreeWidgetItem(visit_item)
                sample_item.setText(0, f"  {sample_id}")
        self._visit_list.expandAll()

        self._render_sample_tree(self._all_sample_data)

    # ── Event handlers ─────────────────────────────────────────────────────

    def _render_sample_tree(self, sample_data: list):
        """Render samples in the tree. Can be ALL samples or filtered by visit code."""
        self._sample_tree.clear()

        for s_id, s_type, s_date, _, s_count, _, db_id, aliquots, visit_key in sample_data:
            sample_item = QTreeWidgetItem(self._sample_tree)
            sample_item.setText(0, s_id)
            sample_item.setText(1, s_type)
            sample_item.setText(2, s_date)
            sample_item.setText(4, s_count)
            sample_item.setData(0, Qt.ItemDataRole.UserRole, ("sample", db_id))

            for a_id, _, _, a_vol, a_status, a_disc, a_db_id in aliquots:
                aliquot_item = QTreeWidgetItem(sample_item)
                aliquot_item.setText(0, f"  ↳ {a_id}")
                aliquot_item.setText(3, a_vol)
                aliquot_item.setText(4, a_status)
                aliquot_item.setText(5, "⚠" if a_disc else "")
                aliquot_item.setData(
                    0, Qt.ItemDataRole.UserRole, ("aliquot", a_db_id)
                )
                # Colour aliquot rows by status
                color_map = {
                    "Shipped":   QColor("#CCE5FF"),
                    "Blocked":   QColor("#FFF3CC"),
                    "Available": QColor("#D4EDDA"),
                }
                if a_status in color_map:
                    for col in range(6):
                        aliquot_item.setBackground(col, color_map[a_status])

        self._sample_tree.expandAll()
        total = len(sample_data)
        self._sample_count_lbl.setText(
            f"{total} sample{'s' if total != 1 else ''}"
        )

    def _on_visit_clicked(self, item, col):
        """Filter sample tree when a visit code node is clicked in the left panel."""
        visit_key = item.data(0, Qt.ItemDataRole.UserRole)

        # Only filter on top-level visit nodes (child sample-ID items have no UserRole data)
        if visit_key is None or not isinstance(visit_key, str):
            return

        self._current_visit_filter = visit_key
        filtered_samples = [s for s in self._all_sample_data if s[8] == visit_key]
        self._render_sample_tree(filtered_samples)

    def _on_tree_selection_changed(self):
        selected = self._sample_tree.selectedItems()
        if not selected:
            self._btn_add_aliquots.setEnabled(False)
            self._btn_edit.setEnabled(False)
            return
        item_data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if item_data and item_data[0] == "sample":
            self._btn_add_aliquots.setEnabled(True)
            self._btn_edit.setEnabled(True)
        else:
            self._btn_add_aliquots.setEnabled(False)
            self._btn_edit.setEnabled(False)

    def _on_add_sample(self):
        if not self._current_participant_id:
            return
        from app.ui.dialogs.sample_dialog import SampleDialog
        dlg = SampleDialog(
            self, participant_id=self._current_participant_id,
            study_id=self._study_combo.currentData()
        )
        if dlg.exec():
            self._load_samples(self._current_participant_id)

    def _on_add_aliquots(self):
        selected = self._sample_tree.selectedItems()
        if not selected:
            return
        item_data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not item_data or item_data[0] != "sample":
            return
        sample_id = item_data[1]

        from app.ui.dialogs.add_aliquots_dialog import AddAliquotsDialog
        dlg = AddAliquotsDialog(self, sample_id=sample_id)
        if dlg.exec():
            self._load_samples(self._current_participant_id)

    def _on_edit_sample(self):
        selected = self._sample_tree.selectedItems()
        if not selected:
            return
        item_data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not item_data or item_data[0] != "sample":
            return
        sample_id = item_data[1]
        from app.ui.dialogs.sample_dialog import SampleDialog
        dlg = SampleDialog(self, sample_id=sample_id)
        if dlg.exec():
            self._load_samples(self._current_participant_id)
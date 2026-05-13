"""
Sample Processing Tab — register samples and manage aliquots per participant visit.

Layout:
  ┌─ Study selector (top) ─────────────────────────────────────────────┐
  ├─ PID search + checkable list ──┬─ Sample + aliquot tree (right) ───┤
  │  [Search PID…]                 │  Sample ID | Type | Date | …      │
  │  ☑ PID-001                     │  COH-26-1  | Serum | …           │
  │  ☐ PID-002                     │  COH-26-2  | PBMC  | …           │
  │  [Select All]  [Clear All]     │                                   │
  │  ── Visits ──                  │                                   │
  │  All Visits                    │                                   │
  │  1.0                           │                                   │
  └────────────────────────────────┴───────────────────────────────────┘
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.services.participant_service import ParticipantService
from app.core.services.sample_service import SampleService
from app.core.services.study_service import StudyService

_ALL_VISITS_KEY = "__all__"


class SampleTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_sample_data: list = []
        self._current_visit_filter: Optional[str] = None
        self._visits_dict: dict = {}
        self._all_participants: list[tuple[int, str]] = []  # (db_id, pid_str) sorted A→Z
        self._loading_participants = False  # guard: suppress itemChanged during bulk load
        self._build_ui()
        self._load_studies()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Study selector (compact single row) ───────────────────────────
        study_row = QHBoxLayout()
        study_row.setContentsMargins(0, 0, 0, 4)
        self._study_combo = QComboBox()
        self._study_combo.setMinimumWidth(160)
        self._study_combo.currentIndexChanged.connect(self._on_study_changed)
        study_row.addWidget(QLabel("Study:"))
        study_row.addWidget(self._study_combo)
        study_row.addStretch()
        layout.addLayout(study_row)

        # ── Main splitter: participant+visit left, sample tree right ───────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left panel ─────────────────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(180)
        left.setMaximumWidth(240)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)

        left_layout.addWidget(QLabel("Participants:"))

        self._pid_search = QLineEdit()
        self._pid_search.setPlaceholderText("Search PID…")
        self._pid_search.textChanged.connect(self._filter_participant_list)
        left_layout.addWidget(self._pid_search)

        self._participant_list = QListWidget()
        self._participant_list.setMaximumHeight(200)
        self._participant_list.itemChanged.connect(self._on_participant_selection_changed)
        left_layout.addWidget(self._participant_list)

        btn_pid_row = QHBoxLayout()
        self._btn_select_all = QPushButton("Select All")
        self._btn_select_all.setFixedHeight(22)
        self._btn_select_all.clicked.connect(self._on_select_all)
        self._btn_clear_all = QPushButton("Clear All")
        self._btn_clear_all.setFixedHeight(22)
        self._btn_clear_all.clicked.connect(self._on_clear_all)
        btn_pid_row.addWidget(self._btn_select_all)
        btn_pid_row.addWidget(self._btn_clear_all)
        left_layout.addLayout(btn_pid_row)

        left_layout.addWidget(QLabel("Visits:"))
        self._visit_list = QTreeWidget()
        self._visit_list.setHeaderHidden(True)
        self._visit_list.itemClicked.connect(self._on_visit_clicked)
        left_layout.addWidget(self._visit_list)

        # ── Right panel ────────────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)

        btn_row = QHBoxLayout()
        self._btn_add_sample = QPushButton("＋ Add Sample")
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

        self._sample_tree = QTreeWidget()
        self._sample_tree.setColumnCount(6)
        self._sample_tree.setHeaderLabels(
            ["ID", "Type", "Collection Date", "Vol (µL)", "Status", "Discrepancy"]
        )
        self._sample_tree.setAlternatingRowColors(True)
        self._sample_tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._sample_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._sample_tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        right_layout.addWidget(self._sample_tree)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([200, 800])
        layout.addWidget(splitter)

    # ── Study / participant loading ─────────────────────────────────────────

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
        self._loading_participants = True
        self._participant_list.blockSignals(True)
        self._participant_list.clear()
        self._participant_list.blockSignals(False)
        self._loading_participants = False

        self._all_participants = []
        self._pid_search.clear()
        self._visit_list.clear()
        self._sample_tree.clear()
        self._all_sample_data = []
        self._sample_count_lbl.setText("")
        self._btn_add_sample.setEnabled(False)

        if not study_id:
            return

        with get_session() as session:
            svc = ParticipantService(session)
            participants, _ = svc.search({"study_id": study_id}, page_size=500)
            seen: set[str] = set()
            unique: list[tuple[int, str]] = []
            for p in participants:
                if p.pid not in seen:
                    seen.add(p.pid)
                    unique.append((p.id, p.pid))

        self._all_participants = sorted(unique, key=lambda x: x[1])
        self._populate_participant_list(self._all_participants)

    def _populate_participant_list(self, participants: list[tuple[int, str]]):
        """Fill the list widget with sorted, unchecked participants."""
        self._loading_participants = True
        self._participant_list.blockSignals(True)
        self._participant_list.clear()
        for db_id, pid_str in participants:
            item = QListWidgetItem(pid_str)
            item.setData(Qt.ItemDataRole.UserRole, db_id)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._participant_list.addItem(item)
        self._participant_list.blockSignals(False)
        self._loading_participants = False

    def _filter_participant_list(self, text: str):
        """Show/hide list items by case-insensitive prefix match; order preserved."""
        needle = text.strip().lower()
        for i in range(self._participant_list.count()):
            item = self._participant_list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _on_select_all(self):
        self._loading_participants = True
        self._participant_list.blockSignals(True)
        for i in range(self._participant_list.count()):
            item = self._participant_list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)
        self._participant_list.blockSignals(False)
        self._loading_participants = False
        self._on_participant_selection_changed()

    def _on_clear_all(self):
        self._loading_participants = True
        self._participant_list.blockSignals(True)
        for i in range(self._participant_list.count()):
            self._participant_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self._participant_list.blockSignals(False)
        self._loading_participants = False
        self._on_participant_selection_changed()

    def _checked_participant_ids(self) -> list[int]:
        ids = []
        for i in range(self._participant_list.count()):
            item = self._participant_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def _on_participant_selection_changed(self, _item=None):
        if self._loading_participants:
            return
        checked_ids = self._checked_participant_ids()
        self._btn_add_sample.setEnabled(len(checked_ids) == 1)
        if checked_ids:
            self._load_samples(checked_ids)
        else:
            self._visit_list.clear()
            self._sample_tree.clear()
            self._all_sample_data = []
            self._sample_count_lbl.setText("")

    # ── Sample loading ─────────────────────────────────────────────────────

    def _load_samples(self, participant_ids: list[int]):
        """Load and merge samples for all checked participants."""
        self._visit_list.clear()
        self._sample_tree.clear()
        self._current_visit_filter = None

        all_sample_data: list = []
        visits: dict[str, list] = {}

        with get_session() as session:
            svc = SampleService(session)
            for pid_db in participant_ids:
                samples = svc.get_samples_for_participant(pid_db)
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
                    all_sample_data.append((
                        s.sample_id,
                        s.sample_type,
                        str(s.collection_date.date()) if s.collection_date else "",
                        "",
                        f"{len(s.aliquots)} aliquot(s)",
                        "",
                        s.id,
                        aliquot_data,
                        visit_key,
                    ))

        self._all_sample_data = all_sample_data
        self._visits_dict = visits

        # Visit list: "All Visits" at top, then each visit code
        all_item = QTreeWidgetItem(self._visit_list)
        all_item.setText(0, "All Visits")
        all_item.setData(0, Qt.ItemDataRole.UserRole, _ALL_VISITS_KEY)

        for visit_key in self._visits_dict:
            visit_item = QTreeWidgetItem(self._visit_list)
            visit_item.setText(0, visit_key)
            visit_item.setData(0, Qt.ItemDataRole.UserRole, visit_key)
            for sample_id in self._visits_dict[visit_key]:
                child = QTreeWidgetItem(visit_item)
                child.setText(0, f"  {sample_id}")

        self._visit_list.expandAll()
        self._render_sample_tree(self._all_sample_data)

    # ── Rendering ──────────────────────────────────────────────────────────

    def _render_sample_tree(self, sample_data: list):
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
                aliquot_item.setData(0, Qt.ItemDataRole.UserRole, ("aliquot", a_db_id))
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
        self._sample_count_lbl.setText(f"{total} sample{'s' if total != 1 else ''}")

    # ── Event handlers ─────────────────────────────────────────────────────

    def _on_visit_clicked(self, item, col):
        visit_key = item.data(0, Qt.ItemDataRole.UserRole)
        if visit_key is None:
            return
        if visit_key == _ALL_VISITS_KEY:
            self._current_visit_filter = None
            self._render_sample_tree(self._all_sample_data)
        else:
            self._current_visit_filter = visit_key
            filtered = [s for s in self._all_sample_data if s[8] == visit_key]
            self._render_sample_tree(filtered)

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
        checked_ids = self._checked_participant_ids()
        if len(checked_ids) != 1:
            return
        from app.ui.dialogs.sample_dialog import SampleDialog
        dlg = SampleDialog(
            self, participant_id=checked_ids[0],
            study_id=self._study_combo.currentData()
        )
        if dlg.exec():
            self._load_samples(checked_ids)

    def _on_add_aliquots(self):
        selected = self._sample_tree.selectedItems()
        if not selected:
            return
        item_data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not item_data or item_data[0] != "sample":
            return
        from app.ui.dialogs.add_aliquots_dialog import AddAliquotsDialog
        dlg = AddAliquotsDialog(self, sample_id=item_data[1])
        if dlg.exec():
            self._load_samples(self._checked_participant_ids())

    def _on_edit_sample(self):
        selected = self._sample_tree.selectedItems()
        if not selected:
            return
        item_data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not item_data or item_data[0] != "sample":
            return
        from app.ui.dialogs.sample_dialog import SampleDialog
        dlg = SampleDialog(self, sample_id=item_data[1])
        if dlg.exec():
            self._load_samples(self._checked_participant_ids())

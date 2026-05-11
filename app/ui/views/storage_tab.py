"""
Storage Tab — QSplitter with hierarchy tree on left and box grid on right.

Hierarchy: Freezer → Compartment → Rack → Drawer → Box → Position
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QSplitter,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from app.core.models.database import get_session
from app.core.services.storage_service import StorageService
from app.ui.widgets.box_grid_widget import BoxGridWidget, CellData
from app.utils.exception_handler import slot_safe


class StorageTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_box_id: Optional[int] = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left pane: hierarchy tree ──────────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar — one button per hierarchy level
        tree_toolbar = QHBoxLayout()
        btn_refresh         = QPushButton("🔄 Refresh")
        btn_new_freezer     = QPushButton("＋ Freezer")
        btn_new_compartment = QPushButton("＋ Compartment")
        btn_new_rack        = QPushButton("＋ Rack")
        btn_new_drawer      = QPushButton("＋ Drawer")
        btn_new_box         = QPushButton("＋ Box")
        btn_edit            = QPushButton("✏️ Edit")
        btn_delete          = QPushButton("🗑️ Delete")
        
        btn_refresh.clicked.connect(self.refresh)
        btn_new_freezer.clicked.connect(self._on_new_freezer)
        btn_new_compartment.clicked.connect(self._on_new_compartment)
        btn_new_rack.clicked.connect(self._on_new_rack)
        btn_new_drawer.clicked.connect(self._on_new_drawer)
        btn_new_box.clicked.connect(self._on_new_box)
        btn_edit.clicked.connect(self._on_edit_item)
        btn_delete.clicked.connect(self._on_delete_item)
        
        btn_edit.setEnabled(False)
        btn_delete.setEnabled(False)
        
        self._btn_edit = btn_edit
        self._btn_delete = btn_delete

        # Split buttons into three rows to keep the layout tidy
        toolbar_row1 = QHBoxLayout()
        toolbar_row1.addWidget(btn_refresh)
        toolbar_row1.addWidget(btn_new_freezer)
        toolbar_row1.addWidget(btn_new_compartment)
        toolbar_row2 = QHBoxLayout()
        toolbar_row2.addWidget(btn_new_rack)
        toolbar_row2.addWidget(btn_new_drawer)
        toolbar_row2.addWidget(btn_new_box)
        toolbar_row3 = QHBoxLayout()
        toolbar_row3.addWidget(btn_edit)
        toolbar_row3.addWidget(btn_delete)
        toolbar_row3.addStretch()

        left_layout.addLayout(toolbar_row1)
        left_layout.addLayout(toolbar_row2)
        left_layout.addLayout(toolbar_row3)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.currentItemChanged.connect(self._on_tree_selection)
        left_layout.addWidget(self._tree)

        left.setMinimumWidth(220)
        left.setMaximumWidth(340)

        # ── Right pane: box grid + info panel ─────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self._info_label = QLabel("Select a box from the tree to view its layout.")
        self._info_label.setStyleSheet("color: grey; padding: 4px;")
        right_layout.addWidget(self._info_label)

        # Legend
        legend = QHBoxLayout()
        for colour, label in [
            ("#4A90D9", "Occupied"),
            ("#E8A838", "Blocked"),
            ("#A0A0A0", "Shipped"),
            ("#2ECC71", "Selected"),
            ("#F8F9FA", "Empty"),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {colour}; font-size: 14px;")
            legend.addWidget(dot)
            legend.addWidget(QLabel(label))
            legend.addSpacing(8)
        legend.addStretch()
        right_layout.addLayout(legend)

        self._cell_info = QGroupBox("Selected cell")
        self._cell_info.setVisible(False)
        cell_info_layout = QVBoxLayout(self._cell_info)
        self._cell_detail = QLabel("")
        self._cell_detail.setWordWrap(True)
        cell_info_layout.addWidget(self._cell_detail)

        cell_btns = QHBoxLayout()
        self._btn_place  = QPushButton("Place Aliquot…")
        self._btn_move   = QPushButton("Move…")
        self._btn_remove = QPushButton("Remove")
        self._btn_place.clicked.connect(self._on_place_aliquot)
        self._btn_move.clicked.connect(self._on_move_aliquot)
        self._btn_remove.clicked.connect(self._on_remove_aliquot)
        cell_btns.addWidget(self._btn_place)
        cell_btns.addWidget(self._btn_move)
        cell_btns.addWidget(self._btn_remove)
        cell_btns.addStretch()
        cell_info_layout.addLayout(cell_btns)
        right_layout.addWidget(self._cell_info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._grid = BoxGridWidget()
        self._grid.cell_clicked.connect(self._on_cell_clicked)
        self._grid.cell_double_clicked.connect(self._on_cell_double_clicked)
        self._grid.aliquot_dropped.connect(self._on_aliquot_dropped)

        scroll.setWidget(self._grid)
        right_layout.addWidget(scroll)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 800])

        main_layout.addWidget(splitter)

    # ── Data loading ───────────────────────────────────────────────────────

    def refresh(self):
        """Reload the full hierarchy tree."""
        self._tree.clear()
        with get_session() as session:
            svc = StorageService(session)
            freezers = svc.get_all_freezers()
            # Collect data while session is open
            tree_data = []
            for f in freezers:
                comps = []
                for comp in f.compartments:
                    racks = []
                    for rack in comp.racks:
                        drawers = []
                        for drawer_box in rack.drawers:  # drawer_box is StorageDrawer
                            # Get all drawer-level StorageBox objects under this StorageDrawer
                            drawer_boxes = [
                                (db.id, db.name, 
                                 [(b.id, b.name, b.rows, b.cols,
                                   b.occupied_positions, b.total_positions)
                                  for b in db.child_boxes],  # Get nested boxes (Box-1, Box-2, etc.)
                                 )
                                for db in drawer_box.boxes  # db = drawer-level StorageBox (01, 02, etc.)
                            ]
                            for drawer_id, drawer_name, boxes in drawer_boxes:
                                drawers.append((drawer_id, drawer_name, boxes))
                        racks.append((rack.id, rack.name, drawers))
                    comps.append((comp.id, comp.name, racks))
                tree_data.append((f.id, f.name, f.temperature or "", comps))

        for freezer_id, f_name, temp, comps in tree_data:
            # Level 1: Freezer
            f_item = QTreeWidgetItem(self._tree)
            f_label = f"🗄  {f_name}"
            if temp:
                f_label += f"  ({temp})"
            f_item.setText(0, f_label)
            f_item.setData(0, Qt.ItemDataRole.UserRole, ("freezer", freezer_id))
            f_item.setExpanded(True)

            for comp_id, comp_name, racks in comps:
                # Level 2: Compartment
                comp_item = QTreeWidgetItem(f_item)
                comp_item.setText(0, f"🔲  {comp_name}")
                comp_item.setData(0, Qt.ItemDataRole.UserRole, ("compartment", comp_id))
                comp_item.setExpanded(True)

                for rack_id, rack_name, drawers in racks:
                    # Level 3: Rack
                    rack_item = QTreeWidgetItem(comp_item)
                    rack_item.setText(0, f"📐  {rack_name}")
                    rack_item.setData(0, Qt.ItemDataRole.UserRole, ("rack", rack_id))
                    rack_item.setExpanded(True)

                    for drawer_id, drawer_name, boxes in drawers:
                        # Level 4: Drawer
                        drawer_item = QTreeWidgetItem(rack_item)
                        drawer_item.setText(0, f"📂  {drawer_name}")
                        drawer_item.setData(0, Qt.ItemDataRole.UserRole, ("drawer", drawer_id))
                        drawer_item.setExpanded(True)

                        for box_id, box_name, rows, cols, occupied, total in boxes:
                            # Level 5: Box
                            box_item = QTreeWidgetItem(drawer_item)
                            box_item.setText(0,
                                f"📦  {box_name}  ({rows}×{cols})  [{occupied}/{total}]"
                            )
                            box_item.setData(0, Qt.ItemDataRole.UserRole, ("box", box_id))

        if self._current_box_id:
            self._load_box_grid(self._current_box_id)

    def _load_box_grid(self, box_id: int):
        self._current_box_id = box_id

        with get_session() as session:
            svc = StorageService(session)
            box = svc.get_box_grid(box_id)
            if not box:
                return

            self._info_label.setText(
                f"Box: {box.name}  |  {box.rows} × {box.cols}  |  "
                f"{box.occupied_positions} / {box.total_positions} occupied"
            )

            cells = []
            for pos in box.positions:
                loc = pos.aliquot_location
                aliquot = loc.aliquot if loc else None

                tooltip = None
                label   = None
                aliquot_id = None
                is_blocked = False
                is_shipped = False

                if aliquot:
                    aliquot_id = aliquot.id
                    is_blocked = aliquot.is_blocked
                    is_shipped = aliquot.is_shipped
                    sample = aliquot.sample
                    participant = sample.participant if sample else None

                    label = participant.pid if participant else aliquot.aliquot_id

                    lines = [
                        f"Aliquot: {aliquot.aliquot_id}",
                        f"Sample:  {sample.sample_id if sample else '—'}",
                        f"Type:    {sample.sample_type if sample else '—'}",
                        f"PID:     {participant.pid if participant else '—'}",
                        f"Volume:  {aliquot.volume_ul} µL" if aliquot.volume_ul else "",
                        "🔒 BLOCKED" if is_blocked else "",
                        "✈ SHIPPED" if is_shipped else "",
                    ]
                    tooltip = "\n".join(l for l in lines if l)

                cells.append(CellData(
                    row=pos.row,
                    col=pos.col,
                    position_id=pos.id,
                    aliquot_id=aliquot_id,
                    aliquot_label=label,
                    tooltip=tooltip,
                    is_blocked=is_blocked,
                    is_shipped=is_shipped,
                ))

            self._grid.set_grid_size(box.rows, box.cols)
            self._grid.load_cells(cells)
            self._cell_info.setVisible(False)

    # ── Helper: resolve parent ID from current tree selection ──────────────

    def _get_selected_node(self) -> tuple:
        """Return (kind, id) of currently selected tree node, or (None, None)."""
        current = self._tree.currentItem()
        if current:
            data = current.data(0, Qt.ItemDataRole.UserRole)
            if data:
                return data
        return (None, None)

    def _get_ancestor_id(self, kind: str) -> Optional[int]:
        """Walk up the tree from the current selection to find an ancestor of `kind`."""
        current = self._tree.currentItem()
        while current:
            data = current.data(0, Qt.ItemDataRole.UserRole)
            if data and data[0] == kind:
                return data[1]
            current = current.parent()
        return None

    # ── Event handlers ─────────────────────────────────────────────────────

    @slot_safe
    def _on_tree_selection(self, current, previous):
        if not current:
            self._btn_edit.setEnabled(False)
            self._btn_delete.setEnabled(False)
            return
        
        # Enable edit/delete buttons for any hierarchy item
        item_data = current.data(0, Qt.ItemDataRole.UserRole)
        if item_data:
            self._btn_edit.setEnabled(True)
            self._btn_delete.setEnabled(True)
        else:
            self._btn_edit.setEnabled(False)
            self._btn_delete.setEnabled(False)
        
        if item_data and item_data[0] == "box":
            self._load_box_grid(item_data[1])

    @slot_safe
    def _on_cell_clicked(self, row: int, col: int):
        if not self._current_box_id:
            return

        cells = self._grid._cells
        cell = cells.get((row, col))

        col_label = chr(ord('A') + col) if col < 26 else f"C{col}"
        position_label = f"Position {row + 1}{col_label}"

        if cell and cell.aliquot_id:
            self._cell_detail.setText(
                f"{position_label}\n{cell.tooltip or cell.aliquot_label}"
            )
            self._btn_place.setEnabled(False)
            self._btn_move.setEnabled(True)
            self._btn_remove.setEnabled(True)
        else:
            self._cell_detail.setText(f"{position_label} — Empty")
            self._btn_place.setEnabled(True)
            self._btn_move.setEnabled(False)
            self._btn_remove.setEnabled(False)

        self._cell_info.setVisible(True)

    @slot_safe
    def _on_cell_double_clicked(self, row: int, col: int):
        cell = self._grid._cells.get((row, col))
        if not cell or not cell.aliquot_id:
            from app.ui.dialogs.participant_dialog import ParticipantDialog
            dlg = ParticipantDialog(self)
            dlg.exec()

    @slot_safe
    def _on_aliquot_dropped(self, aliquot_id: int, target_row: int, target_col: int):
        from app.ui.dialogs.reason_dialog import ReasonDialog
        reason_dlg = ReasonDialog(self, "Reason for moving this sample:")
        if not reason_dlg.exec():
            return

        with get_session() as session:
            svc = StorageService(session)
            ok, msg = svc.move_aliquot(
                aliquot_id, self._current_box_id,
                target_row, target_col,
                reason=reason_dlg.reason,
            )

        if ok:
            self._load_box_grid(self._current_box_id)
        else:
            QMessageBox.warning(self, "Cannot Move", msg)

    # ── Creation handlers ──────────────────────────────────────────────────

    @slot_safe
    def _on_new_freezer(self):
        from app.ui.dialogs.freezer_dialog import FreezerDialog
        dlg = FreezerDialog(self)
        if dlg.exec():
            self.refresh()

    @slot_safe
    def _on_new_compartment(self):
        freezer_id = self._get_ancestor_id("freezer")
        from app.ui.dialogs.compartment_dialog import CompartmentDialog
        dlg = CompartmentDialog(self, freezer_id=freezer_id)
        if dlg.exec():
            self.refresh()

    @slot_safe
    def _on_new_rack(self):
        compartment_id = self._get_ancestor_id("compartment")
        from app.ui.dialogs.rack_dialog import RackDialog
        dlg = RackDialog(self, compartment_id=compartment_id)
        if dlg.exec():
            self.refresh()

    @slot_safe
    def _on_new_drawer(self):
        rack_id = self._get_ancestor_id("rack")
        from app.ui.dialogs.drawer_dialog import DrawerDialog
        dlg = DrawerDialog(self, rack_id=rack_id)
        if dlg.exec():
            self.refresh()

    @slot_safe
    def _on_new_box(self):
        drawer_id = self._get_ancestor_id("drawer")
        from app.ui.dialogs.box_dialog import BoxDialog
        dlg = BoxDialog(self, drawer_id=drawer_id)
        if dlg.exec():
            self.refresh()

    @slot_safe
    def _on_edit_item(self):
        """Edit the selected hierarchy item (Freezer, Compartment, Rack, Drawer, Box)."""
        current = self._tree.currentItem()
        if not current:
            return
        
        item_data = current.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return
        
        item_type, item_id = item_data
        
        # Route to appropriate dialog based on item type
        if item_type == "freezer":
            from app.ui.dialogs.freezer_dialog import FreezerDialog
            dlg = FreezerDialog(self, freezer_id=item_id)
            if dlg.exec():
                self.refresh()
        elif item_type == "compartment":
            from app.ui.dialogs.compartment_dialog import CompartmentDialog
            dlg = CompartmentDialog(self, compartment_id=item_id)
            if dlg.exec():
                self.refresh()
        elif item_type == "rack":
            from app.ui.dialogs.rack_dialog import RackDialog
            dlg = RackDialog(self, rack_id=item_id)
            if dlg.exec():
                self.refresh()
        elif item_type == "drawer":
            from app.ui.dialogs.drawer_dialog import DrawerDialog
            dlg = DrawerDialog(self, drawer_id=item_id)
            if dlg.exec():
                self.refresh()
        elif item_type == "box":
            from app.ui.dialogs.box_dialog import BoxDialog
            dlg = BoxDialog(self, box_id=item_id)
            if dlg.exec():
                self.refresh()

    @slot_safe
    def _on_delete_item(self):
        """Delete the selected hierarchy item."""
        current = self._tree.currentItem()
        if not current:
            return
        
        item_data = current.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return
        
        item_type, item_id = item_data
        item_name = current.text(0)
        
        # Confirm deletion
        reply = QMessageBox.warning(
            self,
            "Delete Confirmation",
            f"Are you sure you want to delete {item_type} '{item_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Delete from database
        try:
            with get_session() as session:
                svc = StorageService(session)
                
                if item_type == "freezer":
                    svc.delete_freezer(item_id)
                elif item_type == "compartment":
                    svc.delete_compartment(item_id)
                elif item_type == "rack":
                    svc.delete_rack(item_id)
                elif item_type == "drawer":
                    svc.delete_drawer(item_id)
                elif item_type == "box":
                    svc.delete_box(item_id)
                
                self.refresh()
                QMessageBox.information(self, "Success", f"{item_type.capitalize()} deleted successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete {item_type}: {str(e)}")

    @slot_safe
    def _on_place_aliquot(self):
        selected = self._grid.get_selected_cell()
        if not selected or not self._current_box_id:
            return

        row, col = selected
        col_label = chr(ord('A') + col) if col < 26 else f"C{col}"
        position_label = f"{row + 1}{col_label}"

        from app.ui.dialogs.place_aliquot_dialog import PlaceAliquotDialog
        dlg = PlaceAliquotDialog(self, position_label=position_label)
        if not dlg.exec():
            return

        with get_session() as session:
            svc = StorageService(session)
            ok, msg = svc.place_aliquot(
                aliquot_id=dlg.selected_aliquot_id,
                box_id=self._current_box_id,
                row=row,
                col=col,
            )

        if ok:
            self._load_box_grid(self._current_box_id)
        else:
            QMessageBox.warning(self, "Error", msg)

    @slot_safe
    def _on_move_aliquot(self):
        selected = self._grid.get_selected_cell()
        if not selected or not self._current_box_id:
            return

        row, col = selected
        cell = self._grid._cells.get((row, col))
        if not cell or not cell.aliquot_id:
            return

        from app.ui.dialogs.move_aliquot_dialog import MoveAliquotDialog
        from app.ui.dialogs.reason_dialog import ReasonDialog

        move_dlg = MoveAliquotDialog(
            self,
            box_id=self._current_box_id,
            source_row=row,
            source_col=col,
        )
        if not move_dlg.exec():
            return

        reason_dlg = ReasonDialog(self, "Reason for moving this sample:")
        if not reason_dlg.exec():
            return

        with get_session() as session:
            svc = StorageService(session)
            ok, msg = svc.move_aliquot(
                aliquot_id=cell.aliquot_id,
                target_box_id=self._current_box_id,
                target_row=move_dlg.target_row,
                target_col=move_dlg.target_col,
                reason=reason_dlg.reason,
            )

        if ok:
            self._load_box_grid(self._current_box_id)
        else:
            QMessageBox.warning(self, "Error", msg)

    @slot_safe
    def _on_remove_aliquot(self):
        selected = self._grid.get_selected_cell()
        if not selected:
            return
        cell = self._grid._cells.get(selected)
        if not cell or not cell.aliquot_id:
            return

        from app.ui.dialogs.reason_dialog import ReasonDialog
        dlg = ReasonDialog(self, "Reason for removing this aliquot from its position:")
        if not dlg.exec():
            return

        with get_session() as session:
            svc = StorageService(session)
            ok, msg = svc.remove_aliquot_from_position(cell.aliquot_id, dlg.reason)

        if ok:
            self._load_box_grid(self._current_box_id)
        else:
            QMessageBox.warning(self, "Error", msg)
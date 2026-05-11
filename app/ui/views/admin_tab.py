"""
Admin Tab — user management, audit trail, custom fields.

Layout: inner QTabWidget with three sub-tabs:
  [Users]  [Audit Trail]  [Custom Fields]

Key concept — nested tab widgets:
  A QTabWidget can be placed inside another QTabWidget.
  The outer tabs are the main app sections (Studies, Participants…).
  The inner tabs here are admin sub-sections.
  This avoids a very wide outer tab bar while keeping related
  admin features grouped together.
"""

from __future__ import annotations

import datetime as dt

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from PyQt6.QtCore import QDate

from app.config import AuditAction, Role
from app.core.models.database import get_session
from app.core.services.admin_service import AdminService
from app.core.services.auth_service import app_session


class AdminTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Check permission — only PI and Manager see this tab
        if not app_session.can("admin.users"):
            lbl = QLabel("You do not have permission to access the Admin panel.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: grey; font-size: 14px;")
            layout.addWidget(lbl)
            return

        inner_tabs = QTabWidget()
        inner_tabs.addTab(self._build_users_tab(),        "👥  Users")
        inner_tabs.addTab(self._build_audit_tab(),        "📜  Audit Trail")
        inner_tabs.addTab(self._build_custom_fields_tab(),"⚙️  Custom Fields")
        layout.addWidget(inner_tabs)

    # ══════════════════════════════════════════════════════════════════════
    # USERS SUB-TAB
    # ══════════════════════════════════════════════════════════════════════

    def _build_users_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        # Toolbar
        toolbar = QHBoxLayout()
        btn_refresh  = QPushButton("Refresh")
        btn_create   = QPushButton("＋ Create User")
        btn_approve  = QPushButton("✓ Approve")
        btn_edit     = QPushButton("✎ Edit Role")
        btn_reset_pw = QPushButton("Reset Password")
        btn_delete   = QPushButton("🗑 Delete")

        btn_approve.setEnabled(False)
        btn_edit.setEnabled(False)
        btn_reset_pw.setEnabled(False)
        btn_delete.setEnabled(False)

        self._btn_approve  = btn_approve
        self._btn_edit     = btn_edit
        self._btn_reset_pw = btn_reset_pw
        self._btn_delete   = btn_delete

        for btn in [btn_refresh, btn_create, btn_approve, btn_edit, btn_reset_pw, btn_delete]:
            toolbar.addWidget(btn)
        toolbar.addStretch()
        self._user_count_lbl = QLabel("")
        self._user_count_lbl.setStyleSheet("color: grey;")
        toolbar.addWidget(self._user_count_lbl)
        layout.addLayout(toolbar)

        # Users table
        self._user_table = QTableWidget()
        self._user_table.setColumnCount(7)
        self._user_table.setHorizontalHeaderLabels(
            ["Username", "Email", "Role", "Approved", "Active",
             "Last Login", "Created"]
        )
        self._user_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._user_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._user_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._user_table.setAlternatingRowColors(True)
        self._user_table.verticalHeader().setVisible(False)
        self._user_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._user_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._user_table.itemSelectionChanged.connect(
            self._on_user_selection_changed
        )
        layout.addWidget(self._user_table)

        # Connect buttons
        btn_refresh.clicked.connect(self._load_users)
        btn_create.clicked.connect(self._on_create_user)
        btn_approve.clicked.connect(self._on_approve_user)
        btn_edit.clicked.connect(self._on_edit_user)
        btn_reset_pw.clicked.connect(self._on_reset_password)
        btn_delete.clicked.connect(self._on_delete_user)

        self._load_users()
        return w

    def _load_users(self):
        with get_session() as session:
            svc = AdminService(session)
            users = svc.get_all_users()
            data = [
                (
                    u.username, u.email, u.role,
                    "Yes" if u.is_approved else "Pending",
                    "Yes" if u.is_active else "Disabled",
                    str(u.last_login.date()) if u.last_login else "Never",
                    str(u.created_at.date()) if u.created_at else "",
                    u.id,  # hidden
                )
                for u in users
            ]

        self._user_table.setRowCount(len(data))
        for row_idx, row in enumerate(data):
            for col_idx, val in enumerate(row[:-1]):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                # Colour-code approval status
                if col_idx == 3 and val == "Pending":
                    item.setForeground(
                        Qt.GlobalColor.darkYellow
                    )
                self._user_table.setItem(row_idx, col_idx, item)
            self._user_table.item(row_idx, 0).setData(
                Qt.ItemDataRole.UserRole, row[-1]
            )

        self._user_count_lbl.setText(f"{len(data)} user(s)")
        self._on_user_selection_changed()

    def _selected_user_id(self) -> int | None:
        row = self._user_table.currentRow()
        if row < 0:
            return None
        item = self._user_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_user_selection_changed(self):
        has = self._selected_user_id() is not None
        self._btn_approve.setEnabled(has)
        self._btn_edit.setEnabled(has)
        self._btn_reset_pw.setEnabled(has)
        self._btn_delete.setEnabled(has)

    def _on_create_user(self):
        from app.ui.dialogs.create_user_dialog import CreateUserDialog
        dlg = CreateUserDialog(self)
        if dlg.exec():
            self._load_users()
            
    def _on_approve_user(self):
        uid = self._selected_user_id()
        if not uid:
            return
        with get_session() as session:
            ok, msg = AdminService(session).approve_user(uid)
        if ok:
            self._load_users()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _on_edit_user(self):
        uid = self._selected_user_id()
        if not uid:
            return
        from app.ui.dialogs.edit_user_dialog import EditUserDialog
        dlg = EditUserDialog(self, user_id=uid)
        if dlg.exec():
            self._load_users()

    def _on_reset_password(self):
        uid = self._selected_user_id()
        if not uid:
            return
        from app.ui.dialogs.reset_password_dialog import ResetPasswordDialog
        dlg = ResetPasswordDialog(self, user_id=uid)
        if dlg.exec():
            QMessageBox.information(self, "Done", "Password reset successfully.")

    def _on_delete_user(self):
        uid = self._selected_user_id()
        if not uid:
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this user? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        with get_session() as session:
            ok, msg = AdminService(session).delete_user(uid)
        if ok:
            self._load_users()
        else:
            QMessageBox.warning(self, "Error", msg)

    # ══════════════════════════════════════════════════════════════════════
    # AUDIT TRAIL SUB-TAB
    # ══════════════════════════════════════════════════════════════════════

    def _build_audit_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        # Filter bar
        filter_box = QGroupBox("Filter")
        fbl = QHBoxLayout(filter_box)

        self._audit_action_filter = QComboBox()
        self._audit_action_filter.addItem("All actions", None)
        for action in [AuditAction.CREATE, AuditAction.UPDATE,
                       AuditAction.DELETE, AuditAction.LOGIN,
                       AuditAction.LOGOUT, AuditAction.SHIP,
                       AuditAction.BLOCK, AuditAction.UNBLOCK,
                       AuditAction.MOVE, AuditAction.EXPORT]:
            self._audit_action_filter.addItem(action, action)

        self._audit_entity_filter = QLineEdit()
        self._audit_entity_filter.setPlaceholderText("Entity type…")
        self._audit_entity_filter.setMaximumWidth(130)

        self._audit_date_from = QDateEdit()
        self._audit_date_from.setCalendarPopup(True)
        self._audit_date_from.setDate(QDate.currentDate().addMonths(-1))

        self._audit_date_to = QDateEdit()
        self._audit_date_to.setCalendarPopup(True)
        self._audit_date_to.setDate(QDate.currentDate())

        btn_audit_search = QPushButton("Search")
        btn_audit_search.clicked.connect(self._load_audit)

        fbl.addWidget(QLabel("Action:"))
        fbl.addWidget(self._audit_action_filter)
        fbl.addWidget(QLabel("  Entity:"))
        fbl.addWidget(self._audit_entity_filter)
        fbl.addWidget(QLabel("  From:"))
        fbl.addWidget(self._audit_date_from)
        fbl.addWidget(QLabel("To:"))
        fbl.addWidget(self._audit_date_to)
        fbl.addWidget(btn_audit_search)
        fbl.addStretch()
        layout.addWidget(filter_box)

        # Audit table
        self._audit_table = QTableWidget()
        self._audit_table.setColumnCount(6)
        self._audit_table.setHorizontalHeaderLabels(
            ["Timestamp", "User", "Action", "Entity", "ID", "Description"]
        )
        self._audit_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._audit_table.setAlternatingRowColors(True)
        self._audit_table.verticalHeader().setVisible(False)
        hdr = self._audit_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._audit_table)

        self._audit_count_lbl = QLabel("")
        self._audit_count_lbl.setStyleSheet("color: grey;")
        layout.addWidget(self._audit_count_lbl)

        self._load_audit()
        return w

    def _load_audit(self):
        action = self._audit_action_filter.currentData()
        entity = self._audit_entity_filter.text().strip() or None
        date_from = self._audit_date_from.date().toPyDate()
        date_to   = self._audit_date_to.date().toPyDate()

        with get_session() as session:
            svc = AdminService(session)
            logs, total = svc.get_audit_logs(
                action=action,
                entity_type=entity,
                date_from=date_from,
                date_to=date_to,
                page_size=500,
            )
            # Load usernames while session is open
            data = []
            for entry in logs:
                user = session.get(
                    __import__('app.core.models.models', fromlist=['User']).User,
                    entry.user_id
                ) if entry.user_id else None
                data.append((
                    str(entry.timestamp)[:19] if entry.timestamp else "",
                    user.username if user else "—",
                    entry.action,
                    entry.entity_type,
                    entry.entity_id or "",
                    entry.description or "",
                ))

        self._audit_table.setRowCount(len(data))
        action_colors = {
            AuditAction.DELETE:  "#FFCCCC",
            AuditAction.SHIP:    "#CCE5FF",
            AuditAction.BLOCK:   "#FFF3CC",
            AuditAction.UNBLOCK: "#D4EDDA",
        }
        for row_idx, row in enumerate(data):
            for col_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                self._audit_table.setItem(row_idx, col_idx, item)
            # Colour rows by action type
            action_val = data[row_idx][2]
            if action_val in action_colors:
                from PyQt6.QtGui import QColor
                color = QColor(action_colors[action_val])
                for col_idx in range(6):
                    self._audit_table.item(row_idx, col_idx).setBackground(color)

        self._audit_count_lbl.setText(
            f"Showing {len(data)} of {total} entries"
        )

    # ══════════════════════════════════════════════════════════════════════
    # CUSTOM FIELDS SUB-TAB
    # ══════════════════════════════════════════════════════════════════════

    def _build_custom_fields_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        # Add new field form
        add_box = QGroupBox("Add new custom field")
        add_form = QFormLayout(add_box)
        add_form.setSpacing(8)

        self._cf_name  = QLineEdit()
        self._cf_name.setPlaceholderText("Internal name (e.g. hiv_status)")
        self._cf_label = QLineEdit()
        self._cf_label.setPlaceholderText("Display label (e.g. HIV Status)")
        self._cf_type  = QComboBox()
        self._cf_type.addItems(["text", "number", "date", "select"])

        add_form.addRow("Field name:", self._cf_name)
        add_form.addRow("Label:",      self._cf_label)
        add_form.addRow("Type:",       self._cf_type)

        btn_add_cf = QPushButton("Add field")
        btn_add_cf.clicked.connect(self._on_add_custom_field)
        add_form.addRow("", btn_add_cf)

        self._cf_error = QLabel("")
        self._cf_error.setStyleSheet("color: red;")
        add_form.addRow("", self._cf_error)
        layout.addWidget(add_box)

        # Existing fields table
        layout.addWidget(QLabel("Existing custom fields:"))
        self._cf_table = QTableWidget()
        self._cf_table.setColumnCount(4)
        self._cf_table.setHorizontalHeaderLabels(
            ["Field name", "Label", "Type", "Active"]
        )
        self._cf_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._cf_table.setAlternatingRowColors(True)
        self._cf_table.verticalHeader().setVisible(False)
        self._cf_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._cf_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._cf_table.doubleClicked.connect(self._on_toggle_cf)
        layout.addWidget(self._cf_table)
        layout.addWidget(
            QLabel("Double-click a field to toggle active/disabled.")
        )

        self._load_custom_fields()
        return w

    def _load_custom_fields(self):
        with get_session() as session:
            svc = AdminService(session)
            fields = svc.get_custom_fields()
            data = [
                (f.field_name, f.field_label, f.field_type,
                 "Yes" if f.is_active else "No", f.id)
                for f in fields
            ]

        self._cf_table.setRowCount(len(data))
        for row_idx, row in enumerate(data):
            for col_idx, val in enumerate(row[:-1]):
                self._cf_table.setItem(
                    row_idx, col_idx, QTableWidgetItem(str(val))
                )
            self._cf_table.item(row_idx, 0).setData(
                Qt.ItemDataRole.UserRole, row[-1]
            )

    def _on_add_custom_field(self):
        name  = self._cf_name.text().strip()
        label = self._cf_label.text().strip()
        ftype = self._cf_type.currentText()

        with get_session() as session:
            svc = AdminService(session)
            ok, msg = svc.add_custom_field(name, label, ftype)

        if ok:
            self._cf_name.clear()
            self._cf_label.clear()
            self._cf_error.hide()
            self._load_custom_fields()
        else:
            self._cf_error.setText(msg)
            self._cf_error.show()

    def _on_toggle_cf(self, index):
        row = index.row()
        field_id = self._cf_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        with get_session() as session:
            ok, msg = AdminService(session).toggle_custom_field(field_id)
        if ok:
            self._load_custom_fields()

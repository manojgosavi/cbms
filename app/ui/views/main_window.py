"""
Main application window — Phase 6 final.
All tabs live: Dashboard, Studies, Participants, Samples (new!),
Storage, Search, Shipments, Catalogue, Admin.
Plus: Help menu, About dialog, keyboard shortcuts.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel, QMainWindow, QMessageBox, QStatusBar,
    QTabWidget, QWidget, QVBoxLayout,
)

from app.config import APP_TITLE, APP_VERSION, BACKUP_DIR
from app.core.services.auth_service import app_session


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE}  v{APP_VERSION}")
        self._build_menu()
        self._build_tabs()
        self._build_status_bar()
        self._check_overdue_blocks()

    # ── Menu ───────────────────────────────────────────────────────────────

    def _build_menu(self):
        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("New Study / Project…").triggered.connect(
            self._open_new_study_dialog)
        file_menu.addAction("Add New Participant…").triggered.connect(
            self._open_new_participant_dialog)
        file_menu.addAction("Add Sample Details…").triggered.connect(
            self._open_new_sample_dialog)
        file_menu.addSeparator()
        file_menu.addAction("Create New Freezer…").triggered.connect(
            self._open_freezer_dialog)
        file_menu.addAction("Create New Location Box…").triggered.connect(
            self._open_box_dialog)
        file_menu.addSeparator()
        file_menu.addAction("Close Software").triggered.connect(self.close)

        # Edit
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("Edit Participant Details…")
        edit_menu.addAction("Edit Sample Details…")
        edit_menu.addSeparator()
        edit_menu.addAction("Lock Freezer / Box…")
        edit_menu.addAction("Unlock Freezer / Box…")

        # View
        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Dashboard").triggered.connect(
            lambda: self.tabs.setCurrentWidget(self.dashboard_tab))
        view_menu.addAction("Storage").triggered.connect(
            lambda: self.tabs.setCurrentWidget(self.storage_tab))
        view_menu.addAction("Reports / Catalogue").triggered.connect(
            lambda: self.tabs.setCurrentWidget(self.reports_tab))

        # Search
        search_menu = menubar.addMenu("&Search")
        search_menu.addAction("Search…").triggered.connect(
            lambda: self.tabs.setCurrentWidget(self.search_tab))

        # Admin
        admin_menu = menubar.addMenu("&Admin")
        admin_menu.addAction("User Management…").triggered.connect(
            lambda: self.tabs.setCurrentWidget(self.admin_tab))
        admin_menu.addSeparator()
        admin_menu.addAction("Backup Now").triggered.connect(self._on_backup)

        # Help
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("Keyboard Shortcuts").triggered.connect(
            self._on_shortcuts)
        help_menu.addSeparator()
        help_menu.addAction("About CBMS…").triggered.connect(self._on_about)

    # ── Tabs ───────────────────────────────────────────────────────────────

    def _build_tabs(self):
        self.tabs = QTabWidget()

        from app.ui.views.study_tab       import StudyTab
        from app.ui.views.participant_tab import ParticipantTab
        from app.ui.views.sample_tab      import SampleTab
        from app.ui.views.storage_tab     import StorageTab
        from app.ui.views.search_tab      import SearchTab
        from app.ui.views.shipment_tab    import ShipmentTab
        from app.ui.views.reports_tab     import ReportsTab
        from app.ui.views.dashboard_tab   import DashboardTab
        from app.ui.views.admin_tab       import AdminTab

        self.dashboard_tab   = DashboardTab()
        self.study_tab       = StudyTab()
        self.participant_tab = ParticipantTab()
        self.sample_tab      = SampleTab()
        self.storage_tab     = StorageTab()
        self.search_tab      = SearchTab()
        self.shipment_tab    = ShipmentTab()
        self.reports_tab     = ReportsTab()
        self.admin_tab       = AdminTab()

        self.tabs.addTab(self.dashboard_tab,   "📊  Dashboard")
        self.tabs.addTab(self.study_tab,       "📋  Studies")
        self.tabs.addTab(self.participant_tab, "👤  Participants")
        self.tabs.addTab(self.sample_tab,      "🧪  Samples")
        self.tabs.addTab(self.storage_tab,     "🗄️  Storage")
        self.tabs.addTab(self.search_tab,      "🔍  Search")
        self.tabs.addTab(self.shipment_tab,    "📦  Shipments")
        self.tabs.addTab(self.reports_tab,     "📑  Catalogue")
        self.tabs.addTab(self.admin_tab,       "🔧  Admin")

        self.setCentralWidget(self.tabs)

    # ── Status bar ─────────────────────────────────────────────────────────

    def _get_last_backup_str(self) -> str:
        try:
            backups = sorted(BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime)
            if backups:
                import datetime
                ts = datetime.datetime.fromtimestamp(backups[-1].stat().st_mtime)
                return f"Last backup: {ts.strftime('%Y-%m-%d %H:%M')}"
        except Exception:
            pass
        return "No backup found"

    def _build_status_bar(self):
        bar = QStatusBar()
        user = app_session.current_user
        if user:
            bar.showMessage(
                f"Logged in as: {user.username}  |  Role: {user.role}  |  {APP_TITLE}"
            )
        self._backup_lbl = QLabel()
        self._backup_lbl.setStyleSheet("color: grey; margin-right: 8px;")
        bar.addPermanentWidget(self._backup_lbl)
        self.setStatusBar(bar)
        self._refresh_backup_label()

    def _refresh_backup_label(self):
        self._backup_lbl.setText(self._get_last_backup_str())

    # ── Startup checks ─────────────────────────────────────────────────────

    def _check_overdue_blocks(self):
        try:
            from app.core.models.database import get_session
            from app.core.services.blocking_service import BlockingService
            with get_session() as session:
                count = len(BlockingService(session).get_overdue_blocks())
            if count > 0:
                reply = QMessageBox.question(
                    self, "Overdue blocks",
                    f"{count} aliquot block(s) have passed their unblock date.\n"
                    "Review and release them now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.tabs.setCurrentWidget(self.search_tab)
                    self.search_tab._f_blocked.setChecked(True)
                    self.search_tab._on_search()
        except Exception:
            pass

    # ── Dialog launchers ───────────────────────────────────────────────────

    def _open_new_study_dialog(self):
        from app.ui.dialogs.study_dialog import StudyDialog
        if StudyDialog(self).exec():
            self.study_tab.refresh()

    def _open_new_participant_dialog(self):
        from app.ui.dialogs.participant_dialog import ParticipantDialog
        if ParticipantDialog(self).exec():
            self.participant_tab.refresh()

    def _open_new_sample_dialog(self):
        self.tabs.setCurrentWidget(self.sample_tab)

    def _open_freezer_dialog(self):
        from app.ui.dialogs.freezer_dialog import FreezerDialog
        if FreezerDialog(self).exec():
            self.storage_tab.refresh()

    def _open_box_dialog(self):
        from app.ui.dialogs.box_dialog import BoxDialog
        if BoxDialog(self).exec():
            self.storage_tab.refresh()

    def _on_backup(self):
        from app.utils.backup import run_backup
        ok, path = run_backup()
        if ok:
            self._refresh_backup_label()
            QMessageBox.information(self, "Backup complete",
                                    f"Database backed up to:\n{path}")
        else:
            QMessageBox.warning(self, "Backup failed", path)

    def _on_about(self):
        from app.ui.dialogs.about_dialog import AboutDialog
        AboutDialog(self).exec()

    def _on_shortcuts(self):
        QMessageBox.information(self, "Keyboard shortcuts",
            "Ctrl+1  →  Dashboard\n"
            "Ctrl+2  →  Studies\n"
            "Ctrl+3  →  Participants\n"
            "Ctrl+4  →  Samples\n"
            "Ctrl+5  →  Storage\n"
            "Ctrl+F  →  Search\n"
            "Ctrl+6  →  Shipments\n"
            "Ctrl+7  →  Catalogue\n"
            "Ctrl+8  →  Admin\n"
            "Ctrl+N  →  New participant\n"
            "Ctrl+Shift+N  →  New study\n"
            "Ctrl+B  →  Backup now"
        )

    # ── Cross-tab navigation ───────────────────────────────────────────────

    def show_aliquot_location(self, aliquot_db_id: int):
        self.tabs.setCurrentWidget(self.storage_tab)
        self.storage_tab.navigate_to_aliquot(aliquot_db_id)

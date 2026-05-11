"""
CBMS — entry point.
Run with:  python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QKeySequence

from app.config import APP_TITLE, APP_VERSION, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from app.core.models.database import init_db, get_session
from app.core.services.auth_service import seed_admin
from app.utils.exception_handler import install_global_exception_hook


def _needs_setup() -> bool:
    try:
        from app.core.models.models import Study
        with get_session() as session:
            return session.query(Study).count() == 0
    except Exception:
        return False


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")

    # Install global exception hook FIRST — before any UI is shown.
    # This converts crash-on-unhandled-slot-exception into a QMessageBox.
    install_global_exception_hook()

    # Init DB and seed admin (data folder is created automatically by config)
    init_db()
    with get_session() as session:
        seed_admin(session)

    # Login
    from app.ui.views.login_view import LoginDialog
    login_dlg = LoginDialog()
    if login_dlg.exec() != login_dlg.DialogCode.Accepted:
        sys.exit(0)

    # First-run wizard
    if _needs_setup():
        from app.ui.views.setup_wizard import SetupWizard
        wizard = SetupWizard()
        if wizard.exec() != wizard.DialogCode.Accepted:
            sys.exit(0)

    # Main window
    from app.ui.views.main_window import MainWindow
    window = MainWindow()
    window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

    # Keyboard shortcuts
    from PyQt6.QtGui import QShortcut

    def _tab(n):
        return lambda: window.tabs.setCurrentIndex(n)

    shortcuts = [
        (QKeySequence("Ctrl+1"),       _tab(0)),
        (QKeySequence("Ctrl+2"),       _tab(1)),
        (QKeySequence("Ctrl+3"),       _tab(2)),
        (QKeySequence("Ctrl+4"),       _tab(3)),
        (QKeySequence("Ctrl+5"),       _tab(4)),
        (QKeySequence("Ctrl+F"),       _tab(5)),
        (QKeySequence("Ctrl+6"),       _tab(6)),
        (QKeySequence("Ctrl+7"),       _tab(7)),
        (QKeySequence("Ctrl+8"),       _tab(8)),
        (QKeySequence("Ctrl+B"),       lambda: window._on_backup()),
        (QKeySequence("Ctrl+N"),       lambda: window._open_new_participant_dialog()),
        (QKeySequence("Ctrl+Shift+N"), lambda: window._open_new_study_dialog()),
    ]
    for key, action in shortcuts:
        sc = QShortcut(key, window)
        sc.activated.connect(action)

    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

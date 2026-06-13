"""
Excel bulk import dialog.

Imports participant/sample/aliquot data from Excel with 21 columns:
  PID | Age | Gender | Population | Disease | Visit Code | Visit Time |
  Date Collected | Site Name | Visit Name | Sample Type | Cohort Name |
  Aliquot ID | Freezer / Tank | Container | Slot Position | Shelf | Rack |
  Position | Discrepancy Remark | Discrepancy For

PyQt6 concepts:
  - QFileDialog.getOpenFileName() : native OS file picker
  - QTableWidget                  : displays validation errors row by row
  - QThread / pyqtSignal          : runs import in background to keep UI responsive
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QScrollArea, QWidget,
)
from PyQt6.QtGui import QFont

from app.core.models.database import get_session
from app.core.services.excel_import_service import ExcelImportService
from app.core.services.study_service import StudyService


class _ImportWorker(QThread):
    """Background thread that runs the actual DB import and emits progress."""

    progress = pyqtSignal(int, int)   # (processed, total)
    finished = pyqtSignal(int, str)   # (count_created, error_msg_or_empty)

    def __init__(self, rows, study_id: int, parent=None):
        super().__init__(parent)
        self._rows = rows
        self._study_id = study_id

    def run(self):
        with get_session() as session:
            service = ExcelImportService(session)
            count, error = service.import_rows(
                self._rows,
                self._study_id,
                progress_callback=lambda done, total: self.progress.emit(done, total),
            )
        self.finished.emit(count, error or "")


class ExcelImportDialog(QDialog):
    """Dialog for bulk importing participant/sample/aliquot data from Excel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Import from Excel")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self._worker = None
        self._validated_rows = None
        self._build_ui()
        self._load_studies()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Bulk Import Participants & Samples from Excel")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        # Instructions
        info = QLabel(
            "Download template or prepare Excel file with 21 columns (see header specification below).\n"
            "Row 1 = headers. All rows are validated before import.\n"
            "<b>Required columns:</b> PID  |  <b>Optional:</b> Age, Gender, Population, Disease, Visit Code, "
            "Visit Time, Date Collected, Site Name, Visit Name, Sample Type, Cohort Name, "
            "Aliquot ID, Freezer / Tank, Container, Slot Position, Shelf, Rack, Position, "
            "Discrepancy Remark, Discrepancy For"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Study selector
        study_row = QHBoxLayout()
        study_row.addWidget(QLabel("Study:"))
        self._study_combo = QComboBox()
        study_row.addWidget(self._study_combo)
        study_row.addStretch()
        layout.addLayout(study_row)

        # File picker
        file_row = QHBoxLayout()
        self._file_path = QLineEdit()
        self._file_path.setPlaceholderText("No file selected…")
        self._file_path.setReadOnly(True)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._on_browse)
        file_row.addWidget(self._file_path)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        # Status label
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Progress bar (hidden until import starts)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        # Error table (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)

        self._error_table = QTableWidget(0, 2)
        self._error_table.setHorizontalHeaderLabels(["Row", "Error"])
        self._error_table.setColumnWidth(0, 50)
        self._error_table.setColumnWidth(1, 600)
        self._error_table.hide()
        self._error_table.setMaximumHeight(200)

        scroll_layout.addWidget(self._error_table)
        scroll_area.setWidget(scroll_container)
        layout.addWidget(scroll_area)

        # Buttons
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._import_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._import_btn.setText("Import")
        self._import_btn.clicked.connect(self._on_import)
        self._buttons.rejected.connect(self._on_cancel)
        layout.addWidget(self._buttons)

    def _load_studies(self):
        """Load active studies into combo box."""
        with get_session() as session:
            service = StudyService(session)
            for s in service.get_all_active():
                self._study_combo.addItem(s.project_id_short, s.id)

    def _on_browse(self):
        """Open file browser to select Excel file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "",
            "Excel Files (*.xlsx *.xls)"
        )
        if path:
            self._file_path.setText(path)
            self._validated_rows = None  # reset cached validation on new file
            self._error_table.hide()
            self._status.setText("")

    def _on_cancel(self):
        """Cancel or stop running import."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
            self._status.setText("Import cancelled.")
            self._set_ui_busy(False)
        else:
            self.reject()

    def _on_import(self):
        """Validate and import rows from Excel."""
        path = self._file_path.text().strip()
        if not path:
            self._status.setText("Please select a file.")
            self._error_table.hide()
            return

        study_id = self._study_combo.currentData()
        if not study_id:
            self._status.setText("Please select a study.")
            self._error_table.hide()
            return

        # ── Validate (runs on UI thread; fast since it's pure Python + one file read) ──
        self._status.setText("Loading and validating Excel file…")
        self._error_table.hide()
        self._progress_bar.hide()

        with get_session() as session:
            excel_service = ExcelImportService(session)
            rows, header_errors = excel_service.load_and_validate_excel(path)

        if header_errors:
            self._status.setText(f"File Error:\n{chr(10).join(header_errors)}")
            return

        rows_with_errors = [r for r in rows if r.errors]
        if rows_with_errors:
            self._status.setText(
                f"Validation failed: {len(rows_with_errors)} row(s) have errors. "
                "Fix the Excel file and try again."
            )
            self._error_table.setRowCount(len(rows_with_errors))
            for i, row in enumerate(rows_with_errors):
                self._error_table.setItem(i, 0, QTableWidgetItem(str(row.row_num)))
                self._error_table.setItem(i, 1, QTableWidgetItem("; ".join(row.errors)))
            self._error_table.show()
            return

        # ── Confirm ────────────────────────────────────────────────────────────
        row_count = len(rows)
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Ready to import {row_count:,} row(s). Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._status.setText("Import cancelled.")
            return

        # ── Run import in background thread ────────────────────────────────────
        self._set_ui_busy(True)
        self._progress_bar.setRange(0, row_count)
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat(f"0 / {row_count:,} rows")
        self._progress_bar.show()
        self._status.setText(f"Importing {row_count:,} rows…")

        self._worker = _ImportWorker(rows, study_id, parent=self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_import_finished)
        self._worker.start()

    def _on_progress(self, done: int, total: int):
        """Update progress bar from worker thread signal."""
        self._progress_bar.setValue(done)
        self._progress_bar.setFormat(f"{done:,} / {total:,} rows")

    def _on_import_finished(self, count: int, error_msg: str):
        """Handle worker completion."""
        self._set_ui_busy(False)
        self._progress_bar.hide()

        if error_msg:
            self._status.setText(f"Import Failed:\n{error_msg}")
        else:
            self._status.setText(f"Import successful! {count:,} row(s) imported.")
            self._error_table.hide()
            self.accept()

    def _set_ui_busy(self, busy: bool):
        """Enable/disable controls while import is running."""
        self._import_btn.setEnabled(not busy)
        self._study_combo.setEnabled(not busy)
        self._file_path.setEnabled(not busy)
        cancel_btn = self._buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Stop" if busy else "Cancel")

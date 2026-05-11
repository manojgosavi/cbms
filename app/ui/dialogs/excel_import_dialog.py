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
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QScrollArea, QWidget,
)
from PyQt6.QtGui import QFont

from app.core.models.database import get_session
from app.core.services.excel_import_service import ExcelImportService
from app.core.services.study_service import StudyService


class ExcelImportDialog(QDialog):
    """Dialog for bulk importing participant/sample/aliquot data from Excel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Import from Excel")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.excel_service = None
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

        # Validation / result display
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

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
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        import_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        import_btn.setText("Import")
        import_btn.clicked.connect(self._on_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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

    def _on_import(self):
        """Validate and import rows from Excel."""
        path = self._file_path.text().strip()
        if not path:
            self._status.setText("⚠ Please select a file.")
            self._error_table.hide()
            return

        study_id = self._study_combo.currentData()
        if not study_id:
            self._status.setText("⚠ Please select a study.")
            self._error_table.hide()
            return

        self._status.setText("Loading and validating Excel file…")
        self._error_table.hide()

        # Load and validate
        with get_session() as session:
            excel_service = ExcelImportService(session)
            rows, header_errors = excel_service.load_and_validate_excel(path)

        # Check for header errors
        if header_errors:
            error_msg = "\n".join(header_errors)
            self._status.setText(f"❌ File Error:\n{error_msg}")
            self._error_table.hide()
            return

        # Check for validation errors
        rows_with_errors = [r for r in rows if r.errors]

        if rows_with_errors:
            error_count = len(rows_with_errors)
            self._status.setText(
                f"⚠ Validation failed: {error_count} row(s) have errors. "
                f"Fix the Excel file and try again."
            )
            
            # Show error table
            self._error_table.setRowCount(len(rows_with_errors))
            for i, row in enumerate(rows_with_errors):
                row_item = QTableWidgetItem(str(row.row_num))
                error_msg = "; ".join(row.errors)
                error_item = QTableWidgetItem(error_msg)
                self._error_table.setItem(i, 0, row_item)
                self._error_table.setItem(i, 1, error_item)
            self._error_table.show()
            return

        # All rows valid - ask for confirmation
        row_count = len(rows)
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Ready to import {row_count} row(s). Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            self._status.setText("Import cancelled.")
            return

        # Import
        self._status.setText("Importing data…")
        with get_session() as session:
            excel_service = ExcelImportService(session)
            created_count, error_msg = excel_service.import_rows(rows, study_id)

        if error_msg:
            self._status.setText(f"❌ Import Failed:\n{error_msg}")
            self._error_table.hide()
            return

        self._status.setText(f"✓ Import successful! {created_count} row(s) imported.")
        self._error_table.hide()
        self.accept()


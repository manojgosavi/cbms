"""
Excel bulk import service.

Handles parsing, validating, and importing participant/sample/aliquot data
from Excel files with structure:
  PID | Age | Gender | Population | Disease | Visit Code | Visit Time |
  Date Collected | Site Name | Visit Name | Sample Type | Cohort Name |
  Aliquot ID | Freezer / Tank | Container | Slot Position | Shelf | Rack |
  Position | Discrepancy Remark | Discrepancy For
"""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional
from dateutil.parser import parse, ParserError
import openpyxl

from sqlalchemy.orm import Session

from app.config import Gender, Population, Disease, Site, VisitName, SampleType, CohortName
from app.core.models.models import (
    Participant, Sample, SampleAliquot, Study, Freezer, Compartment,
    StorageRack, StorageDrawer, StorageBox, BoxPosition, AliquotLocation
)
from app.core.services.id_generator import generate_sample_id, generate_aliquot_id
from app.core.repositories.storage_repository import FreezerRepository

# Valid hierarchy values for upright freezers (Freezer 1 & 2)
VALID_SHELVES  = ["I", "II", "III", "IV"]
VALID_RACKS    = ["A", "B", "C", "D", "E", "F"]
VALID_DRAWERS  = ["01", "02", "03", "04", "05"]

# Cylindrical freezers (Freezer 3 & 4): racks 01-13, no shelf or drawer
VALID_CYLINDRICAL_RACKS           = [f"{i:02d}" for i in range(1, 14)]
CYLINDRICAL_SENTINEL_COMPARTMENT  = "CYLINDRICAL"
CYLINDRICAL_SENTINEL_DRAWER       = "01"


@dataclass
class ImportRow:
    """Parsed Excel row (0-indexed in file, but row_num is 1-indexed for display)."""
    row_num: int  # Display row number (2, 3, 4, ...)
    pid: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    population: Optional[str]
    disease: Optional[str]
    visit_code: Optional[str]
    visit_time: Optional[str]
    date_collected: Optional[str]
    site_name: Optional[str]
    visit_name: Optional[str]
    sample_type: Optional[str]
    cohort_name: Optional[str]
    aliquot_id: Optional[str]
    freezer_name: Optional[str]
    container_name: Optional[str]
    slot_position: Optional[int]  # Sequential position 1-100 in box grid
    shelf_name: Optional[str]  # I, II, III, IV
    rack_drawer_combined: Optional[str]  # Format: "D-02" (Rack-Drawer)
    position: Optional[str]  # Will be converted from slot_position to letter+number (e.g., A1)
    discrepancy_remark: Optional[str]
    discrepancy_for: Optional[str]
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ExcelImportService:
    """Service for bulk importing participant/sample/aliquot data from Excel."""

    EXPECTED_HEADERS = [
        'PID', 'Age', 'Gender', 'Population', 'Disease', 'Visit Code', 'Visit Time',
        'Date Collected', 'Site Name', 'Visit Name', 'Sample Type', 'Cohort Name',
        'Aliquot ID', 'Freezer / Tank', 'Container', 'Slot Position', 'Shelf', 'Rack',
        'Position', 'Discrepancy Remark', 'Discrepancy For'
    ]

    def __init__(self, session: Session):
        self.session = session

    def load_and_validate_excel(self, filepath: str) -> tuple[list[ImportRow], list[str]]:
        """
        Load Excel file, parse rows, and validate each row.

        Returns:
          (validated_rows, header_errors)

        If header_errors is non-empty, validated_rows will be empty.
        Each row in validated_rows has an 'errors' list; if non-empty, row failed validation.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            return [], [f"File not found: {filepath}"]

        try:
            wb = openpyxl.load_workbook(filepath, data_only=True)
            ws = wb.active
        except Exception as e:
            return [], [f"Failed to open Excel file: {e}"]

        # Validate headers
        actual_headers = [cell for cell in ws[1]]
        actual_headers = [h.value if h else None for h in actual_headers[:21]]

        if actual_headers != self.EXPECTED_HEADERS:
            return [], [
                f"Excel header mismatch.\n"
                f"Expected: {self.EXPECTED_HEADERS}\n"
                f"Got: {actual_headers}"
            ]

        # Parse rows
        rows = []
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            # Ensure row has at least 21 columns
            row_data = list(row[:21]) + [None] * (21 - len(row[:21]))

            import_row = ImportRow(
                row_num=row_idx,
                pid=row_data[0],
                age=row_data[1],
                gender=row_data[2],
                population=row_data[3],
                disease=row_data[4],
                visit_code=row_data[5],
                visit_time=row_data[6],
                date_collected=row_data[7],
                site_name=row_data[8],
                visit_name=row_data[9],
                sample_type=row_data[10],
                cohort_name=row_data[11],
                aliquot_id=row_data[12],
                freezer_name=row_data[13],
                container_name=row_data[14],
                slot_position=row_data[15],
                shelf_name=row_data[16],
                rack_drawer_combined=row_data[17],
                position=row_data[18],  # Will be populated during validation
                discrepancy_remark=row_data[19],
                discrepancy_for=row_data[20],
            )
            rows.append(import_row)

        # Validate each row
        for row in rows:
            self._validate_row(row)

        return rows, []

    def _validate_row(self, row: ImportRow) -> None:
        """Validate a single row and populate row.errors."""
        errors = []

        # PID (required)
        if not row.pid:
            errors.append("PID is required")
        elif not isinstance(row.pid, str):
            try:
                row.pid = str(row.pid).strip()
            except:
                errors.append("PID must be a string")

        # Age (optional, must be int if provided)
        if row.age is not None:
            try:
                row.age = int(row.age)
            except (ValueError, TypeError):
                errors.append(f"Age must be an integer, got '{row.age}'")

        # Gender (enum validation)
        if row.gender:
            row.gender = str(row.gender).strip()
            valid_genders = [e.value for e in Gender]
            if row.gender not in valid_genders:
                errors.append(f"Invalid Gender '{row.gender}'. Allowed: {valid_genders}")

        # Population (enum validation)
        if row.population:
            row.population = str(row.population).strip()
            valid_pops = [e.value for e in Population]
            if row.population not in valid_pops:
                errors.append(f"Invalid Population '{row.population}'. Allowed: {valid_pops}")

        # Disease (enum validation)
        if row.disease:
            row.disease = str(row.disease).strip()
            valid_diseases = [e.value for e in Disease]
            if row.disease not in valid_diseases:
                errors.append(f"Invalid Disease '{row.disease}'. Allowed: {valid_diseases}")

        # Site Name (enum validation)
        if row.site_name:
            row.site_name = str(row.site_name).strip()
            valid_sites = [e.value for e in Site]
            if row.site_name not in valid_sites:
                errors.append(f"Invalid Site '{row.site_name}'. Allowed: {valid_sites}")

        # Visit Name (enum validation)
        if row.visit_name:
            row.visit_name = str(row.visit_name).strip()
            valid_visits = [e.value for e in VisitName]
            if row.visit_name not in valid_visits:
                errors.append(f"Invalid Visit Name '{row.visit_name}'. Allowed: {valid_visits}")

        # Sample Type (enum validation)
        if row.sample_type:
            row.sample_type = str(row.sample_type).strip()
            valid_samples = [e.value for e in SampleType]
            if row.sample_type not in valid_samples:
                errors.append(f"Invalid Sample Type '{row.sample_type}'. Allowed: {valid_samples}")

        # Cohort Name (enum validation)
        if row.cohort_name:
            row.cohort_name = str(row.cohort_name).strip()
            valid_cohorts = [e.value for e in CohortName]
            if row.cohort_name not in valid_cohorts:
                errors.append(f"Invalid Cohort Name '{row.cohort_name}'. Allowed: {valid_cohorts}")

        # Visit Code (optional, string)
        if row.visit_code:
            row.visit_code = str(row.visit_code).strip()

        # Visit Time (optional, HH:MM format)
        if row.visit_time:
            row.visit_time = str(row.visit_time).strip()
            if not self._is_valid_time(row.visit_time):
                errors.append(f"Visit Time must be HH:MM format, got '{row.visit_time}'")

        # Date Collected (optional, YYYY-MM-DD format)
        if row.date_collected:
            row.date_collected = str(row.date_collected).strip()
            if not self._is_valid_date(row.date_collected):
                errors.append(f"Date Collected must be YYYY-MM-DD format, got '{row.date_collected}'")

        # Storage hierarchy validation
        has_storage = any([row.freezer_name, row.container_name, row.shelf_name,
                           row.rack_drawer_combined, row.slot_position])

        if has_storage:
            # Core fields required for both upright and cylindrical paths
            missing = []
            if not row.freezer_name:        missing.append("Freezer / Tank")
            if not row.container_name:      missing.append("Container")
            if not row.rack_drawer_combined: missing.append("Rack")
            if not row.slot_position:       missing.append("Slot Position")
            if missing:
                errors.append(f"Storage incomplete. Missing: {', '.join(missing)}")
            else:
                is_cylindrical = not row.shelf_name  # no shelf → cylindrical freezer

                if is_cylindrical:
                    # Cylindrical path: rack is a plain number 01-13
                    rack_str = str(row.rack_drawer_combined).strip()
                    try:
                        rack_str = f"{int(rack_str):02d}"
                        if rack_str not in VALID_CYLINDRICAL_RACKS:
                            errors.append(
                                f"Cylindrical rack must be 01–13, got '{rack_str}'"
                            )
                        else:
                            row.rack_drawer_combined = rack_str
                    except (ValueError, TypeError):
                        errors.append(
                            f"Cylindrical rack must be a number 1–13, got '{rack_str}'"
                        )
                else:
                    # Upright path: validate shelf and rack-drawer format
                    row.shelf_name = str(row.shelf_name).strip()
                    if row.shelf_name not in VALID_SHELVES:
                        errors.append(
                            f"Invalid Shelf '{row.shelf_name}'. Allowed: {VALID_SHELVES}"
                        )

                    rack_drawer = str(row.rack_drawer_combined).strip()
                    parts = rack_drawer.split('-')
                    if len(parts) != 2:
                        errors.append(
                            f"Rack format invalid '{rack_drawer}'. Expected: 'A-01'"
                        )
                    else:
                        rack_name   = parts[0].upper()
                        drawer_name = parts[1].strip()
                        if rack_name not in VALID_RACKS:
                            errors.append(
                                f"Invalid Rack '{rack_name}'. Allowed: {VALID_RACKS}"
                            )
                        if drawer_name not in VALID_DRAWERS:
                            errors.append(
                                f"Invalid Drawer '{drawer_name}'. Allowed: {VALID_DRAWERS}"
                            )
                        row.rack_drawer_combined = f"{rack_name}-{drawer_name}"

                # Slot position validation applies to both paths
                try:
                    slot_pos = int(row.slot_position)
                    if slot_pos < 1 or slot_pos > 100:
                        errors.append(
                            f"Slot Position must be 1–100, got '{slot_pos}'"
                        )
                    else:
                        row.position = self._convert_position_number_to_format(slot_pos)
                except (ValueError, TypeError):
                    errors.append(
                        f"Slot Position must be a number, got '{row.slot_position}'"
                    )

        row.errors = errors

    def _is_valid_time(self, time_str: str) -> bool:
        """Check if time_str is valid HH:MM format."""
        pattern = re.compile(r'^(SCR \(NA\)|M([0-9]|[12][0-9]|3[0-6]))$')
        try:
            if pattern.match(time_str):
                return True
        except ValueError:
            return False

    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date_str is valid YYYY-MM-DD format."""
        if not isinstance(date_str, str):
                date_str = str(date_str).strip()
        try:
            parse(date_str, dayfirst=True)
            #datetime.strptime(date_str, "%d-%b-%y")
            return True
        except (ParserError, ValueError, TypeError):
            return False

    def _is_valid_position_format(self, position: str) -> bool:
        """Check if position format is valid (letter A-J + number 1-10, e.g., A1, J10)."""
        try:
            if not position or len(position) < 2:
                return False
            col_letter = position[0].upper()
            row_num = int(position[1:])
            if not ('A' <= col_letter <= 'J') or row_num < 1 or row_num > 10:
                return False
            return True
        except (ValueError, TypeError):
            return False

    def _convert_position_number_to_format(self, position_number: int) -> str:
        """
        Convert sequential position number (1-100) to grid format (A1-J10).
        Position 1-10 = A1-J1, 11-20 = A2-J2, ..., 91-100 = A10-J10
        """
        zero_indexed = position_number - 1
        row = (zero_indexed // 10) + 1  # 1-10
        col_idx = zero_indexed % 10     # 0-9
        col_letter = chr(65 + col_idx)  # A-J
        return f"{col_letter}{row}"
    
    def _position_to_row_col(self, position: str) -> tuple[Optional[int], Optional[int]]:
        """
        Convert position string (e.g., "A1", "B5", "J10") to (row, col) indices.
        
        Position format: LetterNumber (A-J for columns, 1-10 for rows)
        Returns: (0-based row, 0-based col) or (None, None) if invalid
        
        Examples:
          "A1" → (0, 0)
          "B5" → (4, 1)
          "J10" → (9, 9)
        """
        if not position or len(position) < 2:
            return None, None
        
        try:
            col_letter = position[0].upper()
            row_num = int(position[1:])
            
            # Convert to 0-based indices
            col = ord(col_letter) - ord('A')
            row = row_num - 1
            
            # Validate bounds (10×10 grid: rows 0-9, cols A-J which is 0-9)
            if row < 0 or row >= 10 or col < 0 or col >= 10:
                return None, None
            
            return row, col
        except (ValueError, AttributeError):
            return None, None

    def _get_or_create_storage_hierarchy(
        self, freezer_name: str, container_name: str,
        shelf_name: str, rack_drawer_combined: str
    ) -> tuple[Freezer, Compartment, StorageRack, StorageDrawer, StorageBox]:
        """
        Upright freezer hierarchy (Freezer 1 & 2).

        Correct column → DB level mapping:
          shelf_name (col Q)       → Compartment  (I / II / III / IV)
          rack_letter from col R   → StorageRack   (A / B / C / D / E / F)
          drawer_number from col R → StorageDrawer (01 / 02 / 03 / 04 / 05)
          container_name (col O)   → StorageBox    (actual box name)
        """
        freezer_repo = FreezerRepository(self.session)
        rack_letter, drawer_number = rack_drawer_combined.split('-')

        # Freezer
        freezer = freezer_repo.get_by_name(freezer_name)
        if not freezer:
            freezer = Freezer(name=freezer_name)
            self.session.add(freezer)
            self.session.flush()

        # Compartment = Shelf (I / II / III / IV)
        compartment = next(
            (c for c in freezer.compartments if c.name == shelf_name), None
        )
        if not compartment:
            compartment = Compartment(name=shelf_name, freezer_id=freezer.id)
            self.session.add(compartment)
            self.session.flush()
            # Auto-create 6 racks (A-F) under new shelf
            for rack_val in VALID_RACKS:
                self.session.add(StorageRack(name=rack_val, compartment_id=compartment.id))
            self.session.flush()

        # StorageRack = Rack letter (A / B / C / D / E / F)
        rack = next((r for r in compartment.racks if r.name == rack_letter), None)
        if not rack:
            rack = StorageRack(name=rack_letter, compartment_id=compartment.id)
            self.session.add(rack)
            self.session.flush()
            # Auto-create 5 drawers (01-05) under new rack
            for drawer_val in VALID_DRAWERS:
                self.session.add(StorageDrawer(name=drawer_val, rack_id=rack.id))
            self.session.flush()

        # StorageDrawer = Drawer number (01 / 02 / 03 / 04 / 05)
        drawer = next((d for d in rack.drawers if d.name == drawer_number), None)
        if not drawer:
            drawer = StorageDrawer(name=drawer_number, rack_id=rack.id)
            self.session.add(drawer)
            self.session.flush()

        # StorageBox = container_name (actual box label from Excel col O)
        # Use direct query to avoid stale ORM collection cache on repeated calls
        box = self.session.query(StorageBox).filter(
            StorageBox.name == container_name,
            StorageBox.drawer_id == drawer.id,
        ).first()
        if not box:
            box = StorageBox(name=container_name, drawer_id=drawer.id, rows=10, cols=10)
            self.session.add(box)
            self.session.flush()
            for r in range(10):
                for c in range(10):
                    self.session.add(BoxPosition(box_id=box.id, row=r, col=c))
            self.session.flush()

        return freezer, compartment, rack, drawer, box

    def _get_or_create_storage_hierarchy_cylindrical(
        self, freezer_name: str, container_name: str, rack_number: str
    ) -> tuple[Freezer, Compartment, StorageRack, StorageDrawer, StorageBox]:
        """
        Cylindrical freezer hierarchy (Freezer 3 & 4).

        No shelf or drawer in the physical structure.
        Uses sentinel Compartment("CYLINDRICAL") and Drawer("01") to satisfy
        the fixed-depth DB model.

          CYLINDRICAL_SENTINEL_COMPARTMENT → Compartment
          rack_number (01-13)              → StorageRack
          CYLINDRICAL_SENTINEL_DRAWER      → StorageDrawer
          container_name (col O)           → StorageBox
        """
        freezer_repo = FreezerRepository(self.session)

        freezer = freezer_repo.get_by_name(freezer_name)
        if not freezer:
            freezer = Freezer(name=freezer_name)
            self.session.add(freezer)
            self.session.flush()

        compartment = next(
            (c for c in freezer.compartments
             if c.name == CYLINDRICAL_SENTINEL_COMPARTMENT), None
        )
        if not compartment:
            compartment = Compartment(
                name=CYLINDRICAL_SENTINEL_COMPARTMENT, freezer_id=freezer.id
            )
            self.session.add(compartment)
            self.session.flush()

        rack = next((r for r in compartment.racks if r.name == rack_number), None)
        if not rack:
            rack = StorageRack(name=rack_number, compartment_id=compartment.id)
            self.session.add(rack)
            self.session.flush()

        drawer = next(
            (d for d in rack.drawers if d.name == CYLINDRICAL_SENTINEL_DRAWER), None
        )
        if not drawer:
            drawer = StorageDrawer(
                name=CYLINDRICAL_SENTINEL_DRAWER, rack_id=rack.id
            )
            self.session.add(drawer)
            self.session.flush()

        box = self.session.query(StorageBox).filter(
            StorageBox.name == container_name,
            StorageBox.drawer_id == drawer.id,
        ).first()
        if not box:
            box = StorageBox(name=container_name, drawer_id=drawer.id, rows=10, cols=10)
            self.session.add(box)
            self.session.flush()
            for r in range(10):
                for c in range(10):
                    self.session.add(BoxPosition(box_id=box.id, row=r, col=c))
            self.session.flush()

        return freezer, compartment, rack, drawer, box

    def import_rows(self, rows: list[ImportRow], study_id: int) -> tuple[int, Optional[str]]:
        """
        Import validated rows into the database.

        Returns:
          (count_created, error_message)

        If error_message is not None, import was rolled back.
        """
        # Check for validation errors
        rows_with_errors = [r for r in rows if r.errors]
        if rows_with_errors:
            error_list = "\n".join([
                f"Row {r.row_num}: {'; '.join(r.errors)}"
                for r in rows_with_errors
            ])
            return 0, f"Validation failed:\n{error_list}"

        try:
            study = self.session.query(Study).filter(Study.id == study_id).one()
            freezer_repo = FreezerRepository(self.session)

            created_count = 0

            for row in rows:
                # 1. Get or create Participant (check if already exists for this study)
                participant = self.session.query(Participant).filter(
                    Participant.pid == row.pid,
                    Participant.study_id == study_id
                ).first()
                
                if not participant:
                    participant = Participant(
                        pid=row.pid,
                        study_id=study_id,
                        age=row.age,
                        gender=row.gender,
                        population=row.population,
                        disease=row.disease,
                        site_name=row.site_name,
                        cohort_name=row.cohort_name,
                        notes=row.discrepancy_remark,
                    )
                    self.session.add(participant)
                    self.session.flush()

                # 2. Create Sample
                if row.date_collected:
                    if isinstance(row.date_collected, str):
                        try:
                            # Try parsing the date string to datetime object
                            parsed_date = parse(row.date_collected)
                        except (ParserError, ValueError, TypeError):
                            parsed_date = None
                    elif isinstance(row.date_collected, datetime):
                        # Already a datetime object
                        parsed_date = row.date_collected
                    else:
                        # Try to convert if it's a date object to datetime
                        parsed_date = datetime.combine(row.date_collected, datetime.min.time()) if hasattr(row.date_collected, 'date') else None
                else:
                    parsed_date = None
                
                sample_id_str = generate_sample_id(self.session, study)
                sample = Sample(
                    sample_id=sample_id_str,
                    participant_id=participant.id,
                    study_id=study_id,
                    sample_type=row.sample_type,
                    visit_time=row.visit_time,
                    collection_date=parsed_date,
                    visit_code=row.visit_code,
                    visit_name=row.visit_name,
                )
                self.session.add(sample)
                self.session.flush()

                # 3. Always create SampleAliquot (storage location is optional)
                aliquot_id_str = generate_aliquot_id(sample_id_str, 1)
                aliquot = SampleAliquot(
                    aliquot_id=aliquot_id_str,
                    sample_id=sample.id,
                    aliquot_number=1,
                )
                self.session.add(aliquot)
                self.session.flush()

                # 4. Set storage location if provided
                if row.freezer_name:
                    is_cylindrical = not row.shelf_name
                    if is_cylindrical:
                        freezer, container, shelf, rack, box = \
                            self._get_or_create_storage_hierarchy_cylindrical(
                                row.freezer_name, row.container_name,
                                row.rack_drawer_combined
                            )
                    else:
                        freezer, container, shelf, rack, box = \
                            self._get_or_create_storage_hierarchy(
                                row.freezer_name, row.container_name,
                                row.shelf_name, row.rack_drawer_combined
                            )

                    # Place the aliquot in the box grid
                    if row.position:
                        grid_row, grid_col = self._position_to_row_col(row.position)
                        
                        if grid_row is not None and grid_col is not None:
                            # Get the BoxPosition
                            position = self.session.query(BoxPosition).filter(
                                BoxPosition.box_id == box.id,
                                BoxPosition.row == grid_row,
                                BoxPosition.col == grid_col,
                            ).first()
                            
                            if position:
                                # Create AliquotLocation linking aliquot to position
                                location = AliquotLocation(
                                    aliquot_id=aliquot.id,
                                    position_id=position.id,
                                    freezer_name=freezer.name,
                                    compartment_name=container.name,
                                    rack_name=shelf.name,
                                    drawer_name=rack.name,
                                    box_name=box.name,
                                )
                                self.session.add(location)

                created_count += 1

            self.session.commit()
            return created_count, None

        except Exception as e:
            self.session.rollback()
            return 0, f"Import failed: {str(e)}"
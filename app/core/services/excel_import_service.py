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

# Valid shelf and rack names
VALID_SHELVES = ["I", "II", "III", "IV"]
VALID_RACKS = ["A", "B", "C", "D", "E", "F"]
VALID_DRAWERS = ["01", "02", "03", "04", "05"]
VALID_BOXES = ["Box-1", "Box-2", "Box-3", "Box-4", "Box-5"]


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
        storage_fields = [row.freezer_name, row.container_name, row.shelf_name,
                         row.rack_drawer_combined, row.slot_position]
        has_storage = any(storage_fields)

        if has_storage:
            if not all(storage_fields):
                missing = []
                if not row.freezer_name: missing.append("Freezer / Tank")
                if not row.container_name: missing.append("Container")
                if not row.shelf_name: missing.append("Shelf")
                if not row.rack_drawer_combined: missing.append("Rack")
                if not row.slot_position: missing.append("Slot Position")
                errors.append(f"Storage incomplete. Missing: {', '.join(missing)}")
            else:
                # Validate Shelf
                row.shelf_name = str(row.shelf_name).strip()
                if row.shelf_name not in VALID_SHELVES:
                    errors.append(f"Invalid Shelf '{row.shelf_name}'. Allowed: {VALID_SHELVES}")

                # Validate and parse Rack-Drawer combined field
                rack_drawer = str(row.rack_drawer_combined).strip()
                rack_drawer_parts = rack_drawer.split('-')
                if len(rack_drawer_parts) != 2:
                    errors.append(f"Rack format invalid '{rack_drawer}'. Expected format: 'A-01' (Rack-Drawer)")
                else:
                    rack_name = rack_drawer_parts[0].upper()
                    drawer_name = rack_drawer_parts[1].strip()
                    
                    if rack_name not in VALID_RACKS:
                        errors.append(f"Invalid Rack '{rack_name}'. Allowed: {VALID_RACKS}")
                    if drawer_name not in VALID_DRAWERS:
                        errors.append(f"Invalid Drawer '{drawer_name}'. Allowed: {VALID_DRAWERS}")
                    
                    # Store parsed values back
                    row.rack_drawer_combined = f"{rack_name}-{drawer_name}"

                # Validate Slot Position (1-100) and convert to letter+number format
                try:
                    slot_pos = int(row.slot_position)
                    if slot_pos < 1 or slot_pos > 100:
                        errors.append(f"Slot Position must be between 1 and 100, got '{slot_pos}'")
                    else:
                        # Convert sequential number to grid position (A1-J10)
                        row.position = self._convert_position_number_to_format(slot_pos)
                except (ValueError, TypeError):
                    errors.append(f"Slot Position must be a number, got '{row.slot_position}'")

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
        Get or create the complete storage hierarchy.
        Freezer → Container → Shelf → Rack → Drawer → Box-1 (default)
        Returns tuple of (freezer, container, shelf, drawer, box).
        Auto-creates fixed-count items (shelves, racks, drawers, boxes).
        """
        freezer_repo = FreezerRepository(self.session)

        # Parse Rack-Drawer combined field
        rack_letter, drawer_number = rack_drawer_combined.split('-')

        # Get or create Freezer
        freezer = freezer_repo.get_by_name(freezer_name)
        if not freezer:
            freezer = Freezer(name=freezer_name)
            self.session.add(freezer)
            self.session.flush()

        # Get or create Container (was Compartment)
        container = next(
            (c for c in freezer.compartments if c.name == container_name),
            None
        )
        if not container:
            container = Compartment(name=container_name, freezer_id=freezer.id)
            self.session.add(container)
            self.session.flush()
            
            # Auto-create 4 Shelves when container is created
            for shelf_val in VALID_SHELVES:
                shelf = StorageRack(name=shelf_val, compartment_id=container.id)
                self.session.add(shelf)
            self.session.flush()

        # Get the Shelf (StorageRack with shelf_name)
        shelf = next(
            (s for s in container.racks if s.name == shelf_name),
            None
        )
        if not shelf:
            shelf = StorageRack(name=shelf_name, compartment_id=container.id)
            self.session.add(shelf)
            self.session.flush()
            
            # Auto-create 6 Racks under shelf when shelf doesn't exist
            for rack_val in VALID_RACKS:
                rack = StorageDrawer(name=rack_val, rack_id=shelf.id)
                self.session.add(rack)
            self.session.flush()

        # Get or create Rack (StorageDrawer with rack_letter)
        rack = next(
            (r for r in shelf.drawers if r.name == rack_letter),
            None
        )
        if not rack:
            rack = StorageDrawer(name=rack_letter, rack_id=shelf.id)
            self.session.add(rack)
            self.session.flush()
            
            # Auto-create 5 Drawers under rack when rack doesn't exist
            for drawer_val in VALID_DRAWERS:
                drawer = StorageBox(name=drawer_val, drawer_id=rack.id, rows=10, cols=10)
                self.session.add(drawer)
            self.session.flush()
            
            # Pre-populate grid positions for new drawers
            for drawer in rack.boxes:
                for row in range(10):
                    for col in range(10):
                        self.session.add(BoxPosition(box_id=drawer.id, row=row, col=col))
            self.session.flush()

        # Get or create Drawer (StorageBox with drawer_number)
        drawer = next(
            (d for d in rack.boxes if d.name == drawer_number),
            None
        )
        if not drawer:
            drawer = StorageBox(name=drawer_number, drawer_id=rack.id, rows=10, cols=10)
            self.session.add(drawer)
            self.session.flush()
            
            #Auto-create 5 Boxes under drawer when drawer doesn't exist
            for box_val in VALID_BOXES:
                box = StorageBox(name=box_val, parent_box_id=drawer.id, rows=10, cols=10)
                self.session.add(box)
                self.session.flush()  # Flush to get the box.id
    
                # Pre-populate grid positions for this newly created box
                for row in range(10):
                    for col in range(10):
                        self.session.add(BoxPosition(box_id=box.id, row=row, col=col))
            self.session.flush()

        # Get Box-1 (default box in the drawer)
        box = next(
            (b for b in drawer.child_boxes if b.name == "Box-1"),
            None
        )
        if not box:
            box = StorageBox(name="Box-1", parent_box_id=drawer.id, rows=10, cols=10)
            self.session.add(box)
            self.session.flush()
            
            # Pre-populate grid positions for new box
            for row in range(10):
                for col in range(10):
                    self.session.add(BoxPosition(box_id=box.id, row=row, col=col))
            self.session.flush()

        return freezer, container, shelf, rack, box

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
                    # Create new participant only if it doesn't exist
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
                    print(f"[DEBUG] Created new participant: ID={participant.id}, PID={participant.pid}")
                else:
                    print(f"[DEBUG] Using existing participant: ID={participant.id}, PID={participant.pid}")

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
                    # Get or create storage hierarchy and set aliquot location
                    freezer, container, shelf, rack, box = self._get_or_create_storage_hierarchy(
                        row.freezer_name, row.container_name, row.shelf_name,
                        row.rack_drawer_combined
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
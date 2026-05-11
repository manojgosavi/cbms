# CBMS - Changes Summary

## Overview
This release implements **Excel Bulk Upload** with exact column mapping to match your data structure and adds comprehensive validation for all dropdown fields.

## Files Added

### 1. `app/core/services/excel_import_service.py` (NEW)
Complete Excel import service with:
- **ExcelImportService** class for handling bulk uploads
- **ImportRow** dataclass for parsed Excel rows
- Header validation (21 columns exactly)
- Row-by-row validation with detailed error messages
- Storage hierarchy validation (Freezer → Compartment → Rack → Drawer → Box → Position)
- Transaction-based batch import with rollback on error
- Enum validation for all dropdown fields

**Key Features:**
- Loads Excel file and validates headers match expected structure
- Validates each row: PID (required), enum fields, storage path
- Provides detailed error messages per row
- Imports all valid rows in single transaction
- Returns count of created records or detailed error message

### 2. `app/ui/dialogs/excel_import_dialog.py` (UPDATED)
Completely rewritten dialog for Excel import:
- Clean, user-friendly interface with scrollable error table
- Study selector
- File picker
- Real-time validation with error reporting
- Confirmation before import
- Success/failure messages

**Workflow:**
1. User selects Excel file (21 columns)
2. App validates headers and all rows
3. Shows errors if any (row number + error message)
4. Asks for confirmation if valid
5. Imports all rows in transaction
6. Shows success count or error details

## Files Updated

### 1. `app/config.py` (UPDATED)
Added 7 dropdown enums with exact values for validation:

```python
class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    TRANSGENDER = "Transgender"

class Population(str, Enum):
    FSW = "FSW"
    MSM = "MSM"
    PWID = "PWID"
    GENERAL_ADULT = "General Adult"
    CHILD_ONLY = "Child only"
    PAIR_CHILD = "Pair-Child"
    PAIR_MOTHER = "Pair-Mother"

class Disease(str, Enum):
    DIABETES = "Diabetes"
    INFECTED_NO_COMORBIDITY = "Infected without co-morbidity"
    NONE = "None"
    TB = "TB"
    RISK_CVD = "Risk of CVD"
    UNKNOWN_SCREEN_FAILURE = "Unknown-Screen failure"

class Site(str, Enum):
    GHTM = "GHTM"
    ICMAR_NARI = "ICMAR-NARI"
    NIMHANS = "NIMHANS"
    NIRT = "NIRT"
    YRG_CARE = "YRG-Care"

class VisitName(str, Enum):
    SCREENING = "Screening"
    ENROLLMENT = "Enrollment"
    FOLLOW_UP = "Follow-up"

class SampleType(str, Enum):
    SERUM = "Serum"
    ED_PLASMA = "ED Plasma"
    HEP_PLASMA = "Hep Plasma"
    PBMC = "PBMC"

class CohortName(str, Enum):
    HIV_UNINFECTED = "HIV UNINFECTED"
    HIV_INFECTED_ADULT = "HIV INFECTED-ADULT"
    HIV_INFECTED_PEDIATRIC = "HIV INFECTED-PEDIATRIC"
    EARLY_HIV_INFECTED = "EARLY HIV INFECTED"
```

All existing RBAC roles, permissions, and audit actions preserved.

## Excel File Structure (21 Columns)

| Col | Header | Type | Required | Notes |
|-----|--------|------|----------|-------|
| A | PID | String | Yes | Participant ID from input |
| B | Age | Integer | No | Participant age |
| C | Gender | Dropdown | No | Male \| Female \| Transgender |
| D | Population | Dropdown | No | FSW \| MSM \| PWID \| ... |
| E | Disease | Dropdown | No | Diabetes \| TB \| ... |
| F | Visit Code | String | No | User-defined per study |
| G | Visit Time | Time (HH:MM) | No | Collection time |
| H | Date Collected | Date (YYYY-MM-DD) | No | Collection date |
| I | Site Name | Dropdown | No | GHTM \| ICMAR-NARI \| ... |
| J | Visit Name | Dropdown | No | Screening \| Enrollment \| Follow-up |
| K | Sample Type | Dropdown | No | Serum \| ED Plasma \| ... |
| L | Cohort Name | Dropdown | No | HIV UNINFECTED \| ... |
| M | Aliquot ID | String | No | System-generated if blank |
| N | Freezer / Tank | String | No | Storage level 1 |
| O | Container | String | No | Storage level 2 (Compartment) |
| P | Slot Position | String | No | Storage level 3 (Rack) |
| Q | Shelf | String | No | Storage level 4 (Drawer) |
| R | Rack | String | No | Storage level 5 (Box) |
| S | Position | String | No | Storage level 6 (Grid position, e.g., A1) |
| T | Discrepancy Remark | String | No | Audit note |
| U | Discrepancy For | String | No | Field with discrepancy |

**Storage Hierarchy Validation:**
- If ANY storage column filled, ALL 6 levels must be filled
- All levels must exist in database (no auto-creation)
- Position must be valid grid cell (e.g., A1, B5) for the box

## Validation Rules

### Enums (Strict Matching)
- **Gender**: Male, Female, Transgender
- **Population**: FSW, MSM, PWID, General Adult, Child only, Pair-Child, Pair-Mother
- **Disease**: Diabetes, Infected without co-morbidity, None, TB, Risk of CVD, Unknown-Screen failure
- **Site**: GHTM, ICMAR-NARI, NIMHANS, NIRT, YRG-Care
- **Visit Name**: Screening, Enrollment, Follow-up
- **Sample Type**: Serum, ED Plasma, Hep Plasma, PBMC
- **Cohort Name**: HIV UNINFECTED, HIV INFECTED-ADULT, HIV INFECTED-PEDIATRIC, EARLY HIV INFECTED

### Required Fields
- **PID**: Must be non-empty string

### Optional Fields with Format Validation
- **Age**: Integer only
- **Visit Time**: HH:MM format (e.g., 10:30)
- **Date Collected**: YYYY-MM-DD format (e.g., 2026-04-26)

### Storage Path Validation
- Freezer must exist by name
- Compartment must exist under Freezer
- Rack must exist under Compartment
- Drawer must exist under Rack
- Box must exist under Drawer
- Position must be valid grid cell for Box

## Import Flow

1. **Load Excel File**
   - User selects .xlsx/.xls file
   - Service loads and checks headers match exactly (21 columns)
   - Returns error if headers don't match

2. **Validate All Rows**
   - Each row checked against enums, formats, required fields
   - Storage hierarchy validated if present
   - Returns list of rows with errors (if any)

3. **User Review**
   - Shows validation errors in table (Row # + Error message)
   - User can fix Excel file and retry
   - If all valid, shows confirmation dialog

4. **Batch Import**
   - All valid rows imported in single transaction
   - Creates Participant → Sample → SampleAliquot
   - Sets storage location if provided
   - Rolls back on any error

5. **Success/Failure**
   - Shows count of imported rows
   - Shows detailed error if import failed

## Testing

To test the import:

1. Create an Excel file with the 21 columns (first row = headers)
2. Add data rows matching the structure
3. Open CBMS app → Admin or Participant tab → Find "Import from Excel" button
4. Select Study
5. Select Excel file
6. Review validation results
7. Confirm and import

## Backward Compatibility

- ✅ All existing features unchanged
- ✅ RBAC roles and permissions preserved
- ✅ Storage hierarchy (Freezer → Compartment → Rack → Drawer → Box → Position) from previous update
- ✅ All existing dialogs and views unchanged
- ✅ Database schema unchanged

## Known Limitations

- Excel import does NOT create storage locations automatically
  - All Freezer/Compartment/Rack/Drawer/Box entries must exist before import
  - Use Storage tab to create locations first
- Visit definitions must exist (created during Study setup)
- Position grid cells must be valid for the Box size

## Next Steps

1. Replace `app/config.py` with updated version
2. Replace `app/ui/dialogs/excel_import_dialog.py` with updated version
3. Add new file `app/core/services/excel_import_service.py`
4. Test import with sample Excel file
5. Create storage locations (Freezer/Compartment/Rack/Drawer/Box) before importing with location data


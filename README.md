# CBMS — Central Biorepository Management Software

A desktop application for end-to-end sample lifecycle management in a research biorepository. Built with Python + PyQt6, designed for HIV/infectious-disease cohort studies.

## Tech Stack

| Layer      | Technology         | Version  |
| ---------- | ------------------ | -------- |
| UI         | PyQt6              | 6.7.1    |
| ORM        | SQLAlchemy 2.0     | 2.0.36   |
| Database   | SQLite (local)     | built-in |
| Migrations | Alembic            | 1.14.0   |
| Excel I/O  | openpyxl           | 3.1.5    |
| Auth       | bcrypt + RBAC      | 4.2.1    |
| Charts     | matplotlib         | 3.9.3    |
| Packaging  | PyInstaller        | 6.11.0   |
| Tests      | pytest + pytest-qt | 8.3.4    |

## Project Structure

```
cbms/
├── main.py                        # Entry point — Qt app bootstrap, login, main window
├── requirements.txt
├── alembic.ini                    # DB migration config
├── alembic/
│   └── versions/                  # Migration scripts
├── app/
│   ├── config.py                  # Constants, enums (Gender/Population/…), RBAC, paths
│   ├── core/
│   │   ├── models/
│   │   │   ├── models.py          # All SQLAlchemy ORM models
│   │   │   └── database.py        # Engine + session factory
│   │   ├── services/
│   │   │   ├── auth_service.py    # Login, bcrypt hashing, in-process session
│   │   │   ├── audit_service.py   # Audit log writer
│   │   │   ├── id_generator.py    # Sample / aliquot ID logic
│   │   │   ├── study_service.py
│   │   │   ├── participant_service.py
│   │   │   ├── sample_service.py
│   │   │   ├── storage_service.py
│   │   │   ├── search_service.py
│   │   │   ├── blocking_service.py
│   │   │   ├── shipment_service.py
│   │   │   ├── catalogue_service.py
│   │   │   ├── dashboard_service.py
│   │   │   ├── admin_service.py
│   │   │   ├── audit_query_service.py
│   │   │   └── excel_import_service.py  # Bulk Excel upload (21-column format)
│   │   └── repositories/          # DB query abstractions (base + per-entity)
│   ├── ui/
│   │   ├── views/                 # Full-screen tabs (Dashboard, Studies, Participants…)
│   │   ├── dialogs/               # Modal dialogs (add/edit/import/export/…)
│   │   └── widgets/               # Reusable widgets (BoxGridWidget)
│   └── utils/
│       ├── backup.py              # DB backup helper
│       └── exception_handler.py   # Global Qt exception → QMessageBox hook
├── resources/
│   └── icons/                     # App icons (.icns, .ico, .png)
├── tests/
│   ├── unit/                      # Phase-level unit tests (test_phase1 … test_phase6)
│   └── integration/
├── specs/                         # System constitution and design documents
└── docs/
```

## Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py

# Run tests
pytest tests/ -v
```

## Default Admin Account

On first launch a default admin account is created automatically:

| Field    | Value        |
| -------- | ------------ |
| Username | `admin`      |
| Password | `Admin@1234` |

> **Change the password immediately after first login.**

## Application Tabs

| # | Tab           | Shortcut | Purpose                                              |
|---|---------------|----------|------------------------------------------------------|
| 1 | Dashboard     | Ctrl+1   | Study-level KPIs and sample-type charts              |
| 2 | Studies       | Ctrl+2   | Create / manage research projects and visit schedules|
| 3 | Participants  | Ctrl+3   | Register participants; bulk import from Excel         |
| 4 | Samples       | Ctrl+4   | Log collections; manage aliquots                     |
| 5 | Storage       | Ctrl+5   | Visual freezer hierarchy + box grid                  |
| 6 | Search        | Ctrl+F   | Cross-entity search with advanced filters            |
| 7 | Shipments     | Ctrl+6   | Ship aliquot batches; track courier info             |
| 8 | Catalogue     | Ctrl+7   | Browse & export the full sample catalogue            |
| 9 | Admin         | Ctrl+8   | User management, audit log, backup                   |

Other shortcuts: `Ctrl+N` new participant · `Ctrl+Shift+N` new study · `Ctrl+B` backup now.

## Roles & Permissions

| Permission       | PI | Manager | Lab Tech |
|------------------|----|---------|----------|
| study.create     | ✓  | ✓       |          |
| study.delete     | ✓  |         |          |
| participant.*    | ✓  | ✓       | create/edit |
| sample.*         | ✓  | ✓       | create/edit |
| storage.*        | ✓  | ✓       | edit only |
| shipment.*       | ✓  | ✓       |          |
| admin.*          | ✓  | ✓       |          |
| report.view      | ✓  | ✓       | ✓        |

## Excel Bulk Import (21-Column Format)

Import participants + samples + aliquots + storage placement in a single operation.

**Required column order (row 1 = headers):**

| Col | Header             | Type              | Required |
|-----|--------------------|-------------------|----------|
| A   | PID                | String            | Yes      |
| B   | Age                | Integer           |          |
| C   | Gender             | Male / Female / Transgender |   |
| D   | Population         | FSW / MSM / PWID / General Adult / Child only / Pair-Child / Pair-Mother | |
| E   | Disease            | Diabetes / Infected without co-morbidity / None / NA / TB / Risk of CVD / Unknown-Screen failure | |
| F   | Visit Code         | String            |          |
| G   | Visit Time         | HH:MM             |          |
| H   | Date Collected     | YYYY-MM-DD        |          |
| I   | Site Name          | GHTM / ICMR-NARI / NIMHANS / NIRT / YRG-Care / ICMR-NIRT | |
| J   | Visit Name         | Screening / Enrollment / Follow-up | |
| K   | Sample Type        | Serum / ED Plasma / HEP Plasma / EDTA PBMC | |
| L   | Cohort Name        | HIV UNINFECTED / HIV INFECTED-ADULT / HIV INFECTED-PEDIATRIC / EARLY HIV INFECTED | |
| M   | Aliquot ID         | String (auto-generated if blank) | |
| N   | Freezer / Tank     | String            |          |
| O   | Container          | String (Compartment) |       |
| P   | Slot Position      | String (Rack)     |          |
| Q   | Shelf              | String (Drawer)   |          |
| R   | Rack               | String (Box)      |          |
| S   | Position           | Grid cell e.g. A1 |          |
| T   | Discrepancy Remark | String            |          |
| U   | Discrepancy For    | String            |          |

> Storage columns N–S must all be filled or all blank. Storage locations must already exist — import does not create them.

## Storage Hierarchy

```
Freezer
 └── Compartment
      └── Rack (StorageRack)
           └── Drawer (StorageDrawer)
                └── Box  (StorageBox, N×M grid)
                     └── BoxPosition → AliquotLocation → SampleAliquot
```

Supported box sizes: 9×9, 10×10, 8×12, 6×6.

## Build Phases

| Phase | Status      | Description                                                      |
| ----- | ----------- | ---------------------------------------------------------------- |
| 1     | Complete    | Scaffold, DB models, auth, ID generator                          |
| 2     | Complete    | Study / participant / sample CRUD + Excel bulk import            |
| 3     | Complete    | Storage hierarchy + visual box-grid widget                       |
| 4     | Complete    | Cross-entity search, sample blocking, shipment management        |
| 5     | Complete    | Admin panel (users, audit log), reports tab, catalogue export    |
| 6     | Complete    | DB backup, global exception hook, PyInstaller packaging          |

## Known Limitations / Open TODOs

- Participant tab: visit code not yet shown in the participant list display after Excel import.
- Sample tab: left-hand hierarchy groups by visit name; should group by visit code.
- Storage tab: shipped boxes do not yet turn grey in the grid view.
- Catalogue tab: advanced filters (matching Search tab) not yet implemented.

## Building a Distributable

```bash
# macOS
python build.py        # or: pyinstaller CBMS.spec

# Windows
install_and_build.bat
```

See `MAC_BUILD_INSTRUCTIONS.md` for macOS-specific signing / notarization notes.

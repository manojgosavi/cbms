# CBMS System Constitution

**Version:** 1.0  
**Date:** 2026-05-11  
**Status:** Active

This document is the authoritative reference for all design decisions in CBMS. Any new feature, refactor, or bug fix must be consistent with the rules stated here. If a rule needs to change, update this document first and note the reason.

---

## 1. Purpose and Scope

CBMS is a **local-first desktop application** for biorepository management in HIV/infectious-disease research cohort studies. It runs on a single workstation, stores all data in a local SQLite database, and is distributed as a self-contained executable (PyInstaller).

**In scope:** sample lifecycle (collection → aliquoting → storage → shipment), participant registration, study management, user access control, audit logging, Excel bulk import/export, and operational reports.

**Out of scope:** multi-site networked deployment, cloud sync, patient clinical records beyond demographics, and genomic data management.

---

## 2. Architecture Principles

### 2.1 Layered Architecture

```
UI Layer          app/ui/views/ + app/ui/dialogs/ + app/ui/widgets/
    │  calls only services
Service Layer     app/core/services/
    │  calls only repositories
Repository Layer  app/core/repositories/
    │  uses ORM models
Data Layer        app/core/models/  +  SQLite via SQLAlchemy 2.0
```

- **UI must never import repositories directly.** All DB access goes through a service.
- **Services must never import UI modules.** Services are pure business logic.
- **Repositories must never contain business logic** — only query construction and mapping.

### 2.2 Session Management

All database access uses the `get_session()` context manager from `app/core/models/database.py`. Sessions are **short-lived and closed immediately** after each operation. No ORM objects are stored beyond the `with get_session()` block.

When user identity is needed outside a session (e.g. in the status bar or permission checks), read from `app_session` (an in-process singleton holding plain strings, not the detached ORM `User` object).

### 2.3 State

CBMS is a single-process desktop app with **no REST API and no shared state between processes**. `app_session` is the only global state and holds only the current user's identity (username, role, user_id, email). No caching layer exists.

---

## 3. Data Model

### 3.1 Entity Hierarchy

```
User  ←── AuditLog
Study ←── VisitDefinition
Study ←── Participant ←── ParticipantCustomField
                     ←── Sample ←── SampleAliquot ←── AliquotLocation → BoxPosition
                                                   ←── SampleBlock
                                                   ←── ShipmentItem → Shipment
Freezer ←── Compartment ←── StorageRack ←── StorageDrawer ←── StorageBox ←── BoxPosition
CustomFieldDefinition
```

### 3.2 Primary Keys and Public IDs

| Entity       | Internal PK | Public / User-visible ID       | Rule                                      |
|--------------|-------------|-------------------------------|-------------------------------------------|
| Study        | `id` (int)  | `project_id_short` (e.g. COH) | Unique, user-provided at creation         |
| Participant  | `id` (int)  | `pid`                         | User-provided; unique per study           |
| Sample       | `id` (int)  | `sample_id`                   | System-generated: `<PROJECT>-<YY>-<SEQ>` |
| SampleAliquot| `id` (int)  | `aliquot_id`                  | System-generated: `<SAMPLE_ID>-<N>`      |
| Shipment     | `id` (int)  | `shipment_ref`                | System-generated unique ref               |

Never expose internal integer PKs in the UI or exports. Always use the public ID.

### 3.3 Storage Hierarchy (immutable depth)

The storage hierarchy is exactly 6 levels deep:

```
Freezer → Compartment → StorageRack → StorageDrawer → StorageBox → BoxPosition
```

Constraints:
- A `BoxPosition` belongs to exactly one `StorageBox`.
- An `AliquotLocation` maps one aliquot to one position (both `unique=True` FKs).
- A `StorageBox` may optionally have a `parent_box_id` (sub-box nesting), but this is unused in the current UI; do not extend it without a spec update.
- Box sizes are constrained to the list in `config.BOX_GRID_SIZES`: `(9,9)`, `(10,10)`, `(8,12)`, `(6,6)`.

### 3.4 Aliquot State Machine

An aliquot (`SampleAliquot`) has three boolean flags that are **mutually informative but not mutually exclusive**:

| Flag           | Meaning when True                              |
|----------------|------------------------------------------------|
| `is_available` | Available for use (default True)               |
| `is_blocked`   | Reserved for a specific researcher via `SampleBlock` |
| `is_shipped`   | Included in a completed `Shipment`            |

Rules:
- Shipping sets `is_shipped = True` and `is_available = False`.
- Blocking sets `is_blocked = True` but does not change `is_available`.
- Releasing a block sets `is_blocked = False` and `SampleBlock.is_released = True`.
- A shipped aliquot cannot be blocked or moved.

### 3.5 Audit Log

Every significant mutation (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, SHIP, BLOCK, UNBLOCK, MOVE) must produce an `AuditLog` row via `audit_service`. Audit rows are **immutable** — no UPDATE or DELETE is ever issued on `audit_logs`. The service accepts an open `Session` and does not open its own.

---

## 4. Enumerated Values

All dropdown fields are validated against these enums (defined in `app/config.py`). Case-insensitive matching is supported via `_missing_` on each enum.

### Gender
`Male` · `Female` · `Transgender`

### Population
`FSW` · `MSM` · `PWID` · `General Adult` · `Child only` · `Pair-Child` · `Pair-Mother`

### Disease
`Diabetes` · `Infected without co-morbidity` · `None` · `NA` · `TB` · `Risk of CVD` · `Unknown-Screen failure`

### Site
`GHTM` · `ICMR-NARI` · `NIMHANS` · `NIRT` · `YRG-Care` · `ICMR-NIRT`

### VisitName
`Screening` · `Enrollment` · `Follow-up`

### SampleType
`Serum` · `ED Plasma` · `HEP Plasma` · `EDTA PBMC`

### CohortName
`HIV UNINFECTED` · `HIV INFECTED-ADULT` · `HIV INFECTED-PEDIATRIC` · `EARLY HIV INFECTED`

**Rule:** Adding a new enum value requires updating `app/config.py` AND the Excel import validator AND any relevant UI combo boxes in a single commit. Stale combo boxes that show values the DB does not know are a data-quality defect.

---

## 5. RBAC Model

Three roles exist. Roles are assigned per user and cannot be changed by the user themselves.

| Role     | Abbreviation | Typical holder            |
|----------|--------------|---------------------------|
| PI       | PI           | Principal Investigator     |
| Manager  | MANAGER      | Study coordinator/manager  |
| Lab Tech | LAB_TECH     | Bench technician           |

Permission strings follow the pattern `<resource>.<action>` (e.g. `study.delete`). The full permission map lives in `config.Role.PERMISSIONS`. Permission checks use `Role.can(user.role, action)`.

**Rule:** Never hard-code a role name in service or UI code. Always call `Role.can()`. Never grant a permission by checking `user.role == "PI"` directly.

### Pending new role: AUDITOR (not yet implemented)
If added, AUDITOR should have read-only access to `admin.audit` and `report.view` only.

---

## 6. Authentication

- Passwords are hashed with `bcrypt` (cost factor controlled by bcrypt default, currently 12).
- There is no password-reset flow via email — a Manager or PI resets passwords through the Admin tab.
- Sessions are in-process only; there is no session token, cookie, or JWT.
- The default admin account (`admin` / `Admin@1234`) is seeded on first launch. It must be changed before production use.
- Failed login attempts are not currently rate-limited (known gap; acceptable for a local-only app on a secure workstation).

---

## 7. Excel Import Contract

### 7.1 Column Order (must not change without migration)

Columns A–U in this exact order. The header row must match exactly (case-insensitive trimmed match is acceptable):

```
PID | Age | Gender | Population | Disease | Visit Code | Visit Time |
Date Collected | Site Name | Visit Name | Sample Type | Cohort Name |
Aliquot ID | Freezer / Tank | Container | Slot Position | Shelf | Rack |
Position | Discrepancy Remark | Discrepancy For
```

### 7.2 Import Transaction Guarantee

The entire import is wrapped in a single DB transaction. On any error (validation or DB), the transaction rolls back and **no rows are persisted**. Partial imports are forbidden.

### 7.3 Storage Path Rule

If any of the six storage columns (N–S) is non-empty, **all six** must be non-empty. Partial storage paths are a validation error, not a warning.

### 7.4 Entity Creation Rules During Import

| Entity      | Created during import? | Condition                              |
|-------------|------------------------|----------------------------------------|
| Participant  | Yes                   | If PID does not exist in study         |
| Sample       | Yes                   | Always (one per import row)            |
| SampleAliquot| Yes                   | Always (one per import row)            |
| VisitDefinition | No                 | Must pre-exist; matched by visit_name  |
| Storage nodes | No                  | Must pre-exist; import validates only  |

### 7.5 Aliquot ID Generation During Import

If the `Aliquot ID` column (M) is blank, the system generates one using `id_generator`. If a value is provided, it is used as-is after uniqueness validation.

---

## 8. ID Generation

Sample IDs follow the pattern:

```
<project_id_short>-<YY>-<serial>
e.g.  COH-26-1  →  COH-26-2  →  COH-26-10
```

- `project_id_short` comes from the `Study.project_id_short` field.
- `YY` is the two-digit current year at collection time.
- `serial` is the next available integer for that study+year combination.

Aliquot IDs:

```
<sample_id>-<aliquot_number>
e.g.  COH-26-1-1  →  COH-26-1-2
```

**Rule:** ID generation logic lives exclusively in `app/core/services/id_generator.py`. Do not replicate it elsewhere.

---

## 9. UI Rules

### 9.1 Tab Layout (fixed order)

```
Dashboard → Studies → Participants → Samples → Storage → Search →
Shipments → Catalogue → Admin
```

Tab indices are addressed by keyboard shortcuts (Ctrl+1 … Ctrl+8 + Ctrl+F for Search). Do not reorder tabs without updating all shortcut bindings in `main.py`.

### 9.2 Dialog / View Ownership

- Dialogs never open their own DB sessions for read. They receive data from the calling tab via constructor arguments.
- Dialogs open a session only when the user submits (for write operations).
- A view/tab is responsible for refreshing its own data after a dialog closes with `Accepted`.

### 9.3 Permission Gates in UI

Every button or menu action that requires a permission must call `Role.can(app_session.role, "<permission>")` before enabling the widget or executing the action. Disabled buttons are preferred over hidden buttons so users understand what exists.

### 9.4 Box Grid Widget

`BoxGridWidget` renders the visual grid for a `StorageBox`. Each cell is colour-coded:

| Cell state    | Colour     |
|---------------|------------|
| Empty         | White      |
| Occupied      | Blue       |
| Blocked       | Orange     |
| Shipped       | Grey (TODO — not yet implemented) |

---

## 10. Backup and Data Safety

- Backups are triggered manually (Ctrl+B / Admin menu) or programmatically.
- A backup copies `cbms.db` to `data/backups/cbms_<timestamp>.db`.
- SQLite WAL files (`cbms.db-shm`, `cbms.db-wal`) are checkpointed before backup via `PRAGMA wal_checkpoint(FULL)`.
- No automated scheduled backup exists in the current version.
- The database file path is controlled by `config.DB_PATH`. On a read-only install directory, the fallback is `~/.cbms/data/cbms.db`.

---

## 11. Error Handling

- A global Qt exception hook in `app/utils/exception_handler.py` converts unhandled Python exceptions that occur in Qt slots into a `QMessageBox` instead of silently crashing.
- Service methods surface errors by returning `None` or raising a domain-specific exception. They must never swallow exceptions silently.
- UI code wraps service calls in try/except and shows `QMessageBox.critical()` on failure.

---

## 12. Testing Strategy

| Layer         | Location                  | Tooling               |
|---------------|---------------------------|-----------------------|
| Unit          | `tests/unit/test_phaseN.py` | pytest                |
| Integration   | `tests/integration/`      | pytest (empty, TODO)  |
| UI smoke      | none yet                  | pytest-qt available   |

Unit tests are phase-aligned. Each phase test file covers the services introduced in that phase. Tests use an in-memory SQLite database — never the production `data/cbms.db`.

**Rule:** Service tests must not import any UI module. UI tests must not directly call ORM models.

---

## 13. Packaging

The app is packaged with **PyInstaller** using `CBMS.spec`. The spec bundles:
- All Python packages in `venv/`
- `resources/icons/` for the window icon
- The `data/` directory is **not** bundled — it is created at runtime.

Build scripts:
- macOS: `python build.py` or `pyinstaller CBMS.spec`
- Windows: `install_and_build.bat`

See `MAC_BUILD_INSTRUCTIONS.md` for macOS notarization steps.

---

## 14. Known Gaps and Planned Work

These are acknowledged deficiencies, not bugs to hotfix:

| ID  | Area            | Description                                                    | Priority |
|-----|-----------------|----------------------------------------------------------------|----------|
| G1  | Participant tab  | ~~Visit code not shown in participant list after Excel import~~ | Resolved 2026-05-11 |
| G2  | Sample tab       | ~~Left hierarchy groups by visit name; should use visit code~~ | Resolved 2026-05-11 |
| G3  | Storage tab      | Shipped boxes do not turn grey in the box grid                 | Medium   |
| G4  | Catalogue tab    | Advanced search filters missing (parity with Search tab)       | Low      |
| G5  | Auth             | No login rate-limiting (acceptable for local-only deployment)  | Low      |
| G6  | Backup           | No scheduled/automatic backup                                  | Low      |
| G7  | Tests            | Integration test suite is empty                                | Medium   |

---

## 15. Change Log

| Date       | Change                              | Author        |
|------------|-------------------------------------|---------------|
| 2026-05-11 | Initial constitution written        | Claude Code   |
| 2026-05-11 | G1 resolved: Visit Code column added to Participant tab | Claude Code |
| 2026-05-11 | G2 resolved: Sample tab visit hierarchy now groups by visit_code | Claude Code |

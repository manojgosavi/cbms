# Requirements — Storage Data Migration

**Source:** `specs/TODO.md` — "Implement previous change to existing data imported from excel"  
**Branch:** `feature/storage-data-migration`  
**Date:** 2026-05-11  
**Status:** Approved

---

## Problem

Data imported before the storage hierarchy fix (G storage-hierarchy-fix) was stored with the wrong column-to-level mapping:

| DB Node | Wrong name (current data) | Correct name (after reimport) |
|---------|--------------------------|-------------------------------|
| Compartment | Container value (e.g. `COHNSSER3-R HIV UNINFECTED`) | Shelf value (e.g. `III`) |
| StorageRack | Shelf value (e.g. `III`) | Rack letter (e.g. `D`) |
| StorageDrawer | Rack letter (e.g. `D`) | Drawer number (e.g. `02`) |
| StorageBox (parent) | Drawer number (e.g. `02`) | Container value (e.g. `COHNSSER3-R HIV UNINFECTED`) |
| StorageBox (child) | `Box-1` (hardcoded) | *(removed — Box IS the drawer-level container)* |

Current state: **26 AliquotLocations** pointing to `Box-1` child boxes inside a wrong hierarchy. **27 SampleAliquots** exist (1 unlocated).

---

## Scope

**In scope:**
- A standalone script `migrate_storage.py` at the project root.
- The script deletes all storage-related rows: `AliquotLocation`, `BoxPosition`, `StorageBox`, `StorageDrawer`, `StorageRack`, `Compartment`, `Freezer`.
- `SampleAliquot` records are kept intact — they simply become unlocated after the migration.
- After the script runs, the user reimports from Excel using the now-fixed `ExcelImportService`, which creates the correct hierarchy.

**Out of scope:**
- In-place node renaming.
- Automatic reimport — user triggers it manually via the Participants tab.
- Any changes to application code (no UI changes, no service changes).

---

## What the script does

```
1. Connect to DB at data/cbms.db (or ~/.cbms/data/cbms.db)
2. Print counts of what exists: Freezers, Compartments, Racks, Drawers, Boxes, BoxPositions, AliquotLocations
3. Ask for confirmation (--yes flag skips prompt)
4. Delete in dependency order:
     AliquotLocation  (references BoxPosition)
     BoxPosition      (references StorageBox)
     StorageBox       (references StorageDrawer or parent StorageBox)
     StorageDrawer    (references StorageRack)
     StorageRack      (references Compartment)
     Compartment      (references Freezer)
     Freezer
5. Verify SampleAliquot count is unchanged
6. Print success summary and next-step instructions
```

---

## Deletion order (dependency-safe)

The DB has foreign key constraints. Deletion must go deepest-first:

```
AliquotLocation  → delete first (references BoxPosition)
BoxPosition      → delete (references StorageBox)
StorageBox child → delete child boxes first (parent_box_id FK)
StorageBox       → delete (references StorageDrawer or drawer_id)
StorageDrawer    → delete (references StorageRack)
StorageRack      → delete (references Compartment)
Compartment      → delete (references Freezer)
Freezer          → delete last
```

SQLite does not enforce FK constraints by default, but we delete in order to be safe for any future DB backend.

---

## SampleAliquot state after migration

After deleting AliquotLocations, each `SampleAliquot` no longer has a linked location. The `is_available`, `is_blocked`, and `is_shipped` flags are not changed by this script — they remain as-is. The aliquot simply has no physical location recorded until the user reimports from Excel.

---

## Context

- DB path is determined by `app.config.DB_PATH` (handles both dev and bundled paths).
- The script is run once: `python migrate_storage.py`.
- After running the script, the user opens the app, goes to Participants tab → Import from Excel → selects `CBMS_Dummy_Data.xlsx` → the fixed import service creates the correct hierarchy.
- The script is idempotent: if all storage tables are already empty, it prints "Nothing to migrate" and exits cleanly.

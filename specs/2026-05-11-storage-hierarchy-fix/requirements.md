# Requirements — Storage Hierarchy Fix

**Source:** `specs/TODO.md` — storage hierarchy item  
**Branch:** `feature/storage-hierarchy-fix`  
**Date:** 2026-05-11  
**Status:** Approved

---

## Problem

`excel_import_service._get_or_create_storage_hierarchy()` assigns Excel column values to the wrong DB levels:

| Excel Column | Current DB Level | Correct DB Level |
|---|---|---|
| O — Container | Compartment (level 2) | **StorageBox (level 5) — the Box name** |
| Q — Shelf | StorageRack (level 3) | **Compartment (level 2) — the Shelf** |
| R — Rack (e.g. D-02) letter | StorageDrawer (level 4) | StorageRack (level 3) — the Rack letter |
| R — Rack number (e.g. D-**02**) | StorageBox (level 5) | StorageDrawer (level 4) — the Drawer number |
| hardcoded "Box-1" | StorageBox child | **removed — Box IS the drawer's container** |

Result in app today: Storage tab shows Container values (e.g. "COHNSSER3-R HIV UNINFECTED") as Shelf/Compartment nodes, and Box nodes are named "Box-1". Both are wrong.

Additionally the Storage tab UI calls level 2 "Compartment" — it should be labelled **"Shelf"**.

Cylindrical freezers (Freezer 3 & 4) have no shelves or drawers:
- Hierarchy: Freezer → Rack (01–13) → Box (container_name)
- Currently the import validator rejects rows from these freezers because it requires `shelf_name`.

---

## Scope

**In scope:**
1. **`excel_import_service.py`** — fix `_get_or_create_storage_hierarchy` column-to-level mapping.
2. **`excel_import_service.py`** — add cylindrical freezer detection and a separate hierarchy path.
3. **`storage_tab.py`** — rename "Compartment" → "Shelf" in all UI labels, button text, and tree node prefixes.

**Out of scope:**
- DB model changes — `Compartment`, `StorageRack`, `StorageDrawer`, `StorageBox` model names stay the same.
- Migration of existing imported data — existing rows in the DB are not corrected.
- Any other tab or service.

---

## Upright Freezer Hierarchy (Freezer 1 & 2)

Physical:
```
Freezer (NARI/COHRPICA/18-19/01 REGULAR)
  └── Shelf     (I / II / III / IV)           ← col Q  → Compartment in DB
        └── Rack   (A / B / C / D / E / F)   ← letter from col R (e.g. "D-02" → "D") → StorageRack in DB
              └── Drawer (01 / 02 / 03 / 04 / 05) ← number from col R (e.g. "D-02" → "02") → StorageDrawer in DB
                    └── Box  (Container name)  ← col O → StorageBox in DB
                          └── Position         ← col S → BoxPosition
```

Auto-creation rules unchanged:
- Creating a new Compartment → auto-create 4 Shelves (racks): I, II, III, IV
- Creating a new Shelf → auto-create 6 Racks (drawers): A, B, C, D, E, F
- Creating a new Rack → auto-create 5 Drawers (boxes): 01, 02, 03, 04, 05
- Box is named from container_name — NOT hardcoded "Box-1"

Wait — the auto-creation loop structure must also change. Currently it auto-creates racks under a compartment. After the fix, the compartment IS the shelf, so racks are auto-created under the shelf-compartment.

Actually the auto-creation sequence is identical — only the names passed change. The structure of loops stays the same.

---

## Cylindrical Freezer Hierarchy (Freezer 3 & 4)

Physical:
```
Freezer (NARI/COHRPICA/20-21/23 REGULAR)
  └── Rack (01 / 02 / ... / 13)    ← col R (just a number, no letter prefix)
        └── Box (Container name)   ← col O
              └── Position         ← col S
```

DB mapping (using a sentinel Compartment and Drawer to satisfy the fixed-depth model):
```
Freezer
  └── Compartment("CYLINDRICAL")   ← sentinel, auto-created once per cylindrical freezer
        └── StorageRack (rack_number, e.g. "01" … "13")
              └── StorageDrawer("01")  ← sentinel drawer, auto-created once per rack
                    └── StorageBox (container_name)
```

**Detection rule:** if `shelf_name` is absent (None or empty string), treat as cylindrical. Validation must NOT require `shelf_name` for cylindrical rows.

Rack column format for cylindrical: a plain number string ("01"–"13"), no letter prefix. Validation must accept this.

---

## Validation Changes

Current `_validate_row` requires `shelf_name` as part of `storage_fields`. After the fix:
- If `shelf_name` is absent but other storage fields are present → cylindrical path (valid)
- If `shelf_name` present → upright path, validate shelf in `VALID_SHELVES`
- For cylindrical: validate rack column is numeric string "01"–"13" (no letter-dash-number format required)

---

## UI Label Changes (`storage_tab.py`)

| Location | Before | After |
|---|---|---|
| Tree node prefix (level 2) | `"🔲  {name}"` | `"📋  {name}"` |
| Create button | `"＋ Compartment"` | `"＋ Shelf"` |
| Dialog import in `_on_new_compartment` | `CompartmentDialog` (unchanged) | `CompartmentDialog` (unchanged — dialog title may change separately) |
| `_on_delete_item` success message | `"compartment deleted"` | `"shelf deleted"` |
| Edit handler item_type check | `"compartment"` string | unchanged (internal type key stays "compartment") |

The internal `item_type == "compartment"` string used in `UserRole` data stays unchanged so the edit/delete handlers keep working.

---

## Context

- `VALID_SHELVES = ["I", "II", "III", "IV"]` stays — used only for upright path.
- `VALID_RACKS = ["A", "B", "C", "D", "E", "F"]` stays.
- `VALID_DRAWERS = ["01", "02", "03", "04", "05"]` stays.
- `VALID_BOXES` list (currently `["Box-1"…"Box-5"]`) is no longer used for naming — the box name comes from `container_name`. The constant can be removed.
- Debug `print()` statements in `import_rows` should be removed.

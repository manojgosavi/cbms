# Search → Storage Navigation Fix

**Date:** 2026-05-13  
**Branch:** feature/search-storage-navigate-fix  
**Status:** In Progress

---

## Scope

Double-clicking a row in the Search tab (or clicking "Show in box") should:
1. Switch to the Storage tab.
2. Expand and select the tree node for the aliquot's box.
3. Load the box grid for that box.
4. Highlight (select) the specific cell that contains the aliquot.

Currently `show_aliquot_location` in `main_window.py` only calls `tabs.setCurrentWidget(storage_tab)` — steps 2–4 are missing entirely.

---

## Root Cause

`main_window.py` line 215:
```python
def show_aliquot_location(self, aliquot_db_id: int):
    self.tabs.setCurrentWidget(self.storage_tab)   # ← only this, nothing else
```

`StorageTab` has no public method to accept an aliquot ID and navigate to it. The tree node selection, box grid load, and cell highlight all need to be driven from a new `navigate_to_aliquot(aliquot_db_id)` method on `StorageTab`.

---

## Data path to find the box and cell

```
AliquotLocation.aliquot_id == aliquot_db_id
  → AliquotLocation.position_id
    → BoxPosition.id  → BoxPosition.box_id, BoxPosition.row, BoxPosition.col
```

The tree already stores `("box", box_id)` in each box node's `UserRole` data, so the tree can be searched by `box_id` to find and select the correct item.

---

## Decisions

| Decision | Choice |
|----------|--------|
| Where does the DB lookup live? | Inside `StorageTab.navigate_to_aliquot()` — keeps main_window thin |
| Tree item search | Walk all items with `QTreeWidget.findItems` / iterate top-level recursively to match `("box", box_id)` |
| Cell highlight | Add `select_cell(row, col)` to `BoxGridWidget`; called after `_load_box_grid` |
| Aliquot has no location | Show a `QMessageBox.information` "This aliquot has no storage location recorded." |

---

## Out of Scope

- Changing how the search result table is displayed.
- Navigating from any tab other than Search.

# Plan — Storage Tab: Shipped Cells Turn Grey

**Branch:** `feature/shipped-box-grey`  
**Estimated effort:** 20 minutes  
**Files changed:** 2 (`app/core/services/shipment_service.py`, `app/ui/views/storage_tab.py`)

---

## Task Group 1 — Fix the root cause in shipment_service.py

1.1 Open `app/core/services/shipment_service.py`.

1.2 Remove the block that deletes `AliquotLocation` (lines 109–116):

```python
# REMOVE THIS ENTIRE BLOCK:
# Remove from storage location (scope doc: "automatically removed from location")
loc = (
    self.session.query(AliquotLocation)
    .filter(AliquotLocation.aliquot_id == aid)
    .first()
)
if loc:
    self.session.delete(loc)
```

After removal, the per-aliquot loop only does three things: mark as shipped, release the block, add the `ShipmentItem`.

1.3 Update the module docstring to remove the line "After shipment, aliquot is removed from its storage location automatically" — replace with "After shipment, the aliquot's location is preserved for grid history; the cell renders grey."

1.4 Remove the now-unused `AliquotLocation` import if it is no longer referenced. Check: `AliquotLocation` is only imported to query and delete it. After removing that block, the import is unused.

---

## Task Group 2 — Lock shipped cells in storage_tab.py

2.1 Open `app/ui/views/storage_tab.py`, method `_on_cell_clicked`.

2.2 After the existing occupied-cell branch, add a shipped check that overrides the Move/Remove enabled state:

```python
@slot_safe
def _on_cell_clicked(self, row: int, col: int):
    if not self._current_box_id:
        return

    cells = self._grid._cells
    cell = cells.get((row, col))

    col_label = chr(ord('A') + col) if col < 26 else f"C{col}"
    position_label = f"Position {row + 1}{col_label}"

    if cell and cell.aliquot_id:
        self._cell_detail.setText(
            f"{position_label}\n{cell.tooltip or cell.aliquot_label}"
        )
        self._btn_place.setEnabled(False)
        # Shipped cells are locked — aliquot is no longer physically present
        if cell.is_shipped:
            self._btn_move.setEnabled(False)
            self._btn_remove.setEnabled(False)
        else:
            self._btn_move.setEnabled(True)
            self._btn_remove.setEnabled(True)
    else:
        self._cell_detail.setText(f"{position_label} — Empty")
        self._btn_place.setEnabled(True)
        self._btn_move.setEnabled(False)
        self._btn_remove.setEnabled(False)

    self._cell_info.setVisible(True)
```

---

## Task Group 3 — Update docs

3.1 Mark G3 resolved in `specs/constitution.md` §14.

3.2 Strike the G3 item in `TODO.md`.

3.3 Update the constitution §9.4 box grid colour table — remove the `(TODO — not yet implemented)` note from the Shipped row.

---

## Task Group 4 — Commit

```
feat(storage-tab): shipped aliquot cells now render grey

Resolves G3. Removes the AliquotLocation deletion from ShipmentService
so shipped cells remain visible in the box grid as grey (is_shipped=True).
Locks Move/Remove buttons on shipped cells in the storage tab.
```

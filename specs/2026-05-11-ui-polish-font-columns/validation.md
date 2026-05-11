# Validation — UI Polish: Box Grid Font & Column Widths

**Method:** Manual visual check  
**Test file:** `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`  
**Gate:** All checks must pass before merging to `main`

---

## Pre-conditions

- [ ] App runs from source (`python main.py`).
- [ ] `CBMS_Dummy_Data.xlsx` has been imported (27 aliquots with storage locations).

---

## Box Grid Checks

### SC-1 — Aliquot label stays inside the cell

- [ ] Open **Storage tab**.
- [ ] Expand Freezer → Shelf III → Rack D → Drawer 02 → Box `COHNSSER3-R HIV UNINFECTED`.
- [ ] Click the box to load the grid.
- [ ] Find the occupied (blue) cell.
- [ ] The PID label (`COH-26-1-A1` or similar) is fully contained inside the cell — no text spills into adjacent cells.

### SC-2 — Font is legible at reduced size

- [ ] The shrunk label is still readable at arm's length — not so tiny it's invisible.
- [ ] Bold is applied for larger sizes, plain for the smallest.

### SC-3 — Empty cells unaffected

- [ ] Empty (white) cells show no label and no rendering artefact.
- [ ] Hover highlight still works on empty cells.

### SC-4 — Shipped/blocked cells still show label correctly

- [ ] If any aliquot is blocked (orange) or shipped (grey), its label still renders inside the cell.

---

## Column Width Checks

### SC-5 — Participant tab: Age column is compact

- [ ] Open **Participants tab**.
- [ ] With 10 participants loaded, the **Age** column is narrow (fits the number, not stretched to fill the screen).
- [ ] **PID** and **Study** columns auto-fit their content.
- [ ] **Notes** column takes the remaining space (stretches).
- [ ] No horizontal scrollbar appears at the default window size.

### SC-6 — Participant tab: all columns visible without scroll

- [ ] All 11 columns (PID → Registered) are visible in one view at 1280px width.
- [ ] No column is excessively wide.

### SC-7 — Search tab: Discrepancy column stretches

- [ ] Open **Search tab** → click **Search** (no filters).
- [ ] The **Discrepancy** column (last column) stretches to fill remaining space.
- [ ] Freezer / Compartment / Rack / Drawer / Box / Position columns auto-fit their content — short values (e.g. `III`, `D`, `02`) produce narrow columns.

### SC-8 — Other tabs unaffected

- [ ] **Sample tab** tree columns: unchanged — still shows ID, Type, Date, Status, Discrepancy correctly.
- [ ] **Shipment tab**: unchanged.
- [ ] **Admin tab**: unchanged.
- [ ] **Catalogue tab**: unchanged.

---

## Failure Criteria (do not merge if any occur)

| Symptom | Likely cause |
|---------|--------------|
| Text still overflows box cell | `_draw_fitted_label` not called — `drawText` with old `font_label` still in place |
| `AttributeError: horizontalAdvance` | `QFontMetrics` not imported |
| Age column is still very wide | `setSectionResizeMode(2, Stretch)` not replaced |
| Notes column not visible (too narrow) | Stretch set on wrong index — verify COLUMNS list has 11 items, Notes at index 9 |
| Discrepancy not stretching in Search | Index 18 is wrong — count COLUMNS list |
| Other tabs broken | Wrong file edited — check only 3 files changed |

---

## Post-merge checklist

- [ ] `specs/constitution.md` §15 changelog updated.
- [ ] `specs/TODO.md` both items struck.

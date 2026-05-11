# Validation — Dashboard: Cohort Flowchart

**Method:** Manual smoke test  
**Test file:** `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`  
**Gate:** All checks must pass before merging to `main`

---

## Expected Data from CBMS_Dummy_Data.xlsx

After importing the dummy file, the flowchart should reflect:

| Cohort                | Population | Visit      | Participants | Serum | ED Plasma | HEP Plasma | EDTA PBMC |
|-----------------------|------------|------------|-------------|-------|-----------|------------|-----------|
| HIV UNINFECTED        | FSW        | Screening  | 1           | 1     | 1         | –          | –         |
| HIV UNINFECTED        | FSW        | Enrollment | 1           | 1     | 1         | –          | –         |
| HIV INFECTED-ADULT    | –          | Enrollment | varies      | –     | –         | –          | –         |
| HIV INFECTED-PEDIATRIC| –          | Enrollment | varies      | –     | –         | –          | –         |

(Exact counts depend on what's already in the DB. Verify by cross-referencing the Search tab.)

---

## Smoke Test Checklist

### SC-1 — Matplotlib charts are gone

- [ ] Open app → Dashboard tab.
- [ ] No matplotlib charts visible (no bar chart, no pie chart, no histogram).
- [ ] No NavigationToolbar (zoom/pan/save buttons) visible.

### SC-2 — KPI strip still works

- [ ] Six KPI cards still visible at the top: Participants, Samples, Aliquots, Available, Blocked, Shipped.
- [ ] Numbers are non-zero after importing dummy data.

### SC-3 — Flowchart blocks appear

- [ ] Four `QGroupBox` blocks visible, labelled:
  - `Adult PLHIV`
  - `CLHIV`
  - `Early HIV (F < 1 yr)`
  - `HIV Negative At Risk`
- [ ] Blocks are laid out left to right in a scrollable area.

### SC-4 — Non-UNINFECTED cohort table structure

- [ ] `Adult PLHIV` block has a table with column headers `S`, `E`, `F`.
- [ ] Row headers: `n =`, `Serum`, `ED Plasma`, `HEP Plasma`, `EDTA PBMC`.
- [ ] `n =` row is highlighted (blue-ish background).
- [ ] Cells with non-zero vial counts are highlighted (green-ish background).

### SC-5 — HIV UNINFECTED block has population sub-groups

- [ ] `HIV Negative At Risk` block contains three sub-group boxes: `FSW`, `PWID`, `MSM`.
- [ ] Each sub-group has its own `S`, `E`, `F` columns and the same row structure.

### SC-6 — Counts match the database

- [ ] Pick one participant from the dummy data (e.g. `COH20N01A2001S`, HIV UNINFECTED, FSW, Screening).
- [ ] Find their sample type (Serum) and visit (Screening).
- [ ] Confirm the `FSW → S → Serum` cell shows the correct vial count.
- [ ] Cross-check using Search tab: filter by PID, note aliquot count.

### SC-7 — Study filter narrows flowchart

- [ ] Select a specific study in the Study dropdown.
- [ ] Click Refresh.
- [ ] Flowchart updates — counts reflect only that study's data.
- [ ] Select "All studies" → full counts return.

### SC-8 — Empty cohorts show gracefully

- [ ] If a cohort has no data (e.g. CLHIV if no paediatric samples imported), its table is empty but the block still renders without error.
- [ ] No Python exception in the terminal.

### SC-9 — Horizontal scroll works

- [ ] If the window is narrow, a horizontal scrollbar appears.
- [ ] All four cohort blocks are reachable by scrolling.

### SC-10 — No crashes on tab switch

- [ ] Switch away from Dashboard tab and back several times.
- [ ] No exception raised. KPI and flowchart remain correct.

---

## Failure Criteria (do not merge if any occur)

| Symptom | Likely cause |
|---------|--------------|
| `AttributeError: _has_matplotlib` | Old `if self._has_matplotlib` guard not removed |
| Flowchart area is blank | `_draw_flowchart()` not called in `refresh()`, or `get_flowchart_data()` returns empty |
| `n =` row shows wrong count | `max()` across visit_data sample types used — verify participant count logic |
| HIV UNINFECTED shows no sub-groups | `pop_key` matching not finding FSW/PWID/MSM — check `population` field values in DB |
| Counts all zero | Query join order wrong or `study_id` filter applied incorrectly |
| App crashes on Dashboard load | Import error or widget parenting issue — check console traceback |

---

## Post-merge checklist

- [ ] `specs/constitution.md` §15 changelog updated.
- [ ] `specs/TODO.md` dashboard item struck.

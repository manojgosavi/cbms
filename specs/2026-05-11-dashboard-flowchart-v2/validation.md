# Validation — Dashboard Flowchart v2

**Method:** Manual visual check against reference image  
**Reference:** `/Users/manojgosavi/Downloads/FlowChart.jpeg`  
**Test file:** `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`  
**Gate:** All checks must pass before merging to `main`

---

## Pre-conditions

- [ ] App runs from source (`python main.py`).
- [ ] `CBMS_Dummy_Data.xlsx` has been imported into at least one study.

---

## Smoke Test Checklist

### SC-1 — Cohort selector appears

- [ ] Open app → Dashboard tab.
- [ ] Below the KPI strip, a right-aligned `Cohort:` dropdown is visible.
- [ ] Dropdown contains 4 entries: Cohort of Adult PLHIV · Cohort of CLHIV · Cohort of Early HIV (F<1yr) · HIV Negative At Risk Persons.
- [ ] Default selection is the first cohort (Adult PLHIV).

### SC-2 — No QTableWidget blocks visible

- [ ] The old 4-block horizontal layout with grey QTableWidget grids is gone.
- [ ] No NavigationToolbar or matplotlib elements visible.

### SC-3 — Custom painted widget renders

- [ ] The flowchart area shows a custom-drawn grid (not a standard Qt widget).
- [ ] Dark blue header banner at the top with white cohort name text.
- [ ] Visit column headers (S / E / F) with light blue background.
- [ ] n= row below visit headers with a slightly darker blue background.
- [ ] Sample type rows (Serum / ED Plasma / HEP Plasma / EDTA PBMC) with grey label column on the left.
- [ ] Non-zero vial count cells have a light green background.
- [ ] Zero / empty cells are white.
- [ ] Grid lines are visible between all cells.

### SC-4 — Cohort selector switches view

- [ ] Select **Cohort of CLHIV** → flowchart redraws showing only E and F columns (no S column).
- [ ] Select **Cohort of Early HIV** → same — E and F only.
- [ ] Select **HIV Negative At Risk** → three population sub-group header bands (FSW / PWID / MSM) appear above visit headers; each has S · E · F columns.
- [ ] Select **Cohort of Adult PLHIV** → returns to 3-column (S/E/F) view.

### SC-5 — HIV UNINFECTED sub-group headers

- [ ] When "HIV Negative At Risk" is selected, a second header row appears showing FSW / PWID / MSM group labels in mid-blue.
- [ ] Each group has S · E · F sub-columns.
- [ ] Total columns = 9 (3 populations × 3 visits).

### SC-6 — Counts match Search tab

- [ ] Find a specific participant in the Search tab (e.g. `COH20N01A2001S`, FSW, Screening, Serum).
- [ ] Switch to Dashboard → select "HIV Negative At Risk".
- [ ] FSW → S → Serum cell shows a count ≥ 1.

### SC-7 — Study filter still narrows data

- [ ] Select a specific study in the Study dropdown → click Refresh.
- [ ] n= values and vial counts update.
- [ ] Select "All studies" → full counts return.

### SC-8 — KPI strip unaffected

- [ ] Six KPI cards still visible at top with correct counts.

### SC-9 — Visual comparison to reference image

Open `/Users/manojgosavi/Downloads/FlowChart.jpeg` side-by-side:
- [ ] Cohort header color is dark blue (close to `#1F4E79`).
- [ ] Visit headers (S/E/F) have a lighter blue band.
- [ ] The n= row is clearly distinguished from sample type rows.
- [ ] Sample type labels are left-aligned in a grey column.
- [ ] Overall impression: "substantially closer to the reference than v1."

### SC-10 — No crash on switching cohorts rapidly

- [ ] Click through all 4 cohorts quickly several times.
- [ ] No Python exception in the terminal.
- [ ] Widget redraws correctly each time.

---

## Failure Criteria (do not merge if any occur)

| Symptom | Likely cause |
|---------|--------------|
| Widget is blank / not drawn | `_spec` is None — `load()` not called after `_build_flowchart_spec()` |
| `AttributeError: _cohort_combo` | `_build_ui()` not updated — old v1 `_flow_layout` still referenced |
| Population sub-groups missing for HIV UNINFECTED | `has_group_headers` not set or group painting block skipped |
| Counts all zero | `get_flowchart_data()` returns empty — check study filter or DB content |
| Widget too small / cut off | `setMinimumSize()` not called in `_recalculate_size()` |
| `QPainter: must call begin()` error | `paintEvent` called before widget shown — harmless warning, not a blocker |

---

## Post-merge checklist

- [ ] `specs/constitution.md` §15 changelog updated.
- [ ] `specs/TODO.md` redesign item struck through.

# Validation — Catalogue Tab: Advanced Filters

**Method:** Manual smoke test using the project dummy data file  
**Test file:** `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`  
**Gate:** All checks must pass before merging to `main`

---

## Test Data Facts (CBMS_Dummy_Data.xlsx)

10 unique PIDs across various genders, diseases, cohorts, and sites:

| Field       | Values present in file                          |
|-------------|-------------------------------------------------|
| Gender      | Female, Male                                    |
| Disease     | None, NA                                        |
| Cohort      | HIV UNINFECTED, HIV INFECTED-ADULT, HIV INFECTED-PEDIATRIC |
| Site        | ICMR-NARI, GHTM                                |
| Sample Type | Serum, ED Plasma, HEP Plasma, EDTA PBMC        |

Import the dummy file before running these tests (or use existing data).

---

## Smoke Test Checklist

### SC-1 — Filter panel appears

- [ ] Open app → Catalogue tab.
- [ ] A second group box labelled **"Narrow results"** is visible below "Catalogue filters".
- [ ] It contains: PID field, Gender combo, Disease field, Cohort combo, Site combo, Sample Type combo, Clear filters button.
- [ ] All combos default to "All …".

### SC-2 — Baseline: unfiltered catalogue

- [ ] Click **Generate Catalogue** with all "Narrow results" fields at their defaults.
- [ ] All 10 participants appear in the pivot table.
- [ ] Summary label shows no `[filtered]` note.

### SC-3 — PID filter (partial match)

- [ ] Type `COH20` in the PID field.
- [ ] Click **Generate Catalogue**.
- [ ] Only participants whose PID contains `COH20` appear.
- [ ] Summary label shows `[filtered]`.

### SC-4 — Gender filter

- [ ] Set Gender to `Female`.
- [ ] Click **Generate Catalogue**.
- [ ] Only female participants appear.
- [ ] Set Gender back to "All genders" → all participants return.

### SC-5 — Disease filter (partial match)

- [ ] Type `None` in Disease.
- [ ] Click **Generate Catalogue**.
- [ ] Only participants with disease containing "None" appear.

### SC-6 — Cohort filter

- [ ] Set Cohort to `HIV UNINFECTED`.
- [ ] Click **Generate Catalogue**.
- [ ] Only HIV UNINFECTED participants appear.

### SC-7 — Site filter

- [ ] Set Site to `ICMR-NARI`.
- [ ] Click **Generate Catalogue**.
- [ ] Only ICMR-NARI participants appear.

### SC-8 — Sample Type column filter

- [ ] Set Sample Type to `Serum`.
- [ ] Click **Generate Catalogue**.
- [ ] Pivot table shows only the `Serum` column (no ED Plasma, HEP Plasma, etc.).
- [ ] Row counts reflect Serum aliquots only.

### SC-9 — Combined filters

- [ ] Set Gender = `Female`, Site = `ICMR-NARI`.
- [ ] Click **Generate Catalogue**.
- [ ] Only female participants from ICMR-NARI appear.

### SC-10 — Clear filters button

- [ ] With filters set from SC-9, click **Clear filters**.
- [ ] All filter fields reset to defaults ("All …" combos, blank text fields).
- [ ] Click **Generate Catalogue** → full unfiltered catalogue appears.

### SC-11 — Export reflects filtered view

- [ ] Apply a site filter (e.g. `GHTM`).
- [ ] Generate catalogue.
- [ ] Click **Export to Excel…** and save.
- [ ] Open the exported file — it contains only the filtered rows/columns, not all data.

### SC-12 — No data state

- [ ] Apply a filter that matches no participant (e.g. PID = `ZZZZZ`).
- [ ] Click **Generate Catalogue**.
- [ ] Summary label shows "No data found for selected filters."
- [ ] Table is empty. Export button is disabled.

---

## Failure Criteria (do not merge if any occur)

| Symptom | Likely cause |
|---------|--------------|
| Filter panel not visible | `narrow_box` not added to `layout` in `_build_ui` |
| Filter has no effect | `_on_generate` filter pass not applied before populating the table |
| Sample Type filter removes all columns | `stype_q` comparison is case-sensitive and doesn't match stored values |
| `[filtered]` label not shown | `filter_note` variable not included in summary string |
| Clear button doesn't reset combos | `setCurrentIndex(0)` not called on combos in `_on_clear_filters` |
| Export contains all data despite filter | `self._rows` / `self._col_headers` assigned before filter pass |

---

## Post-merge checklist

- [ ] `specs/constitution.md` §14: mark G4 `Resolved 2026-05-11`.
- [ ] `TODO.md`: strike the catalogue filters item.

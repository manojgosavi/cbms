# Requirements — Catalogue Tab: Advanced Filters

**Gap ID:** G4  
**Branch:** `feature/catalogue-filters`  
**Date:** 2026-05-11  
**Status:** Approved

---

## Problem

The Catalogue tab currently exposes only two filters — Study and "Available only". The Search tab has seven filter fields (PID, Age, Site, Visit Time, Cohort, Disease, Sample Type). Researchers using the Catalogue tab to decide which samples to request have no way to narrow the pivot table without exporting to Excel first.

## Scope

**Filters to add (full parity with Search tab, minus Age and Visit Time):**

| Filter       | Widget                  | Match type      | Source enum / field          |
|--------------|-------------------------|-----------------|------------------------------|
| PID          | `QLineEdit`             | Partial (case-insensitive) | `CatalogueRow.pid`   |
| Gender       | `QComboBox`             | Exact           | `config.Gender` + "All"      |
| Disease      | `QLineEdit`             | Partial (case-insensitive) | `CatalogueRow.disease` |
| Cohort       | `QComboBox`             | Exact           | `config.CohortName` + "All"  |
| Site         | `QComboBox`             | Exact           | `config.Site` + "All"        |
| Sample Type  | `QComboBox`             | Exact (column filter) | `config.SampleType` + "All" |

Age and Visit Time are excluded — they belong to `Sample`, not `Participant`, and are not in `CatalogueRow`.

**Out of scope:**
- Any change to `CatalogueService.generate()` — service returns all rows; filtering happens in the UI.
- Changes to the Excel export — export uses whatever is currently in `self._rows` and `self._col_headers` after filtering, so it reflects the filtered view automatically.
- AND/OR mode — catalogue filters always apply as AND (all conditions must match).

---

## Filtering Strategy

**Post-query Python filter in the UI** (user decision). After `svc.generate()` returns:

```python
rows, col_headers = svc.generate(study_id=study_id, available_only=avail)

# 1. Filter rows by participant-level fields
pid_q     = self._f_pid.text().strip().lower()
gender_q  = self._f_gender.currentData()    # None = "All"
disease_q = self._f_disease.text().strip().lower()
cohort_q  = self._f_cohort.currentData()    # None = "All"
site_q    = self._f_site.currentData()      # None = "All"
stype_q   = self._f_stype.currentData()     # None = "All"

def _row_matches(row: CatalogueRow) -> bool:
    if pid_q     and pid_q not in row.pid.lower():                   return False
    if gender_q  and row.gender  != gender_q:                        return False
    if disease_q and disease_q not in (row.disease or "").lower():   return False
    if cohort_q  and row.cohort_name != cohort_q:                    return False
    if site_q    and row.site_name   != site_q:                      return False
    return True

rows = [r for r in rows if _row_matches(r)]

# 2. Filter pivot columns by sample type
if stype_q:
    col_headers = [c for c in col_headers if c == stype_q]
    for r in rows:
        r.sample_counts = {k: v for k, v in r.sample_counts.items() if k == stype_q}
```

---

## UI Layout

The existing `QGroupBox("Catalogue filters")` holds Study and Available-only. Add a second `QGroupBox("Narrow results")` below it with the six new fields arranged in two rows using `QHBoxLayout`:

**Row 1:** PID · Gender · Disease  
**Row 2:** Cohort · Site · Sample Type · [Clear Filters] button

The "Generate Catalogue" button triggers both the service call and the filter pass. Changing a filter field does NOT auto-refresh — user must click Generate again (consistent with current behaviour).

---

## Context

- `CatalogueRow` fields available for filtering: `pid`, `gender`, `disease`, `cohort_name`, `site_name`. All others (`age`, `visit_code`) are not on `CatalogueRow`.
- `CatalogueService.generate()` already accepts a `sample_types` list param but it queries at DB level. We do not use this param — the sample type filter here narrows only the displayed pivot columns post-query, keeping the service unchanged.
- Enums for combo boxes come from `app.config`: `Gender`, `Disease`, `CohortName`, `Site`, `SampleType`.
- The "Export to Excel" button uses `self._rows` and `self._col_headers`, which are assigned after filtering — exports will reflect the filtered view with no extra work.

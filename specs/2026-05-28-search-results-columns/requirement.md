# Requirement: Search Tab — Add Visit Code & Population Columns, Remove Vol

## Source
TODO.md:
> In search tab, results in right pane should include visit code & population column, remove the Vol column.

---

## Problem Statement
The Search tab results table currently shows `Vol (µL)` (aliquot volume) but is missing two contextually important fields: `Visit Code` (which visit the sample was collected at) and `Population` (participant demographic group like FSW/MSM/PWID). Lab staff need these to quickly assess results without cross-referencing other tabs.

---

## Functional Requirements

### FR-1: Add "Visit Code" Column
- Add a "Visit Code" column to the results table, populated from `Sample.visit_code`.
- `SearchResult` dataclass must be extended with a `visit_code` field.
- The search service must populate `visit_code` from `sample.visit_code`.

### FR-2: Add "Population" Column
- Add a "Population" column, populated from `Participant.population`.
- `SearchResult` dataclass must be extended with a `population` field.
- The search service must populate `population` from `participant.population`.

### FR-3: Remove "Vol (µL)" Column
- Remove the `Vol (µL)` column from the results table display.
- `volume_ul` field may be retained in `SearchResult` for potential export use — not displayed.

---

## Affected Files
| File | Change |
|---|---|
| `app/core/services/search_service.py` | Add `visit_code`, `population` to `SearchResult`; populate in `search()` |
| `app/ui/views/search_tab.py` | Update `COLUMNS`, `values` list, fix `Stretch` resize index |

---

## Out of Scope
- Adding Visit Code / Population as new filter fields in the left pane (already exist).
- Any changes to Export dialog columns.
- Any other tab changes.

---

## Confirmed Decisions
1. **Population** placed after Cohort (participant demographic block).
2. **Visit Code** placed after Collection Date (sample block).
3. **Vol (µL)** removed from on-screen table only; `volume_ul` kept in `SearchResult` so Excel export is unaffected.

Final column order (20 columns):
`PID | Age | Gender | Disease | Cohort | Population | Site | Sample ID | Sample Type | Collection Date | Visit Code | Aliquot ID | Status | Freezer | Compartment | Rack | Drawer | Box | Position | Discrepancy`

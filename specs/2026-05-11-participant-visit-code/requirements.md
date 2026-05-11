# Requirements — Participant Tab: Visit Code Column

**Gap ID:** G1  
**Branch:** `feature/visit-code-display`  
**Date:** 2026-05-11  
**Status:** Approved

---

## Problem

After a bulk Excel import, each `SampleAliquot` record is linked back to a `Sample`, and `Sample.visit_code` stores the visit code from the import (e.g. `SCR(NA)`, `M0`, `M6`). However, the Participant tab list does not display this information. A lab technician looking at the participant list has no way to know which visit codes a participant has data for without drilling into the Sample tab.

## Scope

**In scope (G1 only):**
- Add a `Visit Code` column to the existing `QTableWidget` in `app/ui/views/participant_tab.py`.
- Populate it by querying each participant's associated `Sample.visit_code` values from the DB.
- A participant with no samples shows an empty cell.
- A participant with multiple samples shows all distinct visit codes, comma-separated and sorted (e.g. `M0, M6, SCR(NA)`).

**Out of scope:**
- G2 (sample tab hierarchy by visit code) — separate spec.
- Filtering or sorting the participant list by visit code.
- Editing visit codes from the participant tab.
- Any change to the data model (`Participant` model has no `visit_code` field and should not gain one — visit code is a per-sample property, not a per-participant property).

---

## Data Flow

```
Participant (id) ──< Sample (participant_id, visit_code)
```

The participant service's `search()` returns `Participant` ORM objects (detached after the session closes). Visit codes must be fetched within the same session and collected into a plain dict before the session closes.

**Correct approach:**
```python
# Inside the existing `with get_session()` block in participant_tab.refresh()
visit_codes: dict[int, str] = {}
for p in participants:
    codes = sorted(set(
        s.visit_code for s in p.samples if s.visit_code
    ))
    visit_codes[p.id] = ", ".join(codes)
```

`p.samples` is eagerly accessible within the same session because SQLAlchemy will lazy-load it before the session closes. Once the session closes, do not access `p.samples` again.

**Alternative (if lazy-load causes N+1 concerns at scale):**  
Add a dedicated repository method that returns `{participant_id: [visit_codes]}` using a single joined query. This is the preferred approach if the participant list grows beyond ~500 rows. For the current dataset size, the lazy-load approach is acceptable.

---

## Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Column header | `Visit Code` | Matches the Excel import column name exactly |
| Column position | After `Cohort Name` (index 8), before `Notes` | Logically follows demographic/study grouping |
| Multi-value display | Comma-separated, sorted ascending | Deterministic order; scannable |
| Empty value | Empty string `""` | No placeholder text — consistent with other optional columns |
| Data fetch | Within the existing `get_session()` block in `refresh()` | No new session, no new service method needed for this scope |

---

## Context

- `Sample.visit_code` is a nullable `String(16)` column added in Phase 2. It is populated by `excel_import_service.ExcelImportService` from column F of the Excel template.
- Manual participant registration (via the dialog) does not set visit codes — those belong on samples, which are created separately.
- The `COLUMNS` list in `ParticipantTab` is the single source of truth for column order; changing it here automatically updates headers and data alignment.
- Column index `0` stores `participant.id` in `Qt.ItemDataRole.UserRole` — this must remain at index 0 unchanged.

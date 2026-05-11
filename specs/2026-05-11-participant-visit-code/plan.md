# Plan — Participant Tab: Visit Code Column

**Branch:** `feature/visit-code-display`  
**Estimated effort:** 1–2 hours  
**Files changed:** 1 (`app/ui/views/participant_tab.py`)

---

## Task Group 1 — Read and map the existing code

1.1 Open `app/ui/views/participant_tab.py` and locate:
   - `COLUMNS` class attribute (line 22) — this drives both headers and data alignment.
   - `refresh()` method — specifically the `with get_session()` block and the `data = [...]` list comprehension.

1.2 Trace how `data` tuples are assembled and confirm:
   - Last element of each tuple is the hidden `participant.id` (excluded from display via `row_data[:-1]`).
   - Column indices are positional — inserting a new column at index N shifts everything after it.

1.3 Confirm `p.samples` is available as a relationship on `Participant` (see `models.py:150`) and that `Sample.visit_code` is a nullable string field (`models.py:189`).

---

## Task Group 2 — Add the column

2.1 In `COLUMNS`, insert `"Visit Code"` after `"Cohort Name"` and before `"Notes"`:
```python
COLUMNS = ["PID", "Study", "Age", "Gender", "Population", "Disease",
           "Site", "Cohort Name", "Visit Code", "Notes", "Registered"]
```

2.2 In `_build_ui()`, check the `setSectionResizeMode` calls. Currently index 2 is `Stretch`. After inserting a column at index 8, verify the resize modes still point at the right columns. Adjust if needed.

2.3 In `refresh()`, inside the `with get_session()` block, extend the `data` list comprehension to include visit codes. Build them from `p.samples` while the session is still open:

```python
with get_session() as session:
    service = ParticipantService(session)
    participants, total = service.search(filters, page=1, page_size=200)
    data = [
        (
            p.pid,
            p.study_id,
            str(p.age) if p.age else "",
            p.gender or "",
            p.population or "",
            p.disease or "",
            p.site_name or "",
            p.cohort_name or "",
            ", ".join(sorted(set(              # ← NEW
                s.visit_code
                for s in p.samples
                if s.visit_code
            ))),
            p.notes or "",
            str(p.created_at.date()) if p.created_at else "",
            p.id,   # hidden, must stay last
        )
        for p in participants
    ]
```

2.4 No other changes required — `display = list(row_data[:-1])` and the loop that writes cells are index-agnostic; they will pick up the new column automatically.

---

## Task Group 3 — Verify and tidy

3.1 Run the app (`python main.py`), log in as admin.

3.2 If there are existing participants in the DB: check the Participant tab renders without error and the new column appears with the correct header.

3.3 Import a test Excel file with at least two participants:
   - One with a single visit code (e.g. `M0`).
   - One with multiple visit codes across rows (e.g. `M0` and `M6` in separate import rows).
   - One row with no visit code.

3.4 Confirm:
   - Single visit code → displayed as-is.
   - Multiple codes → displayed comma-separated, sorted.
   - No visit code → empty cell (not "None" or blank-crashing).

3.5 Confirm the Edit dialog still opens correctly when double-clicking a row (participant_id still in `UserRole` on column 0).

3.6 Update `specs/constitution.md` section 14 to mark G1 as resolved.

---

## Task Group 4 — Commit and merge

4.1 Stage only `app/ui/views/participant_tab.py` and `specs/constitution.md`.

4.2 Write commit message:
```
feat(participant-tab): add Visit Code column from sample data

Resolves G1. Surfaces Sample.visit_code values in the participant list
as a sorted, comma-separated string built within the same DB session.
```

4.3 Merge `feature/visit-code-display` into `main`.

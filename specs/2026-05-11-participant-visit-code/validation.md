# Validation — Participant Tab: Visit Code Column

**Method:** Manual smoke test using the project dummy data file  
**Test file:** `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`  
**Gate:** All checks must pass before merging to `main`

---

## Test File Facts (CBMS_Dummy_Data.xlsx)

27 data rows · 10 unique PIDs · 21 columns.

Visit Code (column F) is a **decimal number** stored as a float in the Excel file (e.g. `1.0`, `2.0`). The import service stores it as a string in `Sample.visit_code`. The Participant tab must display it as-is from the DB — do not reformat or strip the decimal.

Key participants to verify against:

| PID                  | Expected Visit Codes (sorted)       |
|----------------------|--------------------------------------|
| COH20N01A2001S       | `1.0`                                |
| COH20N01A2001E       | `2.0, 3.0, 6.0`                     |
| COH19T01A1083E       | `2.0, 3.0, 5.0`                     |
| COH22G01B1212E       | `2.0, 4.0, 5.0, 6.0`               |
| COH22G01B1248E       | `4.0, 7.0`                           |
| COH21I01C1064M       | `4.0`                                |

---

## Pre-conditions

- [ ] App runs from source (`python main.py`) without crash.
- [ ] At least one active study exists (create one via the Studies tab if needed).
- [ ] Storage locations referenced in the dummy file exist in the DB, **or** import is attempted knowing that storage validation errors are expected — the participant + sample records should still be created even if storage placement fails.

> Note: The dummy file contains storage column values. If those freezers/racks/boxes do not exist, `excel_import_service` will report storage validation errors and may abort the full import. Create the referenced storage nodes first, or use a study-only import that skips storage validation.

---

## Smoke Test Checklist

### SC-1 — Column header appears

- [ ] Open the app, navigate to the **Participants** tab.
- [ ] The table shows a `Visit Code` column header between `Cohort Name` and `Notes`.
- [ ] No Python traceback printed to the terminal.

### SC-2 — Empty state (before import)

- [ ] With a fresh study and no participants, the table body is empty and the tab loads without error.

### SC-3 — Import the dummy file

- [ ] Click **Import from Excel**.
- [ ] Select `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`.
- [ ] Choose the target study.
- [ ] Complete the import (resolve any storage errors if present, or accept that storage placement is skipped).
- [ ] The dialog closes and the Participants tab refreshes.

### SC-4 — Single visit code participant

- [ ] Find `COH20N01A2001S` in the list.
- [ ] Its `Visit Code` cell shows `1.0`.

### SC-5 — Multiple visit codes participant

- [ ] Find `COH20N01A2001E` in the list.
- [ ] Its `Visit Code` cell shows `2.0, 3.0, 6.0` (sorted ascending, comma-space separated).

### SC-6 — No phantom "None" or crash on empty visit code

- [ ] If any imported participant has a blank visit code in the file, its cell shows an empty string — not the text `None`, not `nan`, not a crash.

### SC-7 — Edit dialog unaffected

- [ ] Click any participant row, then click **Edit**.
- [ ] The correct participant's data pre-fills the dialog (confirms `participant_id` in `UserRole` on column 0 is still correctly set after the column was inserted).
- [ ] Close without saving.

### SC-8 — Study filter still works

- [ ] Switch the study filter dropdown.
- [ ] Only participants for the selected study appear.
- [ ] Visit Code cells remain correctly populated.

### SC-9 — PID search still works

- [ ] Type `COH22G01B` in the PID search box.
- [ ] Only matching participants appear.
- [ ] `COH22G01B1212E` shows `2.0, 4.0, 5.0, 6.0`.

---

## Failure Criteria (do not merge if any occur)

| Symptom | Likely cause |
|---------|--------------|
| `DetachedInstanceError` on `p.samples` | Visit code was read after the session closed — move the set comprehension inside the `with get_session()` block |
| Cell shows `None` | Missing `if s.visit_code` guard in the set comprehension |
| Cell shows `1` instead of `1.0` | The import service is casting the float to int before storing — check `excel_import_service.py` |
| Columns misaligned (data under wrong header) | `COLUMNS` list length ≠ data tuple length — recount after insertion |
| Edit dialog opens wrong participant | `UserRole` lost from column 0, or `row_data[-1]` (the hidden id) was dropped |

---

## Post-merge checklist

- [ ] `specs/constitution.md` §14: mark G1 `Resolved 2026-05-11`.
- [ ] `TODO.md`: remove or strike the "In Participant tab, add the visit code" item.

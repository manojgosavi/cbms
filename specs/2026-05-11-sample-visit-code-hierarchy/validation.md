# Validation — Sample Tab: Visit Hierarchy by Visit Code

**Method:** Manual smoke test using the project dummy data file  
**Test file:** `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`  
**Gate:** All checks must pass before merging to `main`

---

## Test File Facts (CBMS_Dummy_Data.xlsx)

Participants with multiple visit codes to use as test subjects:

| PID                  | Visit Codes (import order) | Visit Names        |
|----------------------|----------------------------|--------------------|
| COH20N01A2001E       | 2.0, 3.0, 6.0              | Enrollment, Follow-up, Follow-up |
| COH19T01A1083E       | 2.0, 3.0, 5.0              | Enrollment, Follow-up, Follow-up |
| COH22G01B1212E       | 2.0, 4.0, 5.0, 6.0         | Enrollment, Follow-up, … |
| COH22G01B1248E       | 4.0, 7.0                   | Follow-up, Follow-up |

Use `COH20N01A2001E` as the primary test case (3 distinct codes, smallest set to verify).

---

## Smoke Test Checklist

### SC-1 — Left panel shows visit codes, not visit names

- [ ] Open app → Samples tab.
- [ ] Select the study, then select participant `COH20N01A2001E`.
- [ ] Left panel shows three top-level nodes labelled `2.0`, `3.0`, `6.0`.
- [ ] Left panel does **not** show `Enrollment` or `Follow-up` as node labels.

### SC-2 — Nodes appear in import order

- [ ] The node order matches the order samples appear in the DB (import order from the Excel file).
- [ ] No re-sorting has occurred.

### SC-3 — Click filter works for each code

- [ ] Click node `2.0` → right panel shows only samples with visit_code `2.0`.
- [ ] Click node `3.0` → right panel shows only samples with visit_code `3.0`.
- [ ] Click node `6.0` → right panel shows only samples with visit_code `6.0`.
- [ ] Right panel sample count label updates correctly for each filter.

### SC-4 — Participant with single visit code

- [ ] Select `COH20N01A2001S` (visit code `1.0` only).
- [ ] Left panel shows one node: `1.0`.
- [ ] Right panel shows all samples for that participant.

### SC-5 — Participant with four visit codes

- [ ] Select `COH22G01B1212E` (codes `2.0`, `4.0`, `5.0`, `6.0`).
- [ ] Left panel shows four nodes.
- [ ] Each click filters correctly.

### SC-6 — No "Visit Name" label appears anywhere in the left panel

- [ ] Scan left panel across all tested participants.
- [ ] No node labelled `Enrollment`, `Screening`, `Follow-up`, or similar appears.

### SC-7 — No debug output in terminal

- [ ] Terminal shows no `[DEBUG ...]` lines when switching participants.

### SC-8 — Add Sample dialog unaffected

- [ ] Click **Add Sample** with a participant selected.
- [ ] Dialog opens without error.
- [ ] Close without saving.

---

## Failure Criteria (do not merge if any occur)

| Symptom | Likely cause |
|---------|--------------|
| Left panel still shows visit names | `visit_name` not replaced with `visit_key = s.visit_code` in `_load_samples` |
| Click on node shows no samples | Tuple index 8 still stores `visit_name` but dict key is now `visit_code` — mismatch between storage and filter |
| `"None"` appears as a node label | Missing `or "No Visit"` guard on `s.visit_code` |
| All samples always shown (filter broken) | `_on_visit_clicked` still reads `visit_name` from UserRole but setData now stores `visit_code` |
| Debug prints still appearing | Some `print()` calls were missed |

---

## Post-merge checklist

- [ ] `specs/constitution.md` §14: mark G2 `Resolved 2026-05-11`.
- [ ] `TODO.md`: strike the "Sample tab left hierarchy should be on basis of visit code" item.

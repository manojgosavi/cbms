# Plan — Search Tab Unblock, Filters, Cohort Fix

## Task Group 1 — Cohort Bug Fix (search_service.py)

1.1 Line 164: change `filters.cohort_name` → `filters.cohort` in the ilike call.  
1.2 Rename `SearchFilters.cohort_name` field to `cohort` to match what search_tab.py sets.  
1.3 Update the `blank_map` entry `"cohort": Participant.cohort_name` (DB column stays `cohort_name`).  
1.4 Add the missing `visit_code` condition: `Sample.visit_code.ilike(f"%{filters.visit_code}%")`.  
1.5 Confirm `population` condition already exists; verify it references `Participant.population`.

## Task Group 2 — Blocking Service Permission (blocking_service.py)

2.1 Remove `app_session.require("sample.edit")` from `release_block()`.  
2.2 Remove `app_session.require("sample.edit")` from `release_multiple()` (it delegates to `release_block`, so removing there is sufficient; double-check).  
2.3 Keep `app_session.require("sample.edit")` in `block_aliquots()` unchanged.

## Task Group 3 — Unblock Dialog (new file: app/ui/dialogs/unblock_dialog.py)

3.1 Create `UnblockDialog(QDialog)` that receives `aliquot_ids: list[int]`.  
3.2 Show a read-only list of aliquot count in the dialog header.  
3.3 QLineEdit for release reason (required, validated on Accept).  
3.4 OK / Cancel buttons; on OK call `BlockingService.release_multiple(aliquot_ids, reason)` inside a session.  
3.5 Show success/error QMessageBox; accept dialog on success.

## Task Group 4 — Search Tab UI (search_tab.py)

4.1 Add "Unblock selected…" QPushButton to the results toolbar (next to "Block selected…").  
4.2 Wire `_btn_unblock.clicked` → `_on_unblock()`.  
4.3 In `_on_selection_changed()`: enable "Unblock selected" when any selected row has `is_blocked == True` (check via `self._results`).  
4.4 Add `_f_visit_code` QLineEdit (partial match) to the left pane filter form — after Visit Time.  
4.5 Add `_f_population` QLineEdit (partial match) to the left pane filter form — after PID.  
4.6 Rename the section label above the Age SpinBox from "Population" → "Age".  
4.7 In `_build_filters()`: set `f.cohort` (was already correct), `f.visit_code`, `f.population`.  
4.8 In `_on_clear()`: clear the two new fields.

## Task Group 5 — Validation & Cleanup

5.1 Run a cohort search with known data — confirm results return.  
5.2 Block an aliquot as LAB_TECH, then unblock it — confirm no permission error.  
5.3 Filter by visit code and population — confirm results filter correctly.  
5.4 Mark TODO item done.

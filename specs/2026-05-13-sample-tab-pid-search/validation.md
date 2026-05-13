# Validation — Sample Tab PID Search & Multi-Select

## Manual Test Cases (using CBMS_Dummy_Data.xlsx data)

### V1 — PID list loads sorted
1. Open CBMS → Sample tab.
2. Select a study.
3. Confirm PIDs appear in alphabetical order in the list.

### V2 — PID search filters list
1. Type a partial PID in the search box.
2. Confirm list narrows to matching PIDs; order remains alphabetical.
3. Clear the search box — full sorted list reappears.

### V3 — Single participant selection (regression)
1. Check exactly one PID checkbox.
2. Visit list populates with that participant's visit codes; "All Visits" at top.
3. Sample tree shows that participant's samples (6 cols, unchanged).
4. "Add Sample" button is enabled.
5. Click a visit code — tree filters to that visit's samples only.

### V4 — Multi-participant selection
1. Check two or more PIDs.
2. Sample tree shows samples from ALL checked participants merged.
3. Visit list shows union of their visit codes.
4. "Add Sample" button is disabled.
5. Uncheck one PID — tree updates immediately.

### V5 — Select All / Clear All
1. Click "Select All" — all PIDs get checked; samples from all participants load.
2. Click "Clear All" — all unchecked; sample tree empties.

### V6 — No regression: Add Aliquots / Edit
1. Check one PID, select a sample row → "Add Aliquots" and "Edit" enable.
2. Check two PIDs, select a sample row → "Add Aliquots" and "Edit" still follow tree-selection logic.

### V7 — Study change clears state
1. Load samples for one study/participant.
2. Change Study dropdown → participant list reloads sorted for new study; sample tree empties.

## Pass Criteria
All V1–V7 cases pass without error dialogs or Python tracebacks.  
No existing tabs (Participant, Storage, Search, Catalogue) show regressions.

# Plan — Sample Tab PID Search & Multi-Select

## Task Group 1 — Participant Selector Redesign

1.1 Remove `self._participant_combo` (QComboBox).  
1.2 Add `self._pid_search` (QLineEdit, placeholder "Search PID…") below Study dropdown.  
1.3 Add `self._participant_list` (QListWidget, checkable items).  
1.4 Add "Select All" / "Clear All" buttons below the list.  
1.5 Wire `_pid_search.textChanged` → `_filter_participant_list()` (client-side, no DB).  
1.6 Wire `_participant_list.itemChanged` → `_on_participant_selection_changed()`.  
1.7 On Study change: load all participants into `_participant_list` sorted alphabetically, checked = none.

## Task Group 2 — PID List Sorting

2.1 When loading participants for a study, sort PIDs alphabetically (A→Z) before inserting into `_participant_list`.  
2.2 `_filter_participant_list()` hides/shows items by case-insensitive prefix match; visible items remain in sorted order.

## Task Group 3 — Multi-Participant Data Loading

3.1 Refactor `_load_samples()` to accept `list[int]` participant IDs (instead of single int).  
3.2 Loop over IDs, query each participant's samples, accumulate into `_all_sample_data`.  
3.3 Call `_load_samples(checked_ids)` whenever checkbox state changes.  
3.4 "Add Sample" button: enable only when exactly 1 participant is checked.

## Task Group 4 — Visit List Compatibility

4.1 Visit list rebuilds from union of all checked participants' visit codes.  
4.2 "All Visits" item at top of visit list to reset the visit filter.  
4.3 Visit filter click filters `_all_sample_data` by the selected visit code.

## Task Group 5 — Cleanup & No-Regression

5.1 Remove old `_on_participant_changed()` and participant-combo logic from `_on_study_changed()`.  
5.2 On study change: clear `_participant_list`, reload PIDs for new study (sorted).  
5.3 "Add Sample" disabled when ≠ 1 PID checked; "Add Aliquots" / "Edit" keep existing tree-selection guard.  
5.4 Sample tree columns unchanged (6 cols, no PID column added).

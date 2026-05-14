# Validation — UX Improvements

## Manual Test Cases

### V1 — Participant export button state
1. Open Participant tab with no study selected → Export button disabled.
2. Select a study with participants → Export button enabled.
3. Type a PID filter that matches nothing → Export button disables.

### V2 — Participant export content
1. With participants loaded, click "Export to Excel".
2. Save dialog appears; choose a location.
3. Open the saved file — headers match tab columns (PID, Study, Age, Gender, …).
4. Row count equals total filtered participants (not just the visible page of 100).

### V3 — Participant table sorting
1. Click the "PID" column header → rows sort alphabetically.
2. Click again → reverse order.
3. Click "Age" → rows sort numerically by age.
4. After sorting, selecting a row and clicking Edit opens the correct participant.

### V4 — Search results sorting
1. Run a search returning multiple rows.
2. Click "Collection Date" header → rows sort by date.
3. Click "Status" → rows sort alphabetically by status.
4. After sorting, "Show in box" still navigates to the correct aliquot.

### V5 — Audit Log sorting
1. Open Admin → Audit Log.
2. Click "Timestamp" header → sorted chronologically.
3. Click "Action" header → sorted by action name.

### V6 — Last backup indicator visible
1. On app startup, status bar (bottom right) shows "Last backup: YYYY-MM-DD HH:MM" or "No backup found".
2. Take a backup (Ctrl+B or Admin) → label updates immediately.
3. Admin tab also shows the backup timestamp near the backup controls.

### V7 — No regression
1. Pagination still works on Participant and Search tabs after sorting.
2. Block/Unblock/Ship actions in Search still operate on the correct aliquot after table is sorted.

## Pass Criteria
All V1–V7 pass without error dialogs or Python tracebacks.

# Validation — Search Tab Unblock, Filters, Cohort Fix

## Manual Test Cases

### V1 — Cohort search returns results
1. Open Search tab.
2. Type a known cohort name (e.g. "HIV INFECTED") in the Cohort field.
3. Click Search — results appear for matching participants.
4. Previously this returned 0 results (bug).

### V2 — Visit Code filter
1. Type a known visit code (e.g. "1.0") in the new Visit Code field.
2. Click Search — only aliquots from that visit code appear.
3. Clear and search again — all results return.

### V3 — Population filter
1. Type a known population value (e.g. "FSW") in the new Population field.
2. Click Search — only matching participants' aliquots appear.
3. Section label above the Age spinner now reads "Age" not "Population".

### V4 — Unblock button state
1. Run a search with no blocked aliquots selected — "Unblock selected" is disabled.
2. Select a row where Status = "Blocked" — "Unblock selected" enables.
3. Select only non-blocked rows — button disables again.

### V5 — Unblock dialog and release (all roles)
1. Log in as LAB_TECH.
2. Select a blocked aliquot row, click "Unblock selected…".
3. Unblock dialog appears showing aliquot count.
4. Enter a reason and click OK.
5. Success message shown; search refreshes; aliquot status changes to "Available".
6. No permission error raised.

### V6 — Unblock reason required
1. Open Unblock dialog, leave reason blank, click OK.
2. Validation error shown; dialog stays open.

### V7 — Block permission unchanged
1. Log in as LAB_TECH.
2. Select an available aliquot, click "Block selected…".
3. Confirm a permission error is raised (sample.edit required for blocking).

### V8 — No regression on existing filters
1. PID, Age, Site, Visit Time, Disease, Sample Type filters still work as before.
2. Block / Ship / Export / Show in box buttons still function correctly.

## Pass Criteria
All V1–V8 pass without error dialogs or Python tracebacks.

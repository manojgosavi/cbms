# Validation — Pagination

## Manual Test Cases

### V1 — Participant tab shows first 100 rows
1. With 1380 rows imported, open Participant tab.
2. Table shows exactly 100 rows.
3. Label reads "Page 1 of X (N total)".
4. Prev button is disabled; Next is enabled.

### V2 — Participant tab page navigation
1. Click Next → table shows rows 101–200; label updates; Prev now enabled.
2. Navigate to last page → Next becomes disabled.
3. Click Prev → goes back one page correctly.

### V3 — Participant filter resets to page 1
1. Navigate to page 3, then type a PID in the search box.
2. Table resets to page 1 of filtered results.

### V4 — Search tab pagination
1. Run a search returning >100 results.
2. Table shows first 100; pagination bar shows correctly.
3. Click Next → next 100 results load; toolbar buttons (Block, Unblock) work on visible selection.
4. Clicking Search again resets to page 1.

### V5 — Audit Log pagination
1. Open Admin tab → Audit Log.
2. With many audit entries, first 100 show; pagination bar appears.
3. Next/Prev navigate correctly.

### V6 — Reports tab pagination
1. Open Reports tab, run a report with >100 rows.
2. Pagination bar appears; first 100 rows shown.
3. Next/Prev navigate the in-memory result set.

### V7 — No regression
1. All existing actions (Edit, Block, Ship, Export) work on the current page.
2. Tabs without pagination (Storage, Sample, Catalogue, Dashboard, Shipments) are unchanged.

## Pass Criteria
All V1–V7 pass without error dialogs or Python tracebacks.

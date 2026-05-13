# Validation — Search → Storage Navigation Fix

## Manual Test Cases

### V1 — Double-click navigates to correct box and cell
1. Open Search tab, run a search that returns results with storage locations.
2. Double-click any row that has a Freezer/Box/Position filled in.
3. Storage tab becomes active automatically.
4. The hierarchy tree scrolls to and selects the correct box node.
5. The box grid renders and the correct cell is highlighted (green selected colour).

### V2 — "Show in box" button has same effect
1. Select a single row in search results with a storage location.
2. Click "Show in box".
3. Same navigation as V1 occurs.

### V3 — Aliquot with no location shows informative message
1. Run a search that returns an aliquot without a storage location (Position column blank).
2. Double-click that row.
3. A dialog appears: "No storage location recorded for this aliquot."
4. Storage tab does not switch (or switches but shows empty grid with the message).

### V4 — No regression on Storage tab normal operation
1. After navigating via search, manually click a different box in the tree.
2. Grid updates correctly to the newly selected box.
3. Place/Move/Remove actions still work normally.

### V5 — No regression on Search tab
1. Other search actions (Block, Unblock, Ship, Export) still work after the double-click fix.

## Pass Criteria
All V1–V5 pass without error dialogs or Python tracebacks.

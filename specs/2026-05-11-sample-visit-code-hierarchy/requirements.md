# Requirements — Sample Tab: Visit Hierarchy by Visit Code

**Gap ID:** G2  
**Branch:** `feature/sample-visit-code-hierarchy`  
**Date:** 2026-05-11  
**Status:** Approved

---

## Problem

The Sample tab left panel groups samples into visit nodes using `Sample.visit_name` (e.g. "Screening", "Enrollment", "Follow-up"). Visit name is a human-readable label but is not unique or stable enough to be a grouping key — the same name can appear across different visit codes. The correct grouping key is `Sample.visit_code` (e.g. `1.0`, `2.0`, `3.0`), which is the numeric identifier set at import time and uniquely identifies a visit timepoint.

## Scope

**In scope (G2 only):**
- Change the left-panel visit nodes in `app/ui/views/sample_tab.py` to display and group by `Sample.visit_code` instead of `Sample.visit_name`.
- Blank `visit_code` falls back to the label `"No Visit"`.
- Node order follows insertion order (the order samples are returned by the DB query — no additional sorting applied).
- Clicking a visit code node still filters the right-hand sample tree to samples belonging to that code.

**Out of scope:**
- Displaying visit name alongside the code.
- Any changes to `Sample.visit_name` storage or the import service.
- Sorting nodes by numeric value.
- Any other tab or service.

---

## Data Flow

```
Sample.visit_code  →  grouping key in _visits_dict  →  left-panel node label
Sample.visit_code  →  stored at tuple index 8       →  filter key in _on_visit_clicked
```

Both the grouping dict key and the cached tuple value at index 8 must change from `visit_name` to `visit_code` in the same edit so the filter stays consistent.

---

## Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Display label | `visit_code` as-is (e.g. `"1.0"`) | Matches Excel column F exactly; no reformatting |
| Fallback label | `"No Visit"` | Consistent with current behaviour for blank visit_name |
| Node order | Insertion order (no sort) | User preference; import order is naturally chronological |
| Filter key at tuple[8] | `visit_code` (was `visit_name`) | Must match the dict key; no other change needed |
| Variable name in code | Rename `visit_name` local var to `visit_key` | Avoids confusion with the `Sample.visit_name` ORM field |

---

## Context

- `Sample.visit_code` is `String(16)`, nullable, set by `excel_import_service`.
- `Sample.visit_name` is `String(64)`, nullable, set separately. It is not touched by this change.
- The `_visits_dict` is built inside a `with get_session()` block and cached on `self._visits_dict`. The filter in `_on_visit_clicked` reads from `self._all_sample_data` which is also cached in the same block. Both must use the same key.
- Debug `print()` statements exist in the current code (`[DEBUG ...]`). They should be removed as part of this change since they were added during development.

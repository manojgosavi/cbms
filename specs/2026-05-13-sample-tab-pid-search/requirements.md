# Sample Tab — PID Search, Multi-Select, Sorted PID List

**Date:** 2026-05-13  
**Branch:** feature/sample-tab-pid-search-multiselect  
**Status:** In Progress

---

## Scope

Upgrade the Sample tab's participant selection to support:

1. **PID Search box** — replace the Participant dropdown with a QLineEdit + checkable QListWidget. Typing filters visible PIDs in real time.
2. **Multiple participant selection** — checking multiple PIDs merges all their samples into the right-side tree.
3. **Sorted PID list** — PIDs loaded alphabetically (A→Z) in the participant list; sort order preserved after filtering.

---

## Out of Scope

- Adding a PID column to the sample tree (tree columns unchanged).
- Adding a Sample Type filter dropdown.
- Changing the aliquot sub-rows structure.
- Persistence of checkbox state across tab switches.

---

## Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Participant list widget | QListWidget with Qt.CheckState checkboxes | Allows multi-select without Ctrl/Shift; clear visual state |
| PID filter | Client-side in-memory filter (hide/show items) | No DB round-trip per keystroke |
| PID sort | Alphabetical A→Z at load time | Consistent, predictable; no toggle needed |
| Sample merge | Flat list in existing 6-col tree | No new columns; visit filter still works on merged data |

---

## Context

Current state:
- Study dropdown + Participant dropdown (one selection at a time)
- Visit list on left filters the right-side tree by visit code
- Sample tree: 6 columns [ID, Type, Collection Date, Vol, Status, Discrepancy]

After this change:
- Study dropdown (unchanged)
- PID search box → checkable, sorted participant list below it + Select All / Clear All
- Visit list shows union of all checked participants' visit codes; "All Visits" at top
- Sample tree unchanged (same 6 columns)
- "Add Sample" disabled when ≠ 1 PID checked

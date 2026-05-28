# Plan: Sample Tab — PID-Based Display & Visit Code Column

> Status: DRAFT — pending answers to open questions in requirement.md

---

## Affected Files

| File | Change |
|---|---|
| `app/ui/views/sample_tab.py` | Primary UI changes (columns, rendering, visit tree labels) |
| `app/core/services/sample_service.py` | Expose participant PID alongside sample data (if not already) |
| `app/core/repositories/sample_repository.py` | Join participant to fetch PID with samples |

---

## Implementation Steps

### Step 1 — Enrich sample data tuple with PID
In `sample_tab.py::_load_samples()`, the current code calls `svc.get_samples_for_participant(pid_db)` which returns `Sample` objects. Each `Sample` has a `participant` relationship, so `s.participant.pid` is available.

Extend the `all_sample_data` tuple to store `participant_pid` alongside the existing fields:
```
(s.sample_id, s.sample_type, date, "", aliquot_count, "", s.id, aliquot_data, visit_key, s.participant.pid)
#                                                                                              ^ new at index 9
```

### Step 2 — Update right-pane tree columns
In `_build_ui()`:
- Change `setColumnCount(6)` → `setColumnCount(7)`
- Change `setHeaderLabels(["ID", "Type", ...])` → `["ID", "Visit Code", "Type", "Collection Date", "Vol (µL)", "Status", "Discrepancy"]`
- Update `ResizeMode` calls for the new column layout.

In `_render_sample_tree()`:
- `sample_item.setText(0, pid)` — show PID instead of `s_id`
- `sample_item.setText(1, visit_code)` — new visit code column
- Shift remaining columns by +1 (Type → col 2, Date → col 3, etc.)
- Store `db_id` via `setData` unchanged (still needed for edit/add-aliquots actions).

### Step 3 — Update left visit-tree children
In `_load_samples()`, when appending visit children:
```python
visits[visit_key].append((s.sample_id, s.participant.pid, s.sample_type))
```
In the visit tree population loop:
```python
child.setText(0, f"  {pid}")  # or f"  {pid} ({sample_type})" for disambiguation
```

### Step 4 — Header column index alignment
`_on_tree_selection_changed` reads `item_data[0]` from `UserRole` — no column index, unaffected.
`_on_visit_clicked` filters `_all_sample_data` by index 8 (visit_key) — index unchanged.
`_render_sample_tree` for aliquots: aliquot rows write to columns 3 (vol), 4 (status), 5 (disc) — shift to 4, 5, 6 with new layout.

---

## Risk / Notes
- Disambiguation in visit tree: if participant has Serum + PBMC in same visit, both children would show the same PID. Append `(sample_type)` to avoid confusion.
- The internal `sample_id` is NOT removed from the data tuple — it remains in `UserRole` data so edit/add-aliquot dialogs continue to work.
- No DB migration needed (display-only change).

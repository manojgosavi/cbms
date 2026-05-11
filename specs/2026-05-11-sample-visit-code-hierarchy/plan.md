# Plan — Sample Tab: Visit Hierarchy by Visit Code

**Branch:** `feature/sample-visit-code-hierarchy`  
**Estimated effort:** 30 minutes  
**Files changed:** 1 (`app/ui/views/sample_tab.py`)

---

## Task Group 1 — Locate all visit_name references in _load_samples

In `app/ui/views/sample_tab.py`, find every line in `_load_samples` that reads `s.visit_name` or uses the local variable `visit_name` as a grouping key. There are four sites:

- **Line 219** — `visit_name = s.visit_name or "No Visit"` → grouping key assignment  
- **Line 239** — `visits[visit_name].append(s.sample_id)` → dict insertion  
- **Line 252** — `visit_name,  # ADD visit_name at index 8` → tuple element  
- **Line 267** — `visit_item.setData(0, Qt.ItemDataRole.UserRole, visit_name)` → stored for filter  
- **Line 266** — `visit_item.setText(0, visit_name)` → display label  

Also note **line 333** in `_on_visit_clicked`:  
- `visit_name = item.data(0, Qt.ItemDataRole.UserRole)` — reads what was stored in setData  
- `if s[8] == visit_name` — compares against tuple index 8  

These two must continue to match whatever key is chosen.

---

## Task Group 2 — Change the grouping key to visit_code

2.1 In `_load_samples`, change the grouping key line:
```python
# Before
visit_name = s.visit_name or "No Visit"

# After
visit_key = s.visit_code or "No Visit"
```

2.2 Update all subsequent uses of `visit_name` as a dict/tuple key to `visit_key`:
```python
# visits dict
if visit_key not in visits:
    visits[visit_key] = []
...
visits[visit_key].append(s.sample_id)

# tuple index 8
visit_key,  # visit_code stored for filtering
```

2.3 Update the visit list population loop (still outside the session block):
```python
for visit_key in self._visits_dict:
    visit_item = QTreeWidgetItem(self._visit_list)
    visit_item.setText(0, visit_key)
    visit_item.setData(0, Qt.ItemDataRole.UserRole, visit_key)

    for sample_id in self._visits_dict[visit_key]:
        sample_item = QTreeWidgetItem(visit_item)
        sample_item.setText(0, f"  {sample_id}")
```

2.4 In `_on_visit_clicked`, rename the local variable to `visit_key` for clarity (the filter `s[8] == visit_key` continues to work because tuple index 8 now holds the visit_code):
```python
def _on_visit_clicked(self, item, col):
    visit_key = item.data(0, Qt.ItemDataRole.UserRole)
    if visit_key is None or not isinstance(visit_key, str):
        return
    self._current_visit_filter = visit_key
    filtered_samples = [s for s in self._all_sample_data if s[8] == visit_key]
    self._render_sample_tree(filtered_samples)
```

---

## Task Group 3 — Remove debug print statements

Remove all `print(f"[DEBUG ...]")` calls added during development. They appear on lines:
- 216, 240, 254, 284, 286, 327, 336

---

## Task Group 4 — Verify and update docs

4.1 Run the app and import `CBMS_Dummy_Data.xlsx`. Select a participant with multiple visit codes (e.g. `COH20N01A2001E` which has codes `2.0`, `3.0`, `6.0`). Confirm the left panel shows `2.0`, `3.0`, `6.0` as node labels (not `Enrollment`, `Follow-up`, etc.).

4.2 Click each node and confirm the right panel filters to only that visit's samples.

4.3 Update `specs/constitution.md` §14 to mark G2 resolved.

4.4 Update `TODO.md` to strike the G2 item.

---

## Task Group 5 — Commit

```
feat(sample-tab): group visit hierarchy by visit_code instead of visit_name

Resolves G2. Changes the left-panel grouping key from Sample.visit_name
to Sample.visit_code. Removes development debug print statements.
```

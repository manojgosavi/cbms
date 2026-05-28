# Validation: Search Tab — Add Visit Code & Population Columns, Remove Vol

---

## Manual Test Cases

### TC-1: Visit Code Column Populated
**Setup:** Run a search that returns samples with a known visit code (e.g., M0).
**Expected:** "Visit Code" column shows the correct value for each row.

### TC-2: Visit Code Column Blank When Null
**Setup:** A result row where `Sample.visit_code` is NULL.
**Expected:** Cell is blank — no crash, no "None" text.

### TC-3: Population Column Populated
**Setup:** Run a search returning participants with a known population (e.g., FSW, MSM).
**Expected:** "Population" column shows the correct value.

### TC-4: Population Column Blank When Null
**Setup:** A result row where `Participant.population` is NULL.
**Expected:** Cell is blank.

### TC-5: Vol Column Absent
**Setup:** Run any search with results.
**Expected:** No "Vol (µL)" column header or data appears in the table.

### TC-6: Discrepancy Column Stretches
**Setup:** Resize the window.
**Expected:** "Discrepancy" column (last column) stretches to fill remaining width; all other columns resize to content.

### TC-7: All Other Columns Intact
**Setup:** Run a search with results covering participant, sample, and storage data.
**Expected:** PID, Age, Gender, Disease, Cohort, Site, Sample ID, Sample Type, Collection Date, Aliquot ID, Status, Freezer, Compartment, Rack, Drawer, Box, Position all show correct values.

### TC-8: Block / Unblock / Ship Actions Still Work
**Setup:** Select rows with specific statuses and trigger each action.
**Expected:** Dialogs open correctly; table refreshes after action completes.

### TC-9: Export Still Works
**Setup:** Run a search, click Export to Excel.
**Expected:** Export dialog opens and completes without error. (Vol column in export is a separate decision — verify with user.)

### TC-10: Double-click Navigate Still Works
**Setup:** Double-click a row that has a storage location.
**Expected:** Navigates to Storage tab and highlights the box position.

---

## Regression Checks
- [ ] `_selected_aliquot_ids()` correctly reads aliquot DB id from col 0 UserRole.
- [ ] Pagination still works after column change.
- [ ] Sort by any column works correctly.
- [ ] OR / AND search mode still respected.
